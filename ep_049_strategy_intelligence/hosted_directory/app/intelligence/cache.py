"""Validated provenance envelope for the local, sanitized intelligence snapshot.

VERSION HISTORY
v1.0.1 (2026-09-04) - Relocated from epics/ep_051_strategy_directory/hosted_directory/ to
epics/ep_049_strategy_intelligence/hosted_directory/ per Ed's EP049 ownership decision. No code changes.
"""
from __future__ import annotations

from datetime import datetime,timezone
import hashlib,json,math

from .models import StrategyIntelligenceProfile

SCHEMA_VERSION="1.0.0"


def validate_local_cache_freshness(payload,max_age_seconds,now=None):
    """Cheap per-request expiry check for a fully validated, unchanged cache file."""
    generated=datetime.fromisoformat(str(payload["generated_at"]).replace("Z","+00:00"));generated=generated if generated.tzinfo else generated.replace(tzinfo=timezone.utc)
    age=((now or datetime.now(timezone.utc))-generated.astimezone(timezone.utc)).total_seconds()
    if age<0 or age>max_age_seconds:raise ValueError("local intelligence cache is stale")
    return payload


def cache_hash(payload):
    body={key:value for key,value in payload.items() if key!="sha256"}
    return hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()


def validate_local_cache(payload,max_age_seconds,now=None):
    if payload.get("schema_version")!=SCHEMA_VERSION or payload.get("profile_depth")!="full":raise ValueError("unsupported local intelligence cache schema")
    if payload.get("sha256")!=cache_hash(payload):raise ValueError("local intelligence cache digest mismatch")
    validate_local_cache_freshness(payload,max_age_seconds,now)
    profiles=[StrategyIntelligenceProfile.model_validate(value) for value in payload.get("profiles",[])];ids=[profile.identity.strategy_id for profile in profiles]
    if not profiles or len(ids)!=len(set(ids)) or len(ids)!=payload.get("catalog_size"):raise ValueError("local intelligence catalogue does not reconcile")
    curves=payload.get("curves")
    if not isinstance(curves,dict) or set(curves)!=set(ids):raise ValueError("local intelligence curve membership does not reconcile")
    by_id={profile.identity.strategy_id:profile for profile in profiles}
    for strategy_id,points in curves.items():
        if len(points)>1000:raise ValueError("local intelligence series exceeds its bound")
        equity=peak=0.0;previous=None
        for number,point in enumerate(points,1):
            observed=datetime.fromisoformat(str(point["closed_at"]).replace("Z","+00:00"));observed=observed if observed.tzinfo else observed.replace(tzinfo=timezone.utc)
            value=float(point["net_return"])
            if previous and observed<previous or not math.isfinite(value):raise ValueError("local intelligence series is invalid")
            previous=observed;equity+=value;peak=max(peak,equity);drawdown=equity-peak
            if int(point["trade_number"])!=number or not math.isclose(float(point["equity"]),equity,abs_tol=1e-6) or not math.isclose(float(point["drawdown"]),drawdown,abs_tol=1e-6):raise ValueError("local intelligence series does not reconcile")
        profile=by_id[strategy_id]
        if profile.evidence.trade_count!=len(points) or not math.isclose(profile.metrics.total_return.value or 0,equity,abs_tol=1e-6):raise ValueError("local profile does not reconcile to its series")
    return payload
