#!/usr/bin/env python3
"""
supela/core/k3_catalog.py
Catalogue des règles K3 opérationnelles.

Chaque règle K3 est un prédicat exécutable traduisant une règle normative
en algorithme vérifiable. Les 4 modules souverains Supela sont enregistrés
avec leurs miroirs institutionnels et leur homogénéité fractale.
"""

from dataclasses import dataclass, field
import hashlib
from typing import List, Dict, Any, Optional


@dataclass
class KR3Rule:
    """Règle K3 opérationnelle."""
    module_id: str
    domaine: str
    predicate: str
    action: str
    priority: int
    coinages: List[str] = field(default_factory=list)
    institutional_mirrors: List[str] = field(default_factory=list)

    def verify(self, context: Dict[str, Any]) -> tuple:
        """Évalue le prédicat K3 sur le contexte donné."""
        try:
            result = eval(self.predicate, {"__builtins__": {}}, context)
            return (True, result, f"OK: {self.predicate}")
        except Exception as e:
            return (False, False, f"ERR: {e}")


class K3Catalog:
    """Catalogue des règles K3 du noyau Supela."""
    INSTITUTIONAL_MIRRORS = {
        "sup-mod-001": ["dgtfip_cgi", "cgi_fiscal", "nomenclature_fiscale"],
        "sup-mod-002": ["iso20022", "bic_swift", "fatf_criblage"],
        "sup-mod-003": ["vr13_accreditation", "mfa_authentication"],
        "sup-mod-004": ["vr15_consensus_majoritaire", "isolation_souveraine"],
    }

    def __init__(self):
        self.rules: Dict[str, KR3Rule] = {}
        self._init_rules()

    def _init_rules(self):
        self.rules["sup-mod-001"] = KR3Rule(
            module_id="sup-mod-001",
            domaine="finance.corporate_tax",
            predicate="plafond_is_15 >= 0.15 and plafond_is_25 >= 0.25",
            action="flag_high_value_transactions(user_id, amount, currency)",
            priority=10,
            coinages=["tax_injunction", "tax_bridge", "fiscal_hold"],
            institutional_mirrors=self.INSTITUTIONAL_MIRRORS["sup-mod-001"],
        )
        self.rules["sup-mod-002"] = KR3Rule(
            module_id="sup-mod-002",
            domaine="finance.swift_compliance",
            predicate="iso20022_compliant and bic_verified and fatf_criblage >= 10000",
            action="route_for_screening(user_id, amount, counterparty)",
            priority=20,
            coinages=["swift_bridge", "banking_link"],
            institutional_mirrors=self.INSTITUTIONAL_MIRRORS["sup-mod-002"],
        )
        self.rules["sup-mod-003"] = KR3Rule(
            module_id="sup-mod-003",
            domaine="security.iam",
            predicate="vr13_accreditation and multi_factor_auth and zero_trust",
            action="grant_access(user_id, resource, level)",
            priority=30,
            coinages=["iam_bridge", "security_link"],
            institutional_mirrors=self.INSTITUTIONAL_MIRRORS["sup-mod-003"],
        )
        self.rules["sup-mod-004"] = KR3Rule(
            module_id="sup-mod-004",
            domaine="ai.consensus_routing",
            predicate="vr15_consensus_majoritaire and isolation_souveraine and majority > n/2",
            action="route_to_consensus_model(model_id, description)",
            priority=40,
            coinages=["ai_bridge", "consensus_link"],
            institutional_mirrors=self.INSTITUTIONAL_MIRRORS["sup-mod-004"],
        )

    def get_rule(self, module_id: str) -> Optional[KR3Rule]:
        return self.rules.get(module_id)

    def all_rules(self) -> Dict[str, KR3Rule]:
        return self.rules.copy()

    def verify_fractal_homogeneity(self) -> tuple:
        """Vérifie que tous les modules partagent la même structure fractale."""
        if not self.rules:
            return (True, "Catalogue vide")
        first = self.rules[list(self.rules.keys())[0]]
        for mid, rule in self.rules.items():
            if vars(rule).keys() != vars(first).keys():
                return (False, f"Homogénéité fractale rompue: {mid}")
        return (True, "Tous les modules partagent la structure fractale")

    def generate_joint_seal_hash(self, module_ids: List[str]) -> str:
        """Calcule l'empreinte de lot SHA-256 pour le scellement conjoint."""
        payload = "|".join(sorted(module_ids))
        return hashlib.sha256(payload.encode()).hexdigest()
