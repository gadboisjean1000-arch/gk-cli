#!/usr/bin/env python3
"""
tools/archive_supela_db.py
Archivage a chaud de la base SQLite Supela + export JSON de l'historique des scellements.
"""

import datetime
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from supela.core.normative_eaas import NormativeStore


def main() -> int:
    db = os.path.join(ROOT, "supela_eaas.db")
    if not os.path.exists(db):
        print(f"Aucune base a archiver: {db}")
        return 0

    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    archive_dir = os.path.join(ROOT, "archives")
    os.makedirs(archive_dir, exist_ok=True)

    archive_path = os.path.join(archive_dir, f"supela_eaas_{ts}.db")
    shutil.copy2(db, archive_path)
    print(f"[OK] Base archivee: {archive_path}")

    store = NormativeStore(db)
    json_path = os.path.join(archive_dir, f"seal_history_{ts}.json")
    store.export_seal_history_json(json_path)
    print(f"[OK] Historique exporte: {json_path}")
    store.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
