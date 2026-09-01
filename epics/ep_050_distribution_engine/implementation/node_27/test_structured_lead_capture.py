"""Offline Node 19→20→21→26→27 regression; socket construction is prohibited."""
from __future__ import annotations
import socket, sys, tempfile, unittest
from copy import deepcopy
from pathlib import Path
HERE=Path(__file__).resolve(); IMPL=HERE.parents[1]
for node in ("node_19","node_20","node_21","node_26","node_27"): sys.path.insert(0,str(IMPL/node))
from quality_compliance import evaluate_asset_compliance
from publishing_scheduler import build_mock_publication_plan
from search_distribution import build_search_distribution_package
from smart_destination_router import build_route_recommendation
from structured_lead_capture import LeadCaptureConflictError, LeadCaptureValidationError, LocalLeadCaptureRepository, build_structured_lead_record
class CaptureTest(unittest.TestCase):
 def setUp(self):
  self.socket=socket.socket; socket.socket=lambda *a,**k:(_ for _ in ()).throw(AssertionError("network prohibited"))
  import json
  source=json.loads((IMPL/"node_21/fixtures/approved_search_asset_fixture.json").read_text()); result,package=evaluate_asset_compliance(source); self.assertTrue(result.approved)
  plan=build_mock_publication_plan(package.to_dict()); search=build_search_distribution_package(plan,package.to_dict())
  context={"topic":"Safe Boiler Pressure Guide","intent":"diagnostic_quote","geography":"Blackheath","service":"boiler_repair","channel":"search_landing","asset_id":plan["asset_id"],"target_id":plan["target_id"],"opportunity_id":plan["opportunity_id"],"external_action":False,"deferred_channel_context":{"22":"deferred","23":"deferred","24":"deferred","25":"deferred"}}
  self.route=build_route_recommendation(plan,package.to_dict(),search,context); self.intake={"session_id":"session_test_001","source":"search_landing","consent":{"granted":True,"timestamp":"2026-08-17T11:12:00Z","version":"v1","basis":"explicit_opt_in"}}
 def tearDown(self): socket.socket=self.socket
 def record(self): return build_structured_lead_record(self.route,self.intake)
 def test_real_node19_to_27_integration(self):
  r=self.record(); self.assertTrue(r["lead_id"].startswith("slc_")); self.assertIs(r["external_action"],False); self.assertEqual(r["acquisition"]["route_id"],self.route["route_id"])
 def test_deterministic(self): self.assertEqual(self.record(),self.record())
 def test_persistence_and_idempotency(self):
  with tempfile.TemporaryDirectory() as d:
   repo=LocalLeadCaptureRepository(Path(d)); self.assertEqual(repo.store(self.record()),repo.store(self.record()))
 def test_conflict(self):
  with tempfile.TemporaryDirectory() as d:
   repo=LocalLeadCaptureRepository(Path(d)); repo.store(self.record()); changed=deepcopy(self.record()); changed["source"]="other"
   with self.assertRaises(LeadCaptureConflictError): repo.store(changed)
 def test_rejects_invalid_consent(self):
  bad=deepcopy(self.intake); bad["consent"]["granted"]=False
  with self.assertRaises(LeadCaptureValidationError): build_structured_lead_record(self.route,bad)
 def test_rejects_pii_unknown_and_bad_source(self):
  for bad in ({**self.intake,"email":"person@example.test"},{**self.intake,"source":"social"}):
   with self.assertRaises(LeadCaptureValidationError): build_structured_lead_record(self.route,bad)
 def test_rejects_non_test_lineage_and_execution(self):
  for route in ({**self.route,"external_action":True},{**self.route,"destination":{**self.route["destination"],"url":"https://example.com/book"}}):
   with self.assertRaises(LeadCaptureValidationError): build_structured_lead_record(route,self.intake)
if __name__=="__main__": unittest.main()
