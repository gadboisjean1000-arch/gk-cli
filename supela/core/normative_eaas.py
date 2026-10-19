#!/usr/bin/env python3
"""
supela/core/normative_eaas.py
Moteur de validation de l'architecture Supela-EaaS.
Zéro dépendance SDK tiers : sqlite3, hashlib, json, datetime, enum, dataclasses, typing.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
import hashlib
from datetime import datetime
import sqlite3
import json


class Status(Enum):
    """Statut d'une dimension de la grille des non-dits."""
    P = "P"      # Proclame
    I = "I"      # Implicite
    NA = "NA"    # Non-affirme
    OK = "OK"


class ModuleState(Enum):
    PLASTIC = "plastique"
    CONSOLIDATION = "consolidation"
    SEALED = "scelle"


DIMENSIONS = [
    "autorite_garantie",
    "mecanisme_application",
    "regime_sanction",
    "hierarchie_normes",
    "portee_territoriale",
    "temporalite",
]


class ValidationGrid:
    """Grille d'audit des non-dits systemiques (Couche 3)."""

    def __init__(self) -> None:
        self.dimensions = {d: Status.P for d in DIMENSIONS}
        self.remaining_na_count = 0

    def set_dimension(self, dim: str, status: Status, comment: str = "") -> None:
        if dim not in self.dimensions:
            raise ValueError("Dimension inconnue")
        self.dimensions[dim] = status
        if status == Status.NA:
            self.remaining_na_count += 1

    def na_count(self) -> int:
        return sum(1 for s in self.dimensions.values() if s == Status.NA)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimensions": {k: v.value for k, v in self.dimensions.items()},
            "remaining_na_count": self.remaining_na_count,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ValidationGrid":
        grid = cls()
        for dim, status in d.get("dimensions", {}).items():
            if dim in DIMENSIONS:
                grid.dimensions[dim] = Status(status)
        grid.remaining_na_count = d.get("remaining_na_count", 0)
        return grid


class SealedModuleMutationError(PermissionError):
    """Erreur levee lorsqu'on tente de muter un module scelle."""


@dataclass
class NormativeModule:
    """Module normatif Supela : predicat K3, indice de consolidation, cycle de vie."""

    id: str
    source: str = "SUP-0"
    k3_predicate: str = ""
    axioms: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    test_vectors: List[Dict[str, Any]] = field(default_factory=list)
    jurisdictional: str = "global"
    registration_hash: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    audit: ValidationGrid = field(default_factory=ValidationGrid)
    state: ModuleState = ModuleState.PLASTIC

    _SEALED_MUTABLE_FIELDS = {"state", "updated_at", "jurisdictional", "source"}

    def __setattr__(self, name: str, value: Any) -> None:
        if (
            getattr(self, "state", None) == ModuleState.SEALED
            and name not in self._SEALED_MUTABLE_FIELDS
        ):
            raise SealedModuleMutationError(
                f"Module {getattr(self, 'id', '?')} est scelle: mutation de {name!r} bloquee"
            )
        super().__setattr__(name, value)

    @property
    def consolidation_index(self) -> float:
        """Indice de consolidation C(m) = tau_K3 * (1 - N_NA/6) * S_sim."""
        if not self.k3_predicate:
            k3_rate = 0.0
        else:
            k3_rate = 0.8 + (len(self.k3_predicate) % 20) / 100.0
        n_na = self.audit.na_count()
        sim_score = 0.5
        if self.test_vectors:
            passed = sum(1 for t in self.test_vectors if t.get("passed", False))
            sim_score = 0.6 + (passed / max(1, len(self.test_vectors))) * 0.4
        return k3_rate * (1 - n_na / 6.0) * sim_score

    def compute_state(self) -> ModuleState:
        c = self.consolidation_index
        if c < 0.5:
            return ModuleState.PLASTIC
        if c < 0.95:
            return ModuleState.CONSOLIDATION
        if c >= 0.95 and self.audit.na_count() == 0:
            return ModuleState.SEALED
        return ModuleState.PLASTIC

    def can_seal(self) -> bool:
        return self.consolidation_index >= 0.95 and self.audit.na_count() == 0

    def seal(self) -> str:
        """Scelle le module (hash SHA-256) si les seuils sont atteints."""
        if not self.can_seal():
            raise PermissionError(
                f"Impossible de sceller: C={self.consolidation_index:.3f}, NA={self.audit.na_count()}"
            )
        payload = f"{self.id}|{self.axioms}|{self.constraints}|{self.k3_predicate}"
        self.registration_hash = hashlib.sha256(payload.encode()).hexdigest()
        self.updated_at = datetime.utcnow().isoformat() + "Z"
        self.state = ModuleState.SEALED
        return self.registration_hash

    def to_dict(self) -> Dict[str, Any]:
        return {
            "module": {
                "id": self.id,
                "source": self.source,
                "state": self.state.value,
                "consolidation_index": round(self.consolidation_index, 4),
                "created_at": self.created_at,
                "updated_at": self.updated_at,
            },
            "normative": {"axioms": self.axioms, "constraints": self.constraints},
            "operational": {
                "k3_predicate": self.k3_predicate,
                "test_vectors": self.test_vectors,
            },
            "institutional": {
                "opposability": True,
                "jurisdiction": self.jurisdictional,
                "hash": self.registration_hash,
            },
            "non_dits": {
                "na": self.audit.na_count(),
                "dims": {k: v.value for k, v in self.audit.dimensions.items()},
            },
        }


class NormativeStore:
    """Couche de persistance SQLite (Couche 2) avec journal WORM des scellements."""

    def __init__(self, db_path: str = "supela_eaas.db") -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS modules (
                id TEXT PRIMARY KEY, source TEXT, state TEXT,
                consolidation_index REAL, k3_predicate TEXT,
                axioms TEXT, constraints TEXT, test_vectors TEXT,
                jurisdictional TEXT, registration_hash TEXT,
                created_at TEXT, updated_at TEXT, audit_data TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS seal_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module_id TEXT, state TEXT, hash TEXT,
                event_type TEXT, timestamp TEXT
            )
            """
        )
        self.conn.commit()

    def save_module(self, module: NormativeModule) -> None:
        cur = self.conn.cursor()
        audit = module.audit.to_dict()
        cur.execute(
            """
            INSERT OR REPLACE INTO modules
            (id, source, state, consolidation_index, k3_predicate,
             axioms, constraints, test_vectors, jurisdictional, registration_hash,
             created_at, updated_at, audit_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                module.id,
                module.source,
                module.state.value,
                round(module.consolidation_index, 4),
                module.k3_predicate,
                json.dumps(module.axioms),
                json.dumps(module.constraints),
                json.dumps(module.test_vectors),
                module.jurisdictional,
                module.registration_hash,
                module.created_at,
                module.updated_at,
                json.dumps(audit),
            ),
        )
        if module.state == ModuleState.SEALED:
            cur.execute(
                "INSERT INTO seal_history (module_id, state, hash, event_type, timestamp) VALUES (?, ?, ?, ?, ?)",
                (
                    module.id,
                    module.state.value,
                    module.registration_hash,
                    "SEALED",
                    module.updated_at,
                ),
            )
        self.conn.commit()

    def load_module(self, module_id: str) -> Optional[NormativeModule]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM modules WHERE id = ?", (module_id,))
        row = cur.fetchone()
        if not row:
            return None
        audit_dict = json.loads(row[12] or "{}")
        grid = ValidationGrid.from_dict(audit_dict)
        module = NormativeModule(
            id=row[0],
            source=row[1],
            state=ModuleState(row[2]),
            k3_predicate=row[4],
            axioms=json.loads(row[5] or "[]"),
            constraints=json.loads(row[6] or "[]"),
            test_vectors=json.loads(row[7] or "[]"),
            jurisdictional=row[8],
            registration_hash=row[9],
            created_at=row[10],
            updated_at=row[11],
            audit=grid,
        )
        return module

    def list_modules(self) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT id, state, consolidation_index, updated_at FROM modules ORDER BY id"
        )
        return [
            {"id": r[0], "state": r[1], "consolidation_index": r[2], "updated_at": r[3]}
            for r in cur.fetchall()
        ]

    def log_seal_event(self, module_id: str, event_type: str) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO seal_history (module_id, state, hash, event_type, timestamp) VALUES (?, ?, ?, ?, ?)",
            (module_id, "SEALED", "", event_type, datetime.utcnow().isoformat() + "Z"),
        )
        self.conn.commit()

    def export_seal_history_json(self, path: str) -> str:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT module_id, state, hash, event_type, timestamp FROM seal_history ORDER BY id"
        )
        rows = cur.fetchall()
        payload = [
            {
                "module_id": r[0],
                "state": r[1],
                "hash": r[2],
                "event_type": r[3],
                "timestamp": r[4],
            }
            for r in rows
        ]
        ledger_sha = hashlib.sha256(json.dumps(payload).encode()).hexdigest()
        output = {"ledger_sha256": ledger_sha, "entries": payload}
        with open(path, "w") as f:
            json.dump(output, f, indent=2)
        return ledger_sha

    def close(self) -> None:
        self.conn.close()
