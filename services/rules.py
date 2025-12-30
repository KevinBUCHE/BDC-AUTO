from __future__ import annotations

from typing import Dict, List, Tuple

STRUCTURE_PRIORITY = [
    ("limon_centrale", "bdc_chk_limon_centrale"),
    ("limon_decoupe", "bdc_chk_limon_decoupe"),
    ("cremaillere", "bdc_chk_cremaillere"),
    ("limon", "bdc_chk_limon"),
]

STRUCTURE_KEYWORDS = {
    "limon_centrale": ["centrale"],
    "limon_decoupe": ["decoup", "découp"],
    "cremaillere": ["cremaillere", "crémaillère"],
    "limon": ["limon"],
}

CONTREMARCHE_MAPPING = {
    "avec": ("bdc_chk_avec-contre-marches", "bdc_chk_avec-sans-marches"),
    "sans": ("bdc_chk_avec-sans-marches", "bdc_chk_avec-contre-marches"),
}

CRITICAL_FIELDS = {
    "bdc_devis_annee_mois",
    "bdc_ref_affaire",
    "bdc_client_nom",
}


def apply_rules(data: Dict[str, object], config: Dict[str, object] | None = None) -> Tuple[Dict[str, object], List[str]]:
    warnings: List[str] = []

    mapped: Dict[str, object] = {
        "bdc_devis_annee_mois": data.get("devis_full", ""),
        "bdc_ref_affaire": data.get("ref_affaire", ""),
        "bdc_client_nom": data.get("client_nom", ""),
        "bdc_commercial_nom": data.get("commercial_nom", ""),
        "bdc_montant_fourniture_ht": data.get("fourniture_ht", ""),
        "bdc_montant_pose_ht": data.get("prestations_ht", ""),
        "bdc_esc_gamme": data.get("esc_gamme", ""),
        "bdc_esc_essence": data.get("esc_essence", ""),
        "bdc_esc_finition_marches": data.get("esc_finition_marches", ""),
        "bdc_esc_finition_structure": data.get("esc_finition_structure", ""),
        "bdc_esc_finition_mains_courante": data.get("esc_finition_mains_courante", ""),
        "bdc_esc_finition_contremarche": data.get("esc_finition_contremarche", ""),
        "bdc_esc_main_courante": data.get("esc_main_courante", ""),
        "bdc_esc_nez_de_marches": data.get("esc_nez_de_marche", ""),
        "bdc_esc_poteaux_depart": data.get("esc_poteaux_depart", ""),
        "bdc_esc_tete_de_poteau": data.get("esc_tete_de_poteau", ""),
        "bdc_esc_section_remplissage_garde_corps_rampant": data.get("remplissage_rampant", ""),
        "bdc_esc_section_remplissage_garde_corps_etage": data.get("remplissage_etage", ""),
        "bdc_esc_remplissage_garde_corps_soubassement": data.get("remplissage_soubassement", ""),
        "pose_sold": bool(data.get("pose_sold", False)),
    }

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

    mapped["bdc_chk_livraison_poseur"] = bool(mapped["pose_sold"])
    mapped["bdc_chk_livraison_client"] = not bool(mapped["pose_sold"])
    mapped["bdc_chk_autoliquidation"] = bool(mapped["pose_sold"])

    depot_address = ""
    if config:
        depot_address = str(config.get("depot_address", "")).strip()
    if mapped["pose_sold"] and depot_address:
        mapped["bdc_livraison_bloc"] = depot_address

    return mapped, warnings
