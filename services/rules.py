from __future__ import annotations

from typing import Dict, List, Tuple

CRITICAL_FIELDS = {
    "bdc_devis_annee_mois",
    "bdc_ref_affaire",
    "bdc_client_nom",
    "bdc_commercial_nom",
    "bdc_montant_fourniture_ht",
}


STRUCTURE_PRIORITY = [
    ("limon_centrale", "bdc_chk_limon_centrale"),
    ("limon_decoupe", "bdc_chk_limon_decoupe"),
    ("cremaillere", "bdc_chk_cremaillere"),
    ("limon", "bdc_chk_limon"),
]


CONTREMARCHE_MAPPING = {
    "avec": ("bdc_chk_avec-contre-marches", "bdc_chk_avec-sans-marches"),
    "sans": ("bdc_chk_avec-sans-marches", "bdc_chk_avec-contre-marches"),
}


STRUCTURE_KEYWORDS = {
    "limon_centrale": ["centrale"],
    "limon_decoupe": ["decoup", "découp"],
    "cremaillere": ["crémaillère", "cremaillere"],
    "limon": ["limon"],
}


def apply_rules(
    data: Dict[str, object], config: Dict[str, object], pose_override: bool | None = None
) -> Tuple[Dict[str, object], List[str]]:
    warnings: List[str] = []
    pose_sold = pose_override if pose_override is not None else bool(data.get("pose_sold", False))

    mapped: Dict[str, object] = {
        "bdc_devis_annee_mois": data.get("devis_full", ""),
        "bdc_ref_affaire": data.get("ref_affaire", ""),
        "bdc_client_nom": data.get("client_nom", ""),
        "bdc_commercial_nom": data.get("commercial_nom", ""),
        "bdc_esc_gamme": data.get("esc_gamme", ""),
        "bdc_esc_tete_de_poteau": data.get("esc_tete_de_poteau", ""),
        "bdc_esc_section_remplissage_garde_corps_rampant": data.get(
            "remplissage_rampant", ""
        ),
        "bdc_esc_section_remplissage_garde_corps_etage": data.get("remplissage_etage", ""),
        "bdc_esc_remplissage_garde_corps_soubassement": data.get(
            "remplissage_soubassement", ""
        ),
        "bdc_esc_essence": data.get("esc_essence", ""),
        "bdc_esc_finition_marches": data.get("esc_finition_marches", ""),
        "bdc_esc_finition_contremarche": data.get("esc_finition_contremarche", ""),
        "bdc_esc_finition_structure": data.get("esc_finition_structure", ""),
        "bdc_esc_finition_mains_courante": data.get("esc_finition_mains_courante", ""),
        "bdc_montant_fourniture_ht": data.get("fourniture_ht", ""),
        "bdc_montant_pose_ht": data.get("prestations_ht", ""),
        "parse_warning": data.get("parse_warning", ""),
    }

    mapped["pose_sold"] = pose_sold

    contremarche_value = str(data.get("esc_contremarche", "")).lower()
    for keyword, (true_field, false_field) in CONTREMARCHE_MAPPING.items():
        if keyword in contremarche_value:
            mapped[true_field] = True
            mapped[false_field] = False
            break

    structure_value = str(data.get("esc_structure", "")).lower()
    for key, field in STRUCTURE_PRIORITY:
        if any(term in structure_value for term in STRUCTURE_KEYWORDS[key]):
            mapped[field] = True
            break

    if structure_value and not any(k in mapped for _, k in STRUCTURE_PRIORITY):
        warnings.append("Structure détectée mais aucune case cochée")

    if data.get("esc_structure"):
        mapped.setdefault("bdc_chk_limon", False)
        mapped.setdefault("bdc_chk_cremaillere", False)
        mapped.setdefault("bdc_chk_limon_decoupe", False)
        mapped.setdefault("bdc_chk_limon_centrale", False)

    remplissage_values = {
        "remplissage_rampant": data.get("remplissage_rampant", ""),
        "remplissage_etage": data.get("remplissage_etage", ""),
        "remplissage_soubassement": data.get("remplissage_soubassement", ""),
    }
    non_empty = [(name, value) for name, value in remplissage_values.items() if value]

    if len(non_empty) == 1 and not remplissage_values.get("remplissage_rampant"):
        mapped["bdc_esc_section_remplissage_garde_corps_rampant"] = non_empty[0][1]

    if not non_empty:
        generic = data.get("remplissage", "")
        if generic:
            mapped["bdc_esc_section_remplissage_garde_corps_rampant"] = generic

    mapped["bdc_chk_livraison_poseur"] = bool(pose_sold)
    mapped["bdc_chk_livraison_client"] = not bool(pose_sold)
    mapped["bdc_chk_autoliquidation"] = bool(pose_sold)

    depot_address = str(config.get("depot_adresse", ""))
    mapped["bdc_livraison_bloc"] = depot_address if pose_sold and depot_address else ""

    return mapped, warnings
