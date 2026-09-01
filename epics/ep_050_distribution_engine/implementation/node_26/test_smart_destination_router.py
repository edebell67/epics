"""Offline Node 19→20→21→26 regression tests; socket construction is prohibited."""
from __future__ import annotations
import json, socket, sys, tempfile, unittest
from copy import deepcopy
from pathlib import Path
HERE=Path(__file__).resolve(); IMPL=HERE.parents[1]
for node in ("node_19","node_20","node_21","node_26"): sys.path.insert(0,str(IMPL/node))
from quality_compliance import evaluate_asset_compliance
from publishing_scheduler import build_mock_publication_plan
from search_distribution import build_search_distribution_package
from smart_destination_router import (DestinationRoutingConflictError,DestinationRoutingValidationError,LocalDestinationRouteRepository,build_route_recommendation)
class RouterTest(unittest.TestCase):
 def setUp(self):
  self.socket=socket.socket; socket.socket=lambda *a,**k:(_ for _ in ()).throw(AssertionError("network prohibited"))
  source=json.loads((IMPL/"node_21/fixtures/approved_search_asset_fixture.json").read_text())
  result, package=evaluate_asset_compliance(source); self.assertTrue(result.approved)
  self.approved=package.to_dict(); self.plan=build_mock_publication_plan(self.approved); self.search=build_search_distribution_package(self.plan,self.approved)
  self.context={"topic":"Safe Boiler Pressure Guide","intent":"diagnostic_quote","geography":"Blackheath","service":"boiler_repair","channel":"search_landing","asset_id":self.plan["asset_id"],"target_id":self.plan["target_id"],"opportunity_id":self.plan["opportunity_id"],"external_action":False,"deferred_channel_context":{"22":"deferred","23":"deferred","24":"deferred","25":"deferred"}}
 def tearDown(self): socket.socket=self.socket
 def route(self): return build_route_recommendation(self.plan,self.approved,self.search,self.context)
 def test_real_node19_to_26_integration(self):
  route=self.route(); self.assertTrue(route["route_id"].startswith("sdr_")); self.assertIs(route["external_action"],False); self.assertTrue(route["destination"]["url"].endswith(".test/book"))
 def test_deterministic(self): self.assertEqual(self.route(),self.route())
 def test_persistence_and_idempotency(self):
  with tempfile.TemporaryDirectory() as d:
   repo=LocalDestinationRouteRepository(Path(d)); self.assertEqual(repo.store(self.route()),repo.store(self.route()))
 def test_conflict(self):
  with tempfile.TemporaryDirectory() as d:
   repo=LocalDestinationRouteRepository(Path(d)); route=self.route(); repo.store(route); altered=deepcopy(route); altered["rule_explanation"]="changed"
   with self.assertRaises(DestinationRoutingConflictError): repo.store(altered)
 def test_missing_node21_lineage(self):
  bad=deepcopy(self.search); bad["manifest"]["asset_id"]="wrong"
  with self.assertRaises(DestinationRoutingValidationError): build_route_recommendation(self.plan,self.approved,bad,self.context)
 def test_real_town_and_service_vary_freely_without_rejection(self):
  """geography/service are real per-campaign data, not a rule-matching literal -- a different
  real town or vertical must route successfully, not be rejected. Until 2026-08-19 _RULES pinned
  geography="blackheath"/service="boiler_repair" as exact-match requirements, so this exact
  scenario ("elsewhere") raised DestinationRoutingValidationError for every real campaign except
  the one hardcoded town/service combination."""
  varied=deepcopy(self.context); varied["geography"]="elsewhere"; varied["service"]="a_different_vertical"
  route=build_route_recommendation(self.plan,self.approved,self.search,varied)
  self.assertEqual(route["routing_context"]["geography"],"elsewhere")
  self.assertEqual(route["routing_context"]["service"],"a_different_vertical")
 def test_unknown_intent_still_rejected(self):
  """intent IS a policy field: an unapproved intent must still be rejected."""
  bad=deepcopy(self.context); bad["intent"]="unapproved_intent"
  with self.assertRaises(DestinationRoutingValidationError): build_route_recommendation(self.plan,self.approved,self.search,bad)
 def test_non_test_destination(self):
  bad=deepcopy(self.approved); bad["cta_definition"]["destination_url"]="https://example.com/book"
  with self.assertRaises(DestinationRoutingValidationError): build_route_recommendation(self.plan,bad,self.search,self.context)
 def test_external_request_pii_and_deferred_completion_rejected(self):
  for key,value in (("external_action",True),("topic","email x@y.test"),("deferred_channel_context",{"22":"complete"})):
   bad=deepcopy(self.context); bad[key]=value
   with self.assertRaises(DestinationRoutingValidationError): build_route_recommendation(self.plan,self.approved,self.search,bad)
 def test_broken_context_lineage(self):
  bad=deepcopy(self.context); bad["asset_id"]="wrong"
  with self.assertRaises(DestinationRoutingValidationError): build_route_recommendation(self.plan,self.approved,self.search,bad)
if __name__=="__main__": unittest.main(verbosity=2)
