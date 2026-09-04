# VERSION HISTORY
# v1.0.0 · 2026-08-24 · Private-object isolation and fail-closed regime API contracts.
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app


def client():
    return TestClient(create_app(settings=Settings(data_backend="memory",intelligence_user_token="secret",sync_token="publisher")))


def auth(user):
    return {"Authorization":"Bearer secret","X-User-ID":user}


def test_private_intelligence_requires_configured_trusted_identity():
    unconfigured=TestClient(create_app(settings=Settings(data_backend="memory")))
    assert unconfigured.get("/api/intelligence/user",headers={"X-User-ID":"a"}).status_code==503
    assert client().get("/api/intelligence/user",headers={"Authorization":"Bearer wrong","X-User-ID":"a"}).status_code==401


def test_watchlists_and_collections_are_isolated_through_api():
    c=client()
    assert c.put("/api/intelligence/user/watchlist/DNA_1",headers=auth("a")).status_code==200
    created=c.post("/api/intelligence/user/collections",headers=auth("a"),json={"name":"Core","strategy_ids":["DNA_1"],"evidence_versions":{"DNA_1":"v1"}})
    assert created.status_code==201
    assert c.get("/api/intelligence/user",headers=auth("a")).json()["watchlist"]==["DNA_1"]
    assert c.get("/api/intelligence/user",headers=auth("b")).json()["watchlist"]==[]


def test_consent_revocation_clears_history_and_user_delete_is_complete():
    c=client();c.put("/api/intelligence/user/consent",headers=auth("a"),json={"history":True})
    c.put("/api/intelligence/user/consent",headers=auth("a"),json={"history":False})
    assert c.get("/api/intelligence/user",headers=auth("a")).json()["history"]==[]
    assert c.delete("/api/intelligence/user",headers=auth("a")).status_code==204
    assert c.get("/api/intelligence/user",headers=auth("a")).json()["watchlist"]==[]


def test_regime_api_fails_closed_for_stale_or_incomplete_features():
    c=client();missing=c.post("/api/intelligence/regimes/classify",json={"market":"FX","as_of":"2026-08-24T10:00:00Z"}).json()
    assert missing["state"]=="UNKNOWN" and missing["reason"]=="NO_CANONICAL_FEATURES"
    fabricated=c.post("/api/intelligence/regimes/classify",json={"market":"FX","as_of":"2026-08-24T10:00:00Z","features":{"trend":1},"stale":False})
    assert fabricated.status_code==422


def test_recommendation_api_returns_only_evidence_valid_candidates():
    c=client()
    fabricated=c.post("/api/intelligence/recommendations",json={"current":{"state":"bull","confidence":1},"candidates":[]})
    assert fabricated.status_code==422
    result=c.post("/api/intelligence/recommendations",json={"market":"FX","strategy_ids":["DNA_1"],"risk_limit":.2})
    assert result.status_code==200 and result.json()["items"]==[]
    assert result.json()["reason"]=="NO_CANONICAL_FEATURES" and result.json()["decision_support_only"] is True
