"""Tenant-isolated user intelligence objects and privacy lifecycle.

VERSION HISTORY
v1.0.1 (2026-09-04) - Relocated from epics/ep_051_strategy_directory/hosted_directory/ to epics/ep_049_strategy_intelligence/hosted_directory/ per Ed's EP049 ownership decision. No code changes.
v1.1.0 · 2026-08-24 · Adds consent state, evidence-version snapshots and deterministic replay metadata.
v1.0.0 · 2026-08-24 · Watchlists, saved plans, collections, preferences, export and deletion services.
"""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime,timezone
from uuid import uuid4
import json
from contextlib import contextmanager


class UserIntelligenceStore:
    """Repository contract used until a production identity-backed PostgreSQL adapter is enabled."""
    def __init__(self):self._users={}
    def _bucket(self,user_id):return self._users.setdefault(user_id,{"watchlist":set(),"watch_versions":{},"searches":{},"collections":{},"preferences":{},"history":[],"consent":{"history":False},"audit":[]})
    def _audit(self,user_id,action):self._bucket(user_id)["audit"].append({"action":action,"at":datetime.now(timezone.utc).isoformat()})
    def watch(self,user_id,strategy_id,evidence_version=None):
        bucket=self._bucket(user_id);bucket["watchlist"].add(strategy_id);bucket["watch_versions"][strategy_id]=evidence_version;self._audit(user_id,"watch")
    def unwatch(self,user_id,strategy_id):
        bucket=self._bucket(user_id);bucket["watchlist"].discard(strategy_id);bucket["watch_versions"].pop(strategy_id,None);self._audit(user_id,"unwatch")
    def save_search(self,user_id,name,plan):
        item_id=str(uuid4());self._bucket(user_id)["searches"][item_id]={"id":item_id,"name":name,"plan":deepcopy(plan),"schema_version":"1.0.0","created_at":datetime.now(timezone.utc).isoformat()};self._audit(user_id,"save_search");return item_id
    def create_collection(self,user_id,name,strategy_ids,notes="",evidence_versions=None):
        item_id=str(uuid4());self._bucket(user_id)["collections"][item_id]={"id":item_id,"name":name,"strategy_ids":list(dict.fromkeys(strategy_ids)),"notes":notes,"evidence_versions":deepcopy(evidence_versions or {}),"created_at":datetime.now(timezone.utc).isoformat()};self._audit(user_id,"create_collection");return item_id
    def set_preferences(self,user_id,preferences):self._bucket(user_id)["preferences"]=deepcopy(preferences);self._audit(user_id,"set_preferences")
    def set_consent(self,user_id,history:bool):
        bucket=self._bucket(user_id);bucket["consent"]["history"]=bool(history)
        if not history:bucket["history"].clear()
        self._audit(user_id,"consent_history_on" if history else "consent_history_off")
    def record(self,user_id,event,consented=None):
        allowed=self._bucket(user_id)["consent"]["history"] if consented is None else bool(consented)
        if allowed:self._bucket(user_id)["history"].append({"event":deepcopy(event),"at":datetime.now(timezone.utc).isoformat()})
    def export(self,user_id):
        bucket=deepcopy(self._bucket(user_id));bucket["watchlist"]=sorted(bucket["watchlist"]);return bucket
    def replay_search(self,user_id,item_id,result_ids):
        item=self._bucket(user_id)["searches"].get(item_id)
        if item is None:return None
        previous=item.get("last_result_ids",[]);item["last_result_ids"]=list(result_ids);item["last_replayed_at"]=datetime.now(timezone.utc).isoformat();self._audit(user_id,"replay_search");return {"plan":deepcopy(item["plan"]),"previous_result_ids":previous}
    def purge_expired(self):return 0
    def delete(self,user_id):self._users.pop(user_id,None)
    def reset_preferences(self,user_id):self._bucket(user_id)["preferences"]={};self._audit(user_id,"reset_preferences")


class PostgresUserIntelligenceStore:
    """Durable tenant store with transaction-local PostgreSQL RLS identity."""
    def __init__(self,database_url,connect=None,verify_boundary=True,maintenance_database_url=None):
        self.database_url=database_url;self.maintenance_database_url=maintenance_database_url;self._connector=connect
        if verify_boundary:self.verify_security_boundary()
    def _connect(self):
        if self._connector:return self._connector()
        import psycopg
        return psycopg.connect(self.database_url)
    @contextmanager
    def _tx(self,user_id):
        with self._connect() as conn,conn.cursor() as cur:
            cur.execute("SELECT set_config('app.user_id',%s,true)",(user_id,));yield cur
    def verify_security_boundary(self):
        with self._connect() as conn,conn.cursor() as cur:
            cur.execute("""SELECT r.rolsuper,r.rolbypassrls,EXISTS(
              SELECT 1 FROM pg_class c WHERE c.relname='intelligence_watchlist' AND c.relowner=r.oid)
              FROM pg_roles r WHERE r.rolname=current_user""")
            row=cur.fetchone()
        if not row or any(row):raise RuntimeError("Unsafe PostgreSQL runtime role: private intelligence requires non-owner NOSUPERUSER NOBYPASSRLS")
    def _audit(self,cur,user_id,action):
        cur.execute("INSERT INTO intelligence_privacy_audit(owner_id,action) VALUES(%s,%s)",(user_id,action))
    def watch(self,user_id,strategy_id,evidence_version=None):
        with self._tx(user_id) as cur:
            cur.execute("""INSERT INTO intelligence_watchlist(owner_id,strategy_id,evidence_version) VALUES(%s,%s,%s)
              ON CONFLICT(owner_id,strategy_id) DO UPDATE SET evidence_version=excluded.evidence_version""",(user_id,strategy_id,evidence_version));self._audit(cur,user_id,"watch")
    def unwatch(self,user_id,strategy_id):
        with self._tx(user_id) as cur:cur.execute("DELETE FROM intelligence_watchlist WHERE owner_id=%s AND strategy_id=%s",(user_id,strategy_id));self._audit(cur,user_id,"unwatch")
    def save_search(self,user_id,name,plan):
        item_id=str(uuid4())
        with self._tx(user_id) as cur:
            cur.execute("INSERT INTO intelligence_saved_search(saved_search_id,owner_id,name,schema_version,canonical_plan) VALUES(%s,%s,%s,'1.0.0',%s::jsonb)",(item_id,user_id,name,json.dumps(plan)));self._audit(cur,user_id,"save_search")
        return item_id
    def create_collection(self,user_id,name,strategy_ids,notes="",evidence_versions=None):
        item_id=str(uuid4());versions=evidence_versions or {}
        with self._tx(user_id) as cur:
            cur.execute("INSERT INTO intelligence_collection(collection_id,owner_id,name,notes) VALUES(%s,%s,%s,%s)",(item_id,user_id,name,notes))
            for strategy_id in dict.fromkeys(strategy_ids):cur.execute("INSERT INTO intelligence_collection_strategy(collection_id,owner_id,strategy_id,evidence_version) VALUES(%s,%s,%s,%s)",(item_id,user_id,strategy_id,versions.get(strategy_id)))
            self._audit(cur,user_id,"create_collection")
        return item_id
    def set_preferences(self,user_id,preferences):
        with self._tx(user_id) as cur:
            cur.execute("""INSERT INTO intelligence_preference(owner_id,explicit_preferences,derivation_version) VALUES(%s,%s::jsonb,'1.0.0')
              ON CONFLICT(owner_id) DO UPDATE SET explicit_preferences=excluded.explicit_preferences,derivation_version='1.0.0',updated_at=now()""",(user_id,json.dumps(preferences)));self._audit(cur,user_id,"set_preferences")
    def set_consent(self,user_id,history):
        with self._tx(user_id) as cur:
            cur.execute("""INSERT INTO intelligence_user_consent(owner_id,history_enabled) VALUES(%s,%s)
              ON CONFLICT(owner_id) DO UPDATE SET history_enabled=excluded.history_enabled,changed_at=now()""",(user_id,bool(history)))
            if not history:cur.execute("DELETE FROM intelligence_user_history WHERE owner_id=%s",(user_id,))
            self._audit(cur,user_id,"consent_history_on" if history else "consent_history_off")
    def record(self,user_id,event,consented=None):
        with self._tx(user_id) as cur:
            if consented is None:
                cur.execute("SELECT history_enabled FROM intelligence_user_consent WHERE owner_id=%s",(user_id,));row=cur.fetchone();allowed=bool(row and row[0])
            else:allowed=bool(consented)
            if allowed:cur.execute("INSERT INTO intelligence_user_history(event_id,owner_id,event_type,event_payload,expires_at) VALUES(%s,%s,%s,%s::jsonb,now()+interval '90 days')",(str(uuid4()),user_id,str(event.get("type","interaction"))[:80],json.dumps(event)))
    def export(self,user_id):
        with self._tx(user_id) as cur:
            cur.execute("SELECT strategy_id,evidence_version FROM intelligence_watchlist WHERE owner_id=%s ORDER BY strategy_id",(user_id,));watch_rows=cur.fetchall();watchlist=[row[0] for row in watch_rows];watch_versions={row[0]:row[1] for row in watch_rows}
            cur.execute("SELECT saved_search_id,name,canonical_plan,schema_version,created_at,last_result_ids,last_replayed_at FROM intelligence_saved_search WHERE owner_id=%s ORDER BY created_at",(user_id,));searches={str(row[0]):{"id":str(row[0]),"name":row[1],"plan":row[2],"schema_version":row[3],"created_at":row[4].isoformat(),"last_result_ids":row[5] or [],"last_replayed_at":row[6].isoformat() if row[6] else None} for row in cur.fetchall()}
            cur.execute("""SELECT c.collection_id,c.name,c.notes,c.created_at,COALESCE(jsonb_agg(jsonb_build_object('strategy_id',s.strategy_id,'evidence_version',s.evidence_version)) FILTER(WHERE s.strategy_id IS NOT NULL),'[]')
              FROM intelligence_collection c LEFT JOIN intelligence_collection_strategy s ON s.collection_id=c.collection_id AND s.owner_id=c.owner_id
              WHERE c.owner_id=%s GROUP BY c.collection_id ORDER BY c.created_at""",(user_id,));collections={}
            for row in cur.fetchall():
                members=row[4];collections[str(row[0])]={"id":str(row[0]),"name":row[1],"notes":row[2],"created_at":row[3].isoformat(),"strategy_ids":[x["strategy_id"] for x in members],"evidence_versions":{x["strategy_id"]:x["evidence_version"] for x in members if x["evidence_version"] is not None}}
            cur.execute("SELECT explicit_preferences FROM intelligence_preference WHERE owner_id=%s",(user_id,));row=cur.fetchone();preferences={} if not row else row[0]
            cur.execute("SELECT history_enabled FROM intelligence_user_consent WHERE owner_id=%s",(user_id,));row=cur.fetchone();consent={"history":bool(row and row[0])}
            cur.execute("SELECT event_payload,occurred_at FROM intelligence_user_history WHERE owner_id=%s AND expires_at>now() ORDER BY occurred_at",(user_id,));history=[{"event":row[0],"at":row[1].isoformat()} for row in cur.fetchall()]
            cur.execute("SELECT action,occurred_at FROM intelligence_privacy_audit WHERE owner_id=%s ORDER BY occurred_at",(user_id,));audit=[{"action":row[0],"at":row[1].isoformat()} for row in cur.fetchall()]
        return {"watchlist":watchlist,"watch_versions":watch_versions,"searches":searches,"collections":collections,"preferences":preferences,"history":history,"consent":consent,"audit":audit}
    def replay_search(self,user_id,item_id,result_ids):
        with self._tx(user_id) as cur:
            cur.execute("SELECT canonical_plan,last_result_ids FROM intelligence_saved_search WHERE owner_id=%s AND saved_search_id=%s",(user_id,item_id));row=cur.fetchone()
            if not row:return None
            cur.execute("UPDATE intelligence_saved_search SET last_result_ids=%s::jsonb,last_replayed_at=now(),updated_at=now() WHERE owner_id=%s AND saved_search_id=%s",(json.dumps(result_ids),user_id,item_id));self._audit(cur,user_id,"replay_search")
        return {"plan":row[0],"previous_result_ids":row[1] or []}
    def purge_expired(self):
        if not self.maintenance_database_url:raise RuntimeError("A dedicated maintenance database role is required for cross-owner retention purge")
        import psycopg
        with psycopg.connect(self.maintenance_database_url) as conn,conn.cursor() as cur:
            cur.execute("SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user");role=cur.fetchone()
            if not role or role[0] or role[1]:raise RuntimeError("Maintenance role must be NOSUPERUSER and NOBYPASSRLS")
            cur.execute("SELECT has_function_privilege(current_user,'public.intelligence_purge_expired_history()','EXECUTE')");function_grant=cur.fetchone()
            private_tables=("intelligence_user_consent","intelligence_watchlist","intelligence_saved_search","intelligence_collection","intelligence_collection_strategy","intelligence_preference","intelligence_user_history","intelligence_privacy_audit")
            cur.execute("SELECT rel,has_table_privilege(current_user,rel,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'),has_any_column_privilege(current_user,rel,'SELECT,INSERT,UPDATE,REFERENCES') FROM unnest(%s::text[]) AS rel",(list(private_tables),));table_grants=cur.fetchall()
            if not function_grant or not function_grant[0] or any(table_grant or column_grant for _,table_grant,column_grant in table_grants):raise RuntimeError("Maintenance role requires only EXECUTE on intelligence_purge_expired_history() and no private-table or column privileges")
            cur.execute("SELECT public.intelligence_purge_expired_history()");row=cur.fetchone();return int(row[0])
    def delete(self,user_id):
        tables=("intelligence_collection_strategy","intelligence_collection","intelligence_saved_search","intelligence_watchlist","intelligence_preference","intelligence_user_history","intelligence_user_consent","intelligence_privacy_audit")
        with self._tx(user_id) as cur:
            for table in tables:cur.execute(f"DELETE FROM {table} WHERE owner_id=%s",(user_id,))
    def reset_preferences(self,user_id):
        with self._tx(user_id) as cur:cur.execute("DELETE FROM intelligence_preference WHERE owner_id=%s",(user_id,));self._audit(cur,user_id,"reset_preferences")


def preference_trace(explicit:dict,events:list[dict])->dict:
    inferred={}
    for item in events:
        market=item.get("market")
        if market:inferred[market]=inferred.get(market,0)+1
    return {"explicit":deepcopy(explicit),"inferred_market_counts":inferred,"derivation_version":"1.0.0","resettable":True}
