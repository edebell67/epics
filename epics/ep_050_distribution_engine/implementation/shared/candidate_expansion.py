# epics/ep_050_distribution_engine/implementation/shared/candidate_expansion.py
# EP050 shared — one-hop candidate generation for the winner-replication/scale-out loop.
#
# A Node 01 target is really a (service, geography.locality) pair. From a winning target, this
# module proposes new CANDIDATE targets one hop away on exactly one axis: same geo with an
# adjacent real service, or same service with an adjacent real geo. It never proposes both axes
# changing at once (see plans/20260818_1645_ep050_winner_replication_and_scale_out.md §4) so a
# later win or loss stays attributable to the one thing that changed.
#
# Both adjacency sources are fixed, curated, real-world data (Option A from that plan), not
# generated or guessed per call: GEO_ADJACENCY reflects actual neighbouring London
# towns/postcode areas to the localities this project has registered targets for; SERVICE_ADJACENCY
# must reflect services this business actually offers, confirmed by the business owner -- not
# merely generic trade plausibility (a real mistake made and corrected on 2026-08-18: see v1.1.0).
# Neither list is exhaustive -- a locality or service with no curated entry raises DerivationError
# rather than guessing, same fail-closed posture as shared/target_parameter_derivation.py.
#
# Pure functions only: no network access, no registry writes. The caller (server.py) is
# responsible for actually registering each returned candidate payload at Node 01 and for gating
# its Phase 2 on human approval, per plan §4/§9.
#
# VERSION HISTORY
# v1.1.0 · 2026-08-18 · Removes "boiler_installation" and "central_heating_repair" from
#   SERVICE_ADJACENCY after direct user verification that this business does not actually offer
#   either -- they were this module's own generic-trade-plausibility guess, not a confirmed fact,
#   and the guess was wrong. This had already minted 2 real (now-deleted) candidate campaigns for
#   non-existent services before being caught. Only "boiler_service" remains, which the user did
#   confirm and has real product/audience data registered. Lesson encoded in the module docstring
#   above: an adjacency entry needs confirmation, not just plausibility, before it goes in this list.
# v1.0.0 · 2026-08-18 · Initial version. Build order item 1+2 of the winner-replication plan.

from __future__ import annotations

import re
from typing import Any, Mapping

# Curated real-world geo adjacency, keyed by slugified locality. Values are the real neighbouring
# towns/postcode areas actually adjacent to that locality in London -- not derived from any
# distance calculation or external API, chosen once from real geography.
GEO_ADJACENCY: dict[str, list[str]] = {
    "blackheath": ["Lewisham", "Greenwich", "Catford", "Charlton", "Eltham"],
}

# Curated real trade-service adjacency, keyed by slugified service. Values are real adjacent
# trades a business offering the key service plausibly also offers.
# Corrected 2026-08-18: "boiler_installation" and "central_heating_repair" were removed after
# direct user verification that this business does not actually offer either -- they were this
# module's own curated guess at generic trade plausibility, not a confirmed fact about the real
# business, and the guess was wrong. Only keep an entry here once it's been confirmed real, not
# merely domain-plausible; a wrong entry mints a real candidate campaign for a service that
# doesn't exist, which is exactly the fabrication this whole design is meant to prevent.
SERVICE_ADJACENCY: dict[str, list[str]] = {
    "boiler_repair": ["boiler_service"],
}


class DerivationError(ValueError):
    """Raised when no curated adjacency exists for the given service or locality -- fail-closed,
    never a guessed/fabricated candidate."""


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _require_target_record(target_record: Mapping[str, Any]) -> tuple[str, str, dict[str, str]]:
    if not isinstance(target_record, Mapping):
        raise DerivationError("target_record must be an object (Node 01 TargetRecord shape)")
    service = target_record.get("service")
    geography = target_record.get("geography")
    if not isinstance(service, str) or not service.strip():
        raise DerivationError("target_record.service is required and must be a non-empty string")
    if not isinstance(geography, Mapping):
        raise DerivationError("target_record.geography must be an object (Node 01 shape)")
    locality = geography.get("locality")
    if not isinstance(locality, str) or not locality.strip():
        raise DerivationError("target_record.geography.locality is required and must be a non-empty string")
    return service, locality, dict(geography)


def derive_adjacent_geo_candidates(target_record: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Same service, one hop to an adjacent real geo. Returns ready-to-register Node 01 payloads
    (target_type/service/market carried over unchanged; only geography.locality changes)."""
    service, locality, geography = _require_target_record(target_record)
    target_type = target_record.get("target_type")
    market = target_record.get("market")
    key = _slugify(locality)
    adjacent = GEO_ADJACENCY.get(key)
    if not adjacent:
        raise DerivationError(
            f"No curated geo adjacency for locality {locality!r} (slug {key!r}) -- "
            "add a real entry to GEO_ADJACENCY before proposing a geo-axis candidate here"
        )
    return [
        {
            "target_type": target_type,
            "service": service,
            "market": market,
            "geography": {**geography, "locality": new_locality},
        }
        for new_locality in adjacent
    ]


def derive_adjacent_service_candidates(target_record: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Same geo, one hop to an adjacent real service. Returns ready-to-register Node 01 payloads
    (target_type/market/geography carried over unchanged; only service changes)."""
    service, _locality, geography = _require_target_record(target_record)
    target_type = target_record.get("target_type")
    market = target_record.get("market")
    key = _slugify(service)
    adjacent = SERVICE_ADJACENCY.get(key)
    if not adjacent:
        raise DerivationError(
            f"No curated service adjacency for service {service!r} (slug {key!r}) -- "
            "add a real entry to SERVICE_ADJACENCY before proposing a service-axis candidate here"
        )
    return [
        {
            "target_type": target_type,
            "service": new_service,
            "market": market,
            "geography": dict(geography),
        }
        for new_service in adjacent
    ]


def derive_one_hop_candidates(target_record: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Both axes combined -- still one hop each, never a compound (geo+service) jump. Geo-axis
    candidates missing a curated entry, or service-axis candidates missing one, are simply omitted
    from that axis rather than failing the whole call, so a target with only one curated axis
    still yields whatever real candidates it can."""
    candidates: list[dict[str, Any]] = []
    try:
        candidates.extend(derive_adjacent_geo_candidates(target_record))
    except DerivationError:
        pass
    try:
        candidates.extend(derive_adjacent_service_candidates(target_record))
    except DerivationError:
        pass
    return candidates
