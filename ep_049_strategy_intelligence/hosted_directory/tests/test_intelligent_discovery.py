# VERSION HISTORY
# v1.2.0 · 2026-08-24 · Adds unit and regime fail-closed discovery coverage.
# v1.1.0 · 2026-08-24 · Adds interpretation API contract coverage.
# v1.0.0 · 2026-08-24 · Query interpretation, equivalence, retrieval and fail-closed constraint tests.
import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app
from app.intelligence.discovery import StrategyQuery,interpret,retrieve


def sample_profile(strategy_id="DNA_1",win=.65,sharpe=1.8,drawdown=-.08,annual=.25,years=6):
    names={"win_rate":win,"sharpe":sharpe,"max_drawdown":drawdown,"annualized_return":annual}
    units={"annualized_return":"fraction/year","max_drawdown":"fraction","win_rate":"fraction","sharpe":"ratio"}
    return {"identity":{"strategy_id":strategy_id},"classification":{"asset_class":"equity","instruments":["NASDAQ"]},
            "metrics":{k:{"value":v,"unit":units[k]} for k,v in names.items()},"evidence":{"years":years,"confidence":.9},"score":{"quality_score":90},"regimes":{}}


def test_natural_language_translates_to_canonical_plan():
    plan=interpret("Show me stock strategies with win rate over 60%, annual return above 20%, drawdown below 10%, Sharpe above 1.5 and at least 5 years history")
    assert plan==StrategyQuery(asset_class="equity",min_win_rate=.6,min_annualized_return=.2,annualized_return_unit="fraction/year",max_drawdown=.1,max_drawdown_unit="fraction",min_sharpe=1.5,min_track_record_years=5)


def test_natural_language_recognises_years_of_evidence():
    assert interpret("FX strategies with at least 1 year of evidence").min_track_record_years==1


def test_structured_and_language_plan_retrieve_same_candidates():
    profiles=[sample_profile(),sample_profile("DNA_2",win=.4)]
    structured=StrategyQuery(asset_class="equity",min_win_rate=.6,max_drawdown=.1,max_drawdown_unit="fraction")
    language=interpret("stock strategies with win rate above 60% and drawdown below 10%")
    assert [x["profile"]["identity"]["strategy_id"] for x in retrieve(profiles,structured)]==[x["profile"]["identity"]["strategy_id"] for x in retrieve(profiles,language)]==["DNA_1"]


def test_constraints_are_applied_before_ranking():
    bad=sample_profile("DNA_BAD",win=.1);bad["score"]["quality_score"]=100
    results=retrieve([bad,sample_profile()],StrategyQuery(min_win_rate=.6))
    assert [x["profile"]["identity"]["strategy_id"] for x in results]==["DNA_1"]


def test_query_schema_rejects_invalid_bounds():
    with pytest.raises(ValueError):StrategyQuery(min_win_rate=1.2)
    with pytest.raises(ValueError):StrategyQuery(annualized_return_unit="money/year")


def test_percentage_constraint_never_compares_to_money_metric():
    profile=sample_profile();profile["metrics"]["annualized_return"]["unit"]="money/year";profile["metrics"]["annualized_return"]["value"]=100000
    assert retrieve([profile],interpret("stock strategy with annual return above 20%"))==[]


def test_regime_constraint_is_enforced_and_requires_valid_evidence():
    profile=sample_profile();plan=StrategyQuery(regime="bull")
    assert retrieve([profile],plan)==[]
    profile["regimes"]={"bull / low volatility":{"confidence":"COLLECTING"}};assert retrieve([profile],plan)==[]
    profile["regimes"]["bull / low volatility"]["confidence"]="VALID";assert len(retrieve([profile],plan))==1


def test_interpretation_api_returns_only_validated_query_plan():
    client=TestClient(create_app(settings=Settings(data_backend="memory")))
    response=client.post("/api/intelligence/query/interpret",json={"query":"FX strategies with win rate above 60%"})
    assert response.status_code==200
    assert response.json()["plan"]["asset_class"]=="FX"
    assert response.json()["plan"]["min_win_rate"]==.6
