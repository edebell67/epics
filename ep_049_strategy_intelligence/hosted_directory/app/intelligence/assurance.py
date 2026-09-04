"""Deterministic intelligence evaluation, SLO and release-gate primitives.

VERSION HISTORY
v1.0.1 (2026-09-04) - Relocated from epics/ep_051_strategy_directory/hosted_directory/ to epics/ep_049_strategy_intelligence/hosted_directory/ per Ed's EP049 ownership decision. No code changes.
v1.0.0 · 2026-08-24 · Adds metric, discovery, recommendation, drift and canary gates.
"""
from __future__ import annotations
import math,time
from copy import deepcopy
from datetime import datetime,timezone
from threading import Lock


def metric_tolerance_report(actual:dict,expected:dict,tolerances:dict)->dict:
    checks=[]
    for name,target in expected.items():
        value=actual.get(name);tolerance=float(tolerances.get(name,0))
        passed=value is not None and math.isfinite(float(value)) and abs(float(value)-float(target))<=tolerance
        checks.append({"metric":name,"actual":value,"expected":target,"tolerance":tolerance,"passed":passed})
    return {"passed":all(item["passed"] for item in checks),"checks":checks}


def discovery_evaluation(cases,interpreter):
    results=[]
    for case in cases:
        actual=interpreter(case["query"]).model_dump(mode="json",exclude_none=True)
        expected={key:value for key,value in case["expected"].items() if value is not None}
        results.append({"id":case["id"],"exact":actual==expected,"actual":actual,"expected":expected})
    exact=sum(item["exact"] for item in results)/len(results) if results else 0
    return {"exact_match":exact,"passed":bool(results) and exact==1,"cases":results}


def rank_invariants(items,score_key="suitability_score"):
    values=[float(item[score_key]) for item in items]
    return {"descending":values==sorted(values,reverse=True),"bounded":all(0<=value<=100 for value in values),"count":len(values)}


def walk_forward_lift(periods,baseline_key="baseline_return",candidate_key="candidate_return"):
    if not periods:return {"passed":False,"lift":None,"periods":0}
    if any(item["trained_through"]>=item["evaluated_from"] for item in periods):return {"passed":False,"lift":None,"periods":len(periods),"reason":"LEAKAGE"}
    candidate=sum(float(item[candidate_key]) for item in periods);baseline=sum(float(item[baseline_key]) for item in periods)
    return {"passed":candidate>baseline,"lift":candidate-baseline,"candidate":candidate,"baseline":baseline,"periods":len(periods)}


class OperationsMonitor:
    def __init__(self,max_samples=10000):self.latencies=[];self.failures=0;self.requests=0;self.freshness={};self.drift={};self.max_samples=max_samples;self._lock=Lock()
    def observe(self,latency_ms,ok=True):
        with self._lock:self.latencies.append(float(latency_ms));self.latencies=self.latencies[-self.max_samples:];self.requests+=1;self.failures+=0 if ok else 1
    def data_state(self,name,age_seconds,max_age_seconds):self.freshness[name]={"age_seconds":age_seconds,"max_age_seconds":max_age_seconds,"ok":age_seconds<=max_age_seconds}
    def drift_state(self,name,current,reference,threshold):
        delta=abs(float(current)-float(reference));self.drift[name]={"delta":delta,"threshold":threshold,"ok":delta<=threshold}
    def report(self,latency_slo_ms=500):
        ordered=sorted(self.latencies);p95=ordered[min(len(ordered)-1,max(0,math.ceil(.95*len(ordered))-1))] if ordered else None
        failure_rate=self.failures/self.requests if self.requests else None;alerts=[]
        if p95 is None or p95>latency_slo_ms:alerts.append("LATENCY_SLO_BREACH")
        if failure_rate is None or failure_rate>.01:alerts.append("ERROR_RATE_SLO_BREACH")
        alerts.extend(f"STALE:{name}" for name,item in self.freshness.items() if not item["ok"]);alerts.extend(f"DRIFT:{name}" for name,item in self.drift.items() if not item["ok"])
        return {"p95_latency_ms":p95,"latency_ok":p95 is not None and p95<=latency_slo_ms,"requests":self.requests,"failures":self.failures,"failure_rate":failure_rate,
                "freshness":self.freshness,"drift":self.drift,"alerts":alerts,"healthy":not alerts}


class ReleaseGate:
    REQUIRED=("metrics","discovery","regime","security","operations","restore","acceptance")
    def decide(self,evidence):
        missing=[name for name in self.REQUIRED if name not in evidence]
        failed=[name for name in self.REQUIRED if name in evidence and not evidence[name].get("passed",False)]
        return {"promote":not missing and not failed,"missing":missing,"failed":failed,"evaluated_at_monotonic":time.monotonic()}


class ReleaseManager:
    """Fail-closed shadow/canary promotion with auditable instant rollback."""
    def __init__(self):self.versions={};self.active=None;self.previous=None;self.audit=[]
    def stage(self,version,evidence,mode="shadow"):
        if mode not in {"shadow","canary"}:raise ValueError("mode must be shadow or canary")
        decision=ReleaseGate().decide(evidence);self.versions[version]={"version":version,"mode":mode,"evidence":deepcopy(evidence),"decision":decision,"staged_at":datetime.now(timezone.utc).isoformat()};self.audit.append({"action":"stage","version":version,"mode":mode,"promotable":decision["promote"]});return deepcopy(self.versions[version])
    def promote(self,version):
        item=self.versions.get(version)
        if not item or not item["decision"]["promote"]:raise ValueError("release evidence is incomplete or failed")
        self.previous=self.active;self.active=version;item["mode"]="public";self.audit.append({"action":"promote","version":version,"previous":self.previous});return self.status()
    def rollback(self):
        if self.previous is None:raise ValueError("no retained release is available")
        target=self.previous;self.previous=self.active;self.active=target;self.audit.append({"action":"rollback","version":target,"retained":self.previous});return self.status()
    def status(self):return {"active":self.active,"previous":self.previous,"versions":deepcopy(self.versions),"audit":deepcopy(self.audit)}
