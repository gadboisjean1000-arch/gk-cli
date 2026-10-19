#!/usr/bin/env python3
"""Tests unitaires du moteur Supela-EaaS."""
import json
import os
import tempfile

import pytest

from supela.core.normative_eaas import (
    NormativeModule,
    NormativeStore,
    ModuleState,
    ValidationGrid,
    Status,
    SealedModuleMutationError,
    DIMENSIONS,
)
from supela.core.k3_catalog import K3Catalog


def test_dimensions_count():
    assert len(DIMENSIONS) == 6


def test_validation_grid_default():
    grid = ValidationGrid()
    assert len(grid.dimensions) == 6
    assert grid.na_count() == 0
    assert all(s == Status.P for s in grid.dimensions.values())


def test_set_dimension_na():
    grid = ValidationGrid()
    grid.set_dimension("temporalite", Status.NA, "non defini")
    assert grid.na_count() == 1


def test_set_dimension_unknown_raises():
    grid = ValidationGrid()
    with pytest.raises(ValueError):
        grid.set_dimension("inexistante", Status.P)


def test_default_state_is_plastic():
    m = NormativeModule(id="M-PLASTIC")
    assert m.state == ModuleState.PLASTIC
    assert m.compute_state() == ModuleState.PLASTIC


def test_consolidation_index_bounds():
    m = NormativeModule(id="M-BOUNDS", k3_predicate="predicat test")
    c = m.consolidation_index
    assert 0.0 <= c <= 1.0


def test_consolidation_index_na_penalty():
    m1 = NormativeModule(id="M1", k3_predicate="p")
    m2 = NormativeModule(id="M2", k3_predicate="p")
    m2.audit.set_dimension("temporalite", Status.NA)
    assert m2.consolidation_index < m1.consolidation_index


def test_can_seal_threshold_met():
    m = NormativeModule(
        id="M-SEAL",
        k3_predicate="a" * 19,
        test_vectors=[{"passed": True}, {"passed": True}],
    )
    assert m.audit.na_count() == 0
    assert m.can_seal() is True
    assert m.compute_state() == ModuleState.SEALED


def test_can_seal_fails_with_na():
    m = NormativeModule(
        id="M-NOSEAL",
        k3_predicate="a" * 19,
        test_vectors=[{"passed": True}],
    )
    m.audit.set_dimension("temporalite", Status.NA)
    assert m.can_seal() is False


def test_seal_sets_hash_and_state():
    m = NormativeModule(
        id="M-HASH",
        k3_predicate="a" * 19,
        test_vectors=[{"passed": True}],
    )
    h = m.seal()
    assert m.state == ModuleState.SEALED
    assert m.registration_hash == h
    assert len(h) == 64


def test_sealed_module_mutation_blocked():
    m = NormativeModule(
        id="M-LOCK",
        k3_predicate="a" * 19,
        test_vectors=[{"passed": True}],
    )
    m.seal()
    with pytest.raises(SealedModuleMutationError):
        m.k3_predicate = "nouvelle_regle"
    with pytest.raises(PermissionError):
        m.axioms = ["axiom"]


def test_state_change_still_possible_after_seal():
    m = NormativeModule(
        id="M-QUAR",
        k3_predicate="a" * 19,
        test_vectors=[{"passed": True}],
    )
    m.seal()
    m.state = ModuleState.PLASTIC
    assert m.state == ModuleState.PLASTIC


def test_module_to_dict():
    m = NormativeModule(id="M-DICT", k3_predicate="p")
    d = m.to_dict()
    assert d["module"]["id"] == "M-DICT"
    assert d["non_dits"]["na"] == 0


def test_save_and_load_module_roundtrip():
    db = os.path.join(tempfile.gettempdir(), "supela_test_roundtrip.db")
    if os.path.exists(db):
        os.remove(db)
    try:
        store = NormativeStore(db)
        m = NormativeModule(
            id="M-RT",
            k3_predicate="a" * 19,
            axioms=["A1"],
            constraints=["C1"],
            test_vectors=[{"passed": True}],
            jurisdictional="EU-FR",
        )
        m.seal()
        store.save_module(m)
        loaded = store.load_module("M-RT")
        store.close()
        assert loaded is not None
        assert loaded.id == "M-RT"
        assert loaded.state == ModuleState.SEALED
        assert loaded.registration_hash == m.registration_hash
        assert loaded.audit.na_count() == 0
        assert loaded.jurisdictional == "EU-FR"
    finally:
        if os.path.exists(db):
            os.remove(db)


def test_load_unknown_module_returns_none():
    db = os.path.join(tempfile.gettempdir(), "supela_test_none.db")
    if os.path.exists(db):
        os.remove(db)
    try:
        store = NormativeStore(db)
        assert store.load_module("DOES-NOT-EXIST") is None
        store.close()
    finally:
        if os.path.exists(db):
            os.remove(db)


def test_log_seal_event_and_export_json():
    db = os.path.join(tempfile.gettempdir(), "supela_test_export.db")
    if os.path.exists(db):
        os.remove(db)
    json_path = os.path.join(tempfile.gettempdir(), "supela_seal_history.json")
    try:
        store = NormativeStore(db)
        store.log_seal_event("M-EVT", "SEALED")
        sha = store.export_seal_history_json(json_path)
        assert len(sha) == 64
        with open(json_path) as f:
            data = json.load(f)
        assert "ledger_sha256" in data
        assert len(data["entries"]) == 1
        assert data["entries"][0]["module_id"] == "M-EVT"
        store.close()
    finally:
        for p in (db, json_path):
            if os.path.exists(p):
                os.remove(p)


def test_k3_catalog_verification():
    cat = K3Catalog()
    assert cat.get_rule("sup-mod-001") is not None
    ok, msg = cat.verify_fractal_homogeneity()
    assert ok is True
    h = cat.generate_joint_seal_hash(["sup-mod-001", "sup-mod-002"])
    assert len(h) == 64
