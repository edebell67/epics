# epics/ep_050_distribution_engine/implementation/operational_console_claude/discovery_engine.py — Persistent Discovery 00A–00F domain engine.
#
# VERSION HISTORY
# v1.0.0 · 2026-08-21 · Implements evidence-gated briefs, signals, clustering, opportunity scoring,
#   offer hypotheses, validation outcomes and the canonical EP050 merge contract.

from __future__ import annotations

import hashlib
import json
import re
import threading
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SCHEMA = "validated_opportunity_offer_contract.v1"
PASS_SCORE = 65
MIN_SIGNALS = 3
MIN_DOMAINS = 2
MIN_COMMITMENTS = 2
_LOCK = threading.RLock()
_WORD = re.compile(r"[a-z0-9]+")
_STOP = {"the", "and", "for", "with", "that", "this", "from", "have", "their", "into", "when", "about", "your", "are", "but", "not"}
_URGENCY = {"urgent", "delay", "late", "deadline", "fine", "penalty", "risk", "costly", "lost", "critical", "blocked"}
_PAYMENT = {"pay", "paid", "price", "cost", "quote", "subscription", "budget", "purchase", "buy", "fee", "hire"}
_COMMITMENTS = {"qualified_waitlist", "demo_request", "interview_confirmed", "paid_pilot", "preorder", "deposit"}


class DiscoveryError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _text(value: Any, field: str, *, minimum: int = 2) -> str:
    value = str(value or "").strip()
    if len(value) < minimum:
        raise DiscoveryError(f"{field} is required")
    return value


def _tokens(value: str) -> list[str]:
    return [w for w in _WORD.findall(value.lower()) if len(w) > 2 and w not in _STOP]


class DiscoveryStore:
    def __init__(self, root: Path):
        self.root = root

    def _path(self, discovery_id: str) -> Path:
        if not re.fullmatch(r"disc_[a-f0-9]{12}", discovery_id):
            raise DiscoveryError("Invalid discovery id")
        return self.root / discovery_id / "discovery.json"

    def save(self, record: dict[str, Any]) -> dict[str, Any]:
        record["updated_at"] = _now()
        path = self._path(record["discovery_id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)
        return record

    def load(self, discovery_id: str) -> dict[str, Any]:
        path = self._path(discovery_id)
        if not path.exists():
            raise DiscoveryError("Discovery brief not found")
        return json.loads(path.read_text(encoding="utf-8"))

    def list(self) -> list[dict[str, Any]]:
        if not self.root.exists():
            return []
        records = [json.loads(p.read_text(encoding="utf-8")) for p in self.root.glob("disc_*/discovery.json")]
        return sorted(records, key=lambda x: x.get("created_at", ""), reverse=True)

    def create(self, body: dict[str, Any]) -> dict[str, Any]:
        brief = {
            "audience": _text(body.get("audience"), "audience"),
            "geography": _text(body.get("geography"), "geography"),
            "problem_territory": _text(body.get("problem_territory"), "problem_territory", minimum=5),
            "commercial_model": _text(body.get("commercial_model", "Undecided"), "commercial_model"),
            "constraints": str(body.get("constraints") or "").strip(),
            "excluded_sources": list(body.get("excluded_sources") or []),
        }
        now = _now()
        record = {"discovery_id": _id("disc"), "schema_version": 1, "stage": "00A", "state": "brief_ready", "brief": brief, "signals": [], "validation_outcomes": [], "clusters": [], "opportunity": None, "offer": None, "contract": None, "run_id": None, "lineage": [{"stage": "00A", "at": now, "action": "brief_created"}], "created_at": now, "updated_at": now}
        with _LOCK:
            return self.save(record)

    def add_signals(self, discovery_id: str, signals: list[dict[str, Any]]) -> dict[str, Any]:
        if not signals:
            raise DiscoveryError("At least one source-attributed signal is required")
        with _LOCK:
            record = self.load(discovery_id)
            existing = {x["fingerprint"] for x in record["signals"]}
            for raw in signals:
                url = _text(raw.get("source_url"), "source_url")
                parsed = urlparse(url)
                if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                    raise DiscoveryError("source_url must be an absolute HTTP(S) URL")
                statement = _text(raw.get("problem_statement"), "problem_statement", minimum=8)
                observed_at = _text(raw.get("observed_at"), "observed_at")
                fingerprint = hashlib.sha256(f"{url}|{statement}".lower().encode()).hexdigest()[:20]
                if fingerprint in existing:
                    continue
                signal = {"signal_id": _id("psig"), "fingerprint": fingerprint, "source_url": url, "source_domain": parsed.netloc.lower(), "source_type": _text(raw.get("source_type", "public_web"), "source_type"), "observed_at": observed_at, "problem_statement": statement, "evidence_excerpt": _text(raw.get("evidence_excerpt", statement), "evidence_excerpt", minimum=8), "urgency_cues": list(raw.get("urgency_cues") or []), "payment_cues": list(raw.get("payment_cues") or [])}
                record["signals"].append(signal);existing.add(fingerprint)
            record["stage"] = "00B";record["state"] = "signals_collected";record["lineage"].append({"stage": "00B", "at": _now(), "action": "signals_added", "count": len(record["signals"])})
            return self.save(record)

    def add_validation(self, discovery_id: str, outcomes: list[dict[str, Any]]) -> dict[str, Any]:
        with _LOCK:
            record = self.load(discovery_id)
            for raw in outcomes:
                kind = _text(raw.get("commitment_type"), "commitment_type")
                if kind not in _COMMITMENTS:
                    raise DiscoveryError(f"commitment_type must be one of {sorted(_COMMITMENTS)}")
                count = int(raw.get("count", 0))
                if count < 1:
                    raise DiscoveryError("validation count must be positive")
                source_url = _text(raw.get("source_url"), "source_url")
                if urlparse(source_url).scheme not in {"http", "https"}:
                    raise DiscoveryError("validation source_url must be HTTP(S)")
                record["validation_outcomes"].append({"outcome_id": _id("vout"), "commitment_type": kind, "count": count, "source_url": source_url, "observed_at": _text(raw.get("observed_at"), "observed_at"), "notes": str(raw.get("notes") or "")})
            record["lineage"].append({"stage": "00F", "at": _now(), "action": "validation_outcomes_added"})
            return self.save(record)

    def evaluate(self, discovery_id: str) -> dict[str, Any]:
        with _LOCK:
            record = self.load(discovery_id)
            signals = record["signals"]
            domains = {x["source_domain"] for x in signals}
            token_counts = Counter(t for s in signals for t in _tokens(s["problem_statement"]))
            themes = [x for x, _ in token_counts.most_common(6)] or _tokens(record["brief"]["problem_territory"])[:6]
            clusters = []
            if signals:
                clusters.append({"cluster_id": _id("need"), "label": " ".join(themes[:4]).title(), "themes": themes, "signal_ids": [s["signal_id"] for s in signals], "source_domains": sorted(domains), "signal_count": len(signals)})
            record["clusters"] = clusters;record["stage"] = "00C"
            corpus = " ".join(s["problem_statement"] + " " + " ".join(s["urgency_cues"] + s["payment_cues"]) for s in signals).lower()
            urgency = sum(1 for x in _URGENCY if x in corpus)
            payment = sum(1 for x in _PAYMENT if x in corpus)
            score = min(25, len(signals) * 7) + min(20, len(domains) * 10) + min(15, urgency * 5) + min(20, payment * 5) + (10 if record["brief"]["audience"] else 0) + (10 if record["brief"]["geography"] else 0)
            gates = {"minimum_signals": len(signals) >= MIN_SIGNALS, "independent_domains": len(domains) >= MIN_DOMAINS, "commercial_evidence": payment > 0, "score_threshold": score >= PASS_SCORE}
            record["opportunity"] = {"score": score, "threshold": PASS_SCORE, "gates": gates, "decision": "strong" if all(gates.values()) else "weak", "rationale": {"signal_count": len(signals), "domain_count": len(domains), "urgency_cues": urgency, "payment_cues": payment}}
            record["stage"] = "00D"
            if not all(gates.values()):
                record["state"] = "rejected_criteria_miss";record["contract"] = None;record["lineage"].append({"stage": "00D", "at": _now(), "action": "opportunity_rejected", "score": score});return self.save(record)
            problem = clusters[0]["label"]
            model = record["brief"]["commercial_model"]
            record["offer"] = {"status": "hypothesis", "name": f"{problem} solution", "product_type": "subscription_app" if "subscription" in model.lower() else "service", "target_customer": record["brief"]["audience"], "problem": problem, "minimum_features": [f"Track {x}" for x in themes[:3]], "value_proposition": f"Help {record['brief']['audience']} reduce {record['brief']['problem_territory']}", "commercial_model": model, "conversion_objective": "qualified_waitlist_or_demo_request", "claims_status": "hypothesis_only"}
            record["stage"] = "00E";commitments = sum(x["count"] for x in record["validation_outcomes"] if x["commitment_type"] in _COMMITMENTS)
            validation_gates = {"demand_gate": True, "buyer_gate": True, "pain_gate": urgency > 0, "payment_gate": payment > 0, "solution_gate": bool(record["offer"]["minimum_features"]), "economics_gate": model.lower() != "undecided", "commitment_gate": commitments >= MIN_COMMITMENTS}
            record["stage"] = "00F"
            if not all(validation_gates.values()):
                record["state"] = "awaiting_validation";record["contract"] = None;record["validation"] = {"gates": validation_gates, "commitments": commitments, "required_commitments": MIN_COMMITMENTS};record["lineage"].append({"stage": "00F", "at": _now(), "action": "validation_incomplete"});return self.save(record)
            record["validation"] = {"gates": validation_gates, "commitments": commitments, "required_commitments": MIN_COMMITMENTS}
            record["contract"] = {"schema": SCHEMA, "contract_id": _id("voc"), "originating_branch": "discovery", "problem": record["offer"]["problem"], "audience": record["brief"]["audience"], "geography": record["brief"]["geography"], "offer": record["offer"], "real_demand_evidence": [{"signal_id": x["signal_id"], "source_url": x["source_url"], "observed_at": x["observed_at"]} for x in signals], "validation_evidence": record["validation_outcomes"], "permitted_claims": ["Concept/prototype", "Features are proposed"], "unresolved_assumptions": [], "commercial_model": model, "conversion_objective": record["offer"]["conversion_objective"], "success_criteria": f"At least {MIN_COMMITMENTS} qualified commitments", "rejection_criteria": f"Score below {PASS_SCORE} or fewer than {MIN_COMMITMENTS} commitments", "created_at": _now()}
            record["state"] = "validated_ready_to_merge";record["lineage"].append({"stage": "00F", "at": _now(), "action": "contract_validated", "contract_id": record["contract"]["contract_id"]})
            return self.save(record)
