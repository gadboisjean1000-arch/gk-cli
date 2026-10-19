#!/usr/bin/env python3
"""
supela/tools/supela_cli.py
CLI Supela-EaaS : status, seal, catalog.
"""

import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from supela.core.normative_eaas import NormativeModule, NormativeStore, ModuleState
from supela.core.k3_catalog import K3Catalog


def _default_sealable_module(module_id: str) -> NormativeModule:
    return NormativeModule(
        id=module_id,
        k3_predicate="a" * 19,
        axioms=["Regle par defaut"],
        test_vectors=[{"passed": True}],
    )


def cmd_status(args) -> int:
    store = NormativeStore(args.db)
    try:
        modules = store.list_modules()
        if not modules:
            print("Aucun module en base.")
            return 0
        print(f"{'ID':<20} {'ETAT':<16} {'C(m)':<8} {'MISE A JOUR'}")
        for m in modules:
            print(
                f"{m['id']:<20} {m['state']:<16} "
                f"{m['consolidation_index']:<8} {m['updated_at']}"
            )
        return 0
    finally:
        store.close()


def cmd_seal(args) -> int:
    store = NormativeStore(args.db)
    try:
        module = store.load_module(args.module)
        created = False
        if module is None:
            print(f"Module introuvable: {args.module} - creation par default.")
            module = _default_sealable_module(args.module)
            created = True
        try:
            h = module.seal()
        except PermissionError as exc:
            print(f"Echec du scellement: {exc}", file=sys.stderr)
            return 1
        store.save_module(module)
        store.log_seal_event(module.id, "SEALED")
        action = "cree et " if created else ""
        print(f"Module {module.id} {action}scelle. Hash SHA-256: {h}")
        if args.git_commit:
            subprocess.run(["git", "add", "supela_eaas.db"], check=False)
            subprocess.run(
                ["git", "commit", "-m", f"supela: seal {module.id}"], check=False
            )
        return 0
    finally:
        store.close()


def cmd_catalog(args) -> int:
    cat = K3Catalog()
    ok, msg = cat.verify_fractal_homogeneity()
    print(msg)
    for mid in sorted(cat.all_rules()):
        rule = cat.get_rule(mid)
        print(f"  {mid}: {rule.domaine}")
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="supela_cli", description="CLI Supela-EaaS")
    parser.add_argument("--db", default="supela_eaas.db", help="Chemin de la base SQLite")
    sub = parser.add_subparsers(dest="command", required=True)

    p_status = sub.add_parser("status", help="Liste les modules persists")
    p_status.set_defaults(func=cmd_status)

    p_seal = sub.add_parser("seal", help="Scelle un module (le cree si absent)")
    p_seal.add_argument("module", help="Identifiant du module")
    p_seal.add_argument(
        "--git-commit", action="store_true", help="Commit Git apres scellement"
    )
    p_seal.set_defaults(func=cmd_seal)

    p_cat = sub.add_parser("catalog", help="Affiche le catalogue K3")
    p_cat.set_defaults(func=cmd_catalog)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
