"""
EP050 Node 16: Canonical Knowledge Store - Test & Verification Suite

Validates:
1. Positive canonical fact registration and query by topic/product
2. Stable, reproducible deterministic fact IDs (fact_ + hash)
3. Mandatory safety guidance for safety-critical facts
4. Prohibited PII screening (emails and phone numbers)
5. Idempotent duplicate registration & conflicting registration rejection
6. Persistence save and reload integrity
7. 100% offline execution with socket block
8. Real upstream pipeline integration test: Node 01 TargetRegistry -> Node 02 ProductIntelligenceRegistry -> Node 16 CanonicalKnowledgeStore

VERSION HISTORY
- v1.0.1 · 2026-09-01 · Normalizes release whitespace so the canonical package passes staged integrity checks; test behavior is unchanged.
- v1.0.0 · 2026-08-17 · Initial complete test suite for Node 16 Canonical Knowledge Store.
"""

import os
import sys
import json
import socket
import tempfile
from pathlib import Path
import pytest

from canonical_knowledge_store import (
    CanonicalKnowledgeStore,
    CanonicalFactRecord,
    ValidationError,
    LineageError,
    ConflictError
)

# Upstream module imports for integration test
BASE_IMPL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_IMPL / "node_01"))
sys.path.insert(0, str(BASE_IMPL / "node_02"))

from registration import TargetRegistry
from product_intelligence import ProductIntelligenceRegistry


@pytest.fixture(autouse=True)
def assert_no_network(monkeypatch):
    """Enforces 100% offline execution by blocking socket creation."""
    def _blocked_socket(*args, **kwargs):
        raise RuntimeError("Network socket creation is prohibited during EP050 tests.")
    monkeypatch.setattr(socket, "socket", _blocked_socket)


def test_positive_fact_registration():
    """Verifies that a valid canonical fact registers and queries cleanly."""
    store = CanonicalKnowledgeStore()
    fact = store.register_fact(
        target_id="target_boiler_blackheath_01",
        topic="boiler_pressure_normal_range",
        claim="Standard domestic combi boiler pressure should remain between 1.0 and 1.5 bar when cold.",
        verification_source="Worcester Bosch & Vaillant Operating Manuals (2025)",
        is_safety_critical=False
    )

    assert isinstance(fact, CanonicalFactRecord)
    assert fact.fact_id.startswith("fact_")
    assert fact.topic == "boiler_pressure_normal_range"
    assert fact.is_safety_critical is False

    retrieved = store.get_fact(fact.fact_id)
    assert retrieved == fact

    by_topic = store.list_facts(topic="boiler_pressure_normal_range")
    assert len(by_topic) == 1
    assert by_topic[0].fact_id == fact.fact_id


def test_safety_critical_guidance_enforcement():
    """Verifies that safety-critical facts require explicit safety guidance."""
    store = CanonicalKnowledgeStore()

    # Missing safety guidance on safety critical fact -> raises ValidationError
    with pytest.raises(ValidationError):
        store.register_fact(
            target_id="target_01",
            topic="gas_leak_protocol",
            claim="Any smell of gas requires immediate isolation of main emergency control valve.",
            verification_source="Gas Safe (Installation and Use) Regulations 1998",
            is_safety_critical=True,
            safety_guidance=None
        )

    # Valid with safety guidance
    fact = store.register_fact(
        target_id="target_01",
        topic="gas_leak_protocol",
        claim="Any smell of gas requires immediate isolation of main emergency control valve.",
        verification_source="Gas Safe (Installation and Use) Regulations 1998",
        is_safety_critical=True,
        safety_guidance="Instruct homeowner not to operate electrical switches, open windows, extinguish naked flames, and evacuate."
    )
    assert fact.is_safety_critical is True
    assert fact.safety_guidance is not None

    safety_facts = store.get_safety_critical_facts(target_id="target_01")
    assert len(safety_facts) == 1
    assert safety_facts[0].fact_id == fact.fact_id


def test_prohibited_pii_screen():
    """Verifies that facts containing email addresses or phone numbers are rejected."""
    store = CanonicalKnowledgeStore()

    with pytest.raises(ValidationError):
        store.register_fact(
            target_id="target_01",
            topic="contact_engineer",
            claim="Contact direct engineer at engineer@boilercompany.co.uk for emergency dispatch.",
            verification_source="Direct Contact"
        )

    with pytest.raises(ValidationError):
        store.register_fact(
            target_id="target_01",
            topic="contact_engineer",
            claim="Call 07123 456 789 immediately.",
            verification_source="Direct Phone"
        )


def test_idempotency_and_conflict_rejection():
    """Verifies that identical facts return the existing record, but conflicting parameters error."""
    store = CanonicalKnowledgeStore()
    f1 = store.register_fact(
        target_id="target_01",
        topic="boiler_repressurise",
        claim="Use the internal filling loop to repressurise the boiler to 1.2 bar.",
        verification_source="Gas Safe Guide",
        is_safety_critical=False
    )
    # Identical registration -> returns f1
    f2 = store.register_fact(
        target_id="target_01",
        topic="boiler_repressurise",
        claim="Use the internal filling loop to repressurise the boiler to 1.2 bar.",
        verification_source="Gas Safe Guide",
        is_safety_critical=False
    )
    assert f1.fact_id == f2.fact_id

    # Conflicting attribute on same ID -> raises ConflictError
    with pytest.raises(ConflictError):
        store.register_fact(
            target_id="target_01",
            topic="boiler_repressurise",
            claim="Use the internal filling loop to repressurise the boiler to 1.2 bar.",
            verification_source="Gas Safe Guide",
            is_safety_critical=True,  # Conflict!
            safety_guidance="Wear safety gloves."
        )


def test_persistence_roundtrip():
    """Verifies saving to and loading from a JSON file."""
    with tempfile.TemporaryDirectory() as td:
        storage_file = Path(td) / "canonical_facts.json"
        store1 = CanonicalKnowledgeStore(storage_path=storage_file)
        f = store1.register_fact(
            target_id="target_01",
            topic="thermostat_battery",
            claim="Low thermostat batteries can simulate complete boiler PCB failure.",
            verification_source="Hive Heating Diagnostic Manual"
        )

        # Create new store from same file
        store2 = CanonicalKnowledgeStore(storage_path=storage_file)
        loaded = store2.get_fact(f.fact_id)
        assert loaded is not None
        assert loaded.fact_id == f.fact_id
        assert loaded.topic == "thermostat_battery"


def test_upstream_node01_node02_node16_integration():
    """
    Real unmocked upstream pipeline integration test:
    Executes TargetRegistry (Node 01) -> ProductIntelligenceRegistry (Node 02) -> CanonicalKnowledgeStore (Node 16).
    """
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        t_reg = TargetRegistry(tmp / "targets.json")
        prod_reg = ProductIntelligenceRegistry(tmp / "prods.json", target_registry=t_reg)
        store = CanonicalKnowledgeStore(storage_path=tmp / "facts.json", target_registry=t_reg, product_registry=prod_reg)

        target = t_reg.register(
            target_type="service_market",
            service="boiler_repair",
            market="domestic_plumbing",
            geography={"locality": "Blackheath", "region": "London", "country": "UK"}
        )

        prod = prod_reg.register(
            target_id=target.target_id,
            problem="Homeowners lose boiler pressure and hot water with no clear diagnosis path.",
            solution="A vetted local boiler-repair callout that diagnoses and restores pressure same-day.",
            features=["Same-day callout", "Fixed diagnostic rate"],
            benefits=["Hot water restored quickly"],
            differentiators=["Local Blackheath coverage"],
            commercial_model="Fixed diagnostic fee.",
            customer_outcome="Working boiler within 24 hours."
        )

        # Register canonical knowledge linked to validated target and product
        fact = store.register_fact(
            target_id=target.target_id,
            topic="gas_safe_compliance",
            claim="All emergency boiler repairs involving combustion chambers or gas supply valves must be carried out by a Gas Safe Registered engineer.",
            verification_source="Gas Safety (Installation and Use) Regulations 1998, Regulation 3",
            is_safety_critical=True,
            safety_guidance="Homeowners must not attempt to dismantle boiler casing or touch internal gas assemblies."
        )

        assert fact.target_id == target.target_id
        assert fact.is_safety_critical is True
        assert store.get_fact(fact.fact_id) == fact
        assert len(store.get_safety_critical_facts(target_id=target.target_id)) == 1
