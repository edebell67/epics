"""Versioned point-in-time market-feature evidence store.

VERSION HISTORY
v1.0.1 (2026-09-04) - Relocated from epics/ep_051_strategy_directory/hosted_directory/ to epics/ep_049_strategy_intelligence/hosted_directory/ per Ed's EP049 ownership decision. No code changes.
v1.0.0 · 2026-08-24 · Adds immutable feature snapshots, freshness gates and as-of lookup.
"""
from __future__ import annotations
from datetime import datetime,timezone
from bisect import bisect_right
import hashlib,json,math


MARKET_CACHE_SCHEMA_VERSION="1.0.0"


def validate_market_cache(payload,now=None):
    """Validate a complete, content-addressed market cache before any row is ingested."""
    if not isinstance(payload,dict) or payload.get("schema_version")!=MARKET_CACHE_SCHEMA_VERSION:
        raise ValueError("unsupported market cache schema")
    rows=payload.get("features")
    if not isinstance(rows,list) or not rows:raise ValueError("market cache has no feature rows")
    expected=payload.get("sha256")
    unsigned={key:value for key,value in payload.items() if key!="sha256"}
    actual=hashlib.sha256(json.dumps(unsigned,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
    if not isinstance(expected,str) or not hmac_compare(expected,actual):raise ValueError("market cache digest mismatch")
    ceiling=_time(now or datetime.now(timezone.utc));seen=set();previous=None
    for row in rows:
        if not isinstance(row,dict) or not {"market","as_of","features","source_version"}<=row.keys():
            raise ValueError("invalid market feature row")
        at=_time(row["as_of"]);key=(str(row["market"]),at)
        if at>ceiling:raise ValueError("future feature snapshots are not accepted")
        if key in seen:raise ValueError("duplicate market feature row")
        if previous is not None and at<previous:raise ValueError("market feature rows are not chronological")
        if not isinstance(row["features"],dict) or not row["features"]:raise ValueError("market feature values are missing")
        values=[float(value) for value in row["features"].values() if value is not None]
        if not values or any(not math.isfinite(value) for value in values):raise ValueError("market features must be finite")
        seen.add(key);previous=at
    return payload


def hmac_compare(left,right):
    """Constant-time comparison without exposing cache digests in errors."""
    import hmac
    return hmac.compare_digest(left,right)


def _time(value):
    parsed=value if isinstance(value,datetime) else datetime.fromisoformat(str(value).replace("Z","+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def freshness_limit(at,weekday_seconds=129600,weekend_seconds=345600):
    """Allow the last business-day observation through weekends and Monday publication time."""
    timestamp=_time(at)
    return weekend_seconds if timestamp.weekday() in {0,5,6} else weekday_seconds


class MarketFeatureStore:
    def __init__(self):self._rows={};self._labels={}
    def ingest(self,market,as_of,features,source_version):
        timestamp=_time(as_of)
        if timestamp>datetime.now(timezone.utc):raise ValueError("future feature snapshots are not accepted")
        clean={key:float(value) for key,value in features.items() if value is not None}
        if any(not math.isfinite(value) for value in clean.values()):raise ValueError("market features must be finite")
        payload=json.dumps({"market":market,"as_of":timestamp.isoformat(),"features":clean,"source_version":source_version},sort_keys=True,separators=(",",":"))
        digest=hashlib.sha256(payload.encode()).hexdigest();key=(market,timestamp)
        if key in self._rows and self._rows[key]["sha256"]!=digest:raise ValueError("point-in-time feature snapshot is immutable")
        self._rows[key]={"market":market,"as_of":timestamp,"features":clean,"source_version":source_version,"sha256":digest}
        return digest
    def as_of(self,market,at):
        timestamp=_time(at);eligible=[row for (name,when),row in self._rows.items() if name==market and when<=timestamp]
        return None if not eligible else max(eligible,key=lambda row:row["as_of"])
    def current(self,market,now,max_age_seconds=3600):
        timestamp=_time(now);row=self.as_of(market,timestamp)
        if row is None:return {"state":"UNAVAILABLE","fresh":False}
        age=(timestamp-row["as_of"]).total_seconds()
        return {**row,"age_seconds":age,"fresh":0<=age<=max_age_seconds,"state":"CURRENT" if 0<=age<=max_age_seconds else "STALE"}
    def history(self,market,through=None):
        limit=_time(through) if through is not None else datetime.max.replace(tzinfo=timezone.utc)
        return sorted((row for (name,when),row in self._rows.items() if name==market and when<=limit),key=lambda row:row["as_of"])
    def record_label(self,market,as_of,result,feature_as_of,classifier_version="1.0.0"):
        timestamp=_time(as_of);key=(market,timestamp,classifier_version);payload={"market":market,"as_of":timestamp,"feature_as_of":_time(feature_as_of),"classifier_version":classifier_version,**result}
        existing=self._labels.get(key)
        if existing and existing!=payload:raise ValueError("point-in-time regime label is immutable")
        self._labels[key]=payload;return payload
    def label_as_of(self,market,at):
        timestamp=_time(at);rows=[row for (name,when,_),row in self._labels.items() if name==market and when<=timestamp]
        return None if not rows else max(rows,key=lambda row:row["as_of"])


class PostgresMarketFeatureStore:
    def __init__(self,database_url):self.database_url=database_url
    def _connect(self):
        import psycopg
        return psycopg.connect(self.database_url)
    def ingest(self,market,as_of,features,source_version):
        timestamp=_time(as_of)
        if timestamp>datetime.now(timezone.utc):raise ValueError("future feature snapshots are not accepted")
        clean={key:float(value) for key,value in features.items() if value is not None}
        if any(not math.isfinite(value) for value in clean.values()):raise ValueError("market features must be finite")
        payload=json.dumps({"market":market,"as_of":timestamp.isoformat(),"features":clean,"source_version":source_version},sort_keys=True,separators=(",",":"));digest=hashlib.sha256(payload.encode()).hexdigest()
        with self._connect() as conn,conn.cursor() as cur:
            cur.execute("INSERT INTO intelligence_market_feature(market,as_of,source_version,features,sha256) VALUES(%s,%s,%s,%s::jsonb,%s) ON CONFLICT(market,as_of) DO NOTHING RETURNING sha256",(market,timestamp,source_version,json.dumps(clean),digest));inserted=cur.fetchone()
            if inserted is None:
                cur.execute("SELECT sha256 FROM intelligence_market_feature WHERE market=%s AND as_of=%s",(market,timestamp));winner=cur.fetchone()
                if not winner or winner[0]!=digest:raise ValueError("point-in-time feature snapshot is immutable")
        return digest
    def as_of(self,market,at):
        with self._connect() as conn,conn.cursor() as cur:
            cur.execute("SELECT market,as_of,features,source_version,sha256 FROM intelligence_market_feature WHERE market=%s AND as_of<=%s ORDER BY as_of DESC LIMIT 1",(market,_time(at)));row=cur.fetchone()
        return None if not row else {"market":row[0],"as_of":row[1],"features":row[2],"source_version":row[3],"sha256":row[4]}
    def current(self,market,now,max_age_seconds=3600):
        timestamp=_time(now);row=self.as_of(market,timestamp)
        if row is None:return {"state":"UNAVAILABLE","fresh":False}
        age=(timestamp-row["as_of"]).total_seconds();return {**row,"age_seconds":age,"fresh":0<=age<=max_age_seconds,"state":"CURRENT" if 0<=age<=max_age_seconds else "STALE"}
    def history(self,market,through=None):
        limit=_time(through) if through is not None else datetime.max.replace(tzinfo=timezone.utc)
        with self._connect() as conn,conn.cursor() as cur:
            cur.execute("SELECT market,as_of,features,source_version,sha256 FROM intelligence_market_feature WHERE market=%s AND as_of<=%s ORDER BY as_of",(market,limit));rows=cur.fetchall()
        return [{"market":row[0],"as_of":row[1],"features":row[2],"source_version":row[3],"sha256":row[4]} for row in rows]
    def record_label(self,market,as_of,result,feature_as_of,classifier_version="1.0.0"):
        with self._connect() as conn,conn.cursor() as cur:
            cur.execute("""INSERT INTO intelligence_regime_label(market,as_of,classifier_version,state,probabilities,feature_as_of,confidence)
              VALUES(%s,%s,%s,%s,%s::jsonb,%s,%s) ON CONFLICT(market,as_of,classifier_version) DO NOTHING""",(market,_time(as_of),classifier_version,result["state"],json.dumps(result.get("probabilities",{})),_time(feature_as_of),result["confidence"]))
        return {"market":market,"as_of":_time(as_of),"feature_as_of":_time(feature_as_of),"classifier_version":classifier_version,**result}
    def label_as_of(self,market,at):
        with self._connect() as conn,conn.cursor() as cur:
            cur.execute("SELECT market,as_of,classifier_version,state,probabilities,feature_as_of,confidence FROM intelligence_regime_label WHERE market=%s AND as_of<=%s ORDER BY as_of DESC LIMIT 1",(market,_time(at)));row=cur.fetchone()
        return None if not row else {"market":row[0],"as_of":row[1],"classifier_version":row[2],"state":row[3],"probabilities":row[4],"feature_as_of":row[5],"confidence":float(row[6])}


def join_regimes_without_lookahead(returns,regime_rows):
    """Attach only the latest regime known at each return timestamp."""
    labels=sorted(regime_rows,key=lambda row:_time(row["as_of"]));joined=[]
    for item in sorted(returns,key=lambda row:_time(row["timestamp"])):
        at=_time(item["timestamp"]);eligible=[row for row in labels if _time(row["as_of"])<=at]
        if eligible:joined.append({**item,"regime":eligible[-1]["state"],"regime_as_of":_time(eligible[-1]["as_of"]).isoformat()})
    return joined


def join_regimes_bisect(returns,sorted_labels):
    """Same no-lookahead semantics as join_regimes_without_lookahead, but
    O(n log m) via bisect instead of O(n*m) - needed to join many strategies'
    trade points against a long (years of daily rows) regime-label history in
    one bulk pass without it becoming the dominant cost. `sorted_labels` must
    already be sorted by as_of (build once per request, reuse across every
    strategy) - pass the return value of build_regime_label_index()."""
    times,states=sorted_labels;joined=[]
    for item in sorted(returns,key=lambda row:_time(row["timestamp"])):
        at=_time(item["timestamp"]);idx=bisect_right(times,at)-1
        if idx>=0:joined.append({**item,"regime":states[idx],"regime_as_of":times[idx].isoformat()})
    return joined


def build_regime_label_index(regime_rows):
    """Sort a market's classified regime-label history once into parallel
    (times, states) arrays for join_regimes_bisect to bisect against."""
    ordered=sorted(regime_rows,key=lambda row:_time(row["as_of"]))
    return [_time(row["as_of"]) for row in ordered],[row["state"] for row in ordered]
