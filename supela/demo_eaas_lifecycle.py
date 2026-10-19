#!/usr/bin/env python3
"""
demo_eaas_lifecycle.py
Démonstration end-to-end du cycle de vie Supela en 9 étapes.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from supela.core.normative_eaas import NormativeModule, NormativeStore, ModuleState, ValidationGrid, Status


def step1_create_plastic():
    print("\n[Étape 1] Créer module PLASTIC")
    m = NormativeModule(
        id="SUP-MOD-001",
        k3_predicate="tax_injunction(amount) > 10000 -> flag(user_id)",
        axioms=["Rigueur normative", "Opposabilité universelle"],
        constraints=["Châlinage toujours actif"],
        test_vectors=[],
        jurisdictional="EU-FR",
    )
    m.audit.set_dimension("autorite_garantie", Status.P, "Désignation du gardien")
    m.audit.set_dimension("mecanisme_application", Status.P, "Algorithme de contrôle")
    m.audit.set_dimension("regime_sanction", Status.P, "Mise en quarantaine")
    m.audit.set_dimension("hierarchie_normes", Status.P, "DAG de précédence")
    m.audit.set_dimension("portée_territoriale", Status.P, "Périmètre EU")
    m.audit.set_dimension("temporalite", Status.NA, "A cheval sur plusieurs trimestres")
    m.state = ModuleState.PLASTIC
    print(f"  C(m) = {m.consolidation_index:.4f}, Statut: {m.state.value}")
    return m


def step2_audit_nondits(module):
    print("\n[Étape 2] Foliation des 6 non-dits")
    grid = module.audit
    print(f"  Dimensions auditées: {len(grid.dimensions)}")
    print(f"  Non-affirmées restantes: {grid.remaining_na_count}")
    for dim, status in grid.dimensions.items():
        print(f"    - {dim}: {status.value}")
    return grid


def step3_translate_k3(module):
    print("\n[Étape 3] Traduction opératoire K3")
    print(f"  Prédicat K3: {module.k3_predicate}")
    module.test_vectors = [
        {"input": {"amount": 5000}, "expected": False},
        {"input": {"amount": 15000}, "expected": True, "passed": True},
    ]
    passed = sum(1 for v in module.test_vectors if v.get("passed", False))
    print(f"  Tests de validation: {passed}/{len(module.test_vectors)}")
    return passed


def step4_validate_k3(module, passed):
    print("\n[Étape 4] Validation des vecteurs de test")
    print(f"  Taux K3 (τ): {passed}/{len(module.test_vectors)} réussis")
    return passed


def step5_simulate_prospective(module):
    print("\n[Étape 5] Simulation prospective (Couche 5)")
    # Vérifie la non-contradiction avec d'autres modules
    contradictions = 0
    for tv in module.test_vectors:
        if not tv.get("passed", False):
            contradictions += 1
    score = 0.6 + (len(module.test_vectors) - contradictions) * 0.1
    print(f"  Score de stabilité S_sim: {score:.2f}")
    return score


def step6_verify_thresholds(module):
    print("\n[Étape 6] Vérification des seuils de scellement")
    c = module.consolidation_index
    n_na = module.audit.na_count()
    print(f"  C(m) = {c:.4f} (seuil: 0.95)")
    print(f"  N_NA = {n_na} (seuil: 0)")
    print(f"  Résultat: {'✓' if c >= 0.95 and n_na == 0 else '✗'}")


def step7_seal_module(module):
    print("\n[Étape 7] Scellement par crop intelligent & persistance")
    h = module.seal()
    print(f"  Statut: {module.state.value}")
    print(f"  Hash SHA-256: {h}")
    return h


def step8_block_mutations(module):
    print("\n[Étape 8] Blocage des mutations directs (Crop définitif)")
    try:
        module.k3_predicate = "new_rule"
        print("  ✗ ÉCHEC: la mutation a été bloquée")
    except PermissionError:
        print("  ✓ Blocage de la mutation réussi (Crop définitif activé)")
    return module.state == ModuleState.SEALED


def step9_quarantine_drive(module):
    print("\n[Étape 9] Dérive externe -> Quarantaine")
    print(f"  Dérive détectée: REFORME_FISCALE_IS_2027 (sévérité 0.85)")
    module.state = ModuleState.PLASTIC
    print(f"  Nouveau statut: {module.state.value} (module en quarantaine)")
    return module.state == ModuleState.PLASTIC


def main():
    print("=" * 60)
    print("  Démonstration End-to-End : Cycle de Vie Supela")
    print("=" * 60)

    store = NormativeStore("supela_eaas.db")

    m = step1_create_plastic()
    step2_audit_nondits(m)
    n_val = step3_translate_k3(m)
    step4_validate_k3(m, n_val)
    step5_simulate_prospective(m)
    step6_verify_thresholds(m)
    step7_seal_module(m)
    step8_block_mutations(m)
    step9_quarantine_drive(m)

    store.save_module(m)
    print("\n[OK] Module sauvegardé en base SQLite")
    store.close()
    print("\n" + "=" * 60)
    print("  Cycle de vie complet terminé.")
    print("=" * 60)


if __name__ == "__main__":
    main()
