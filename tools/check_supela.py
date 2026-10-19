#!/usr/bin/env python3
"""
tools/check_supela.py
Verification sanitaire du moteur Supela-EaaS (compile + imports + smoke tests).
"""

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

FILES = ["supela/core/normative_eaas.py", "supela/core/k3_catalog.py"]


def main() -> int:
    rc = 0
    import py_compile

    for rel in FILES:
        path = os.path.join(ROOT, rel)
        try:
            py_compile.compile(path, doraise=True)
            print(f"[OK] {rel}")
        except py_compile.PyCompileError as exc:
            print(f"[ERR] {rel}: {exc}")
            rc = 1

    from supela.core.normative_eaas import (
        NormativeModule,
        NormativeStore,
        ModuleState,
    )
    from supela.core.k3_catalog import K3Catalog

    m = NormativeModule(id="CHECK-001", k3_predicate="x > 0")
    assert m.compute_state() == ModuleState.PLASTIC
    print("[OK] calcul d'etat par defaut: PLASTIC")

    cat = K3Catalog()
    ok, msg = cat.verify_fractal_homogeneity()
    print(f"[OK] catalogue K3: {msg}")
    if not ok:
        rc = 1

    db = os.path.join(tempfile.gettempdir(), "supela_check.db")
    if os.path.exists(db):
        os.remove(db)
    store = NormativeStore(db)
    m2 = NormativeModule(id="CHECK-002")
    store.save_module(m2)
    loaded = store.load_module("CHECK-002")
    assert loaded is not None and loaded.id == "CHECK-002"
    store.close()
    os.remove(db)
    print("[OK] persistance SQLite (sauvegarde/chargement)")
    print("check_supela: OK" if rc == 0 else "check_supela: ECHEC")
    return rc


if __name__ == "__main__":
    sys.exit(main())
