from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple

import pdfplumber

SRX_PATTERN = re.compile(r"SRX(\d{4})([A-Z]{3})(\d{6})")
PRICE_PATTERN = re.compile(r"(\d[\d\s]*,\d{2})")


ANCHORS = {
    "devis": "DEVIS",
    "ref_affaire": "Réf affaire",
    "code_client": "Code client",
    "contact": "Contact commercial",
    "modele": "- Modèle",
    "contremarche": "- Contremarche",
    "structure": "- Structure",
    "fourniture": "PRIX DE LA FOURNITURE HT",
    "prestations": "PRIX PRESTATIONS ET SERVICES HT",
    "prestations_section": "PRESTATIONS",
}


class ParsedDevis(Tuple[Dict[str, object], List[str]]):
    pass


def _extract_lines(pdf_path: Path) -> List[str]:
    lines: List[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for raw_line in text.splitlines():
                cleaned = raw_line.replace("\u202f", " ").strip()
                if cleaned:
                    lines.append(cleaned)
    return lines


def _find_line(lines: List[str], anchor: str) -> int:
    for idx, line in enumerate(lines):
        if anchor.lower() in line.lower():
            return idx
    return -1


def _extract_after_colon(line: str) -> str:
    if ":" in line:
        return line.split(":", 1)[1].strip()
    return ""


def _search_price(line: str) -> str:
    match = PRICE_PATTERN.search(line)
    return match.group(1).strip() if match else ""


def _get_next_line(lines: List[str], index: int) -> str:
    if 0 <= index + 1 < len(lines):
        return lines[index + 1].strip()
    return ""


def _fallback_client(lines: List[str]) -> str:
    for line in lines:
        if line.isupper() and len(line.split()) >= 2:
            return line.strip()
    return ""


def _fallback_commercial(lines: List[str]) -> str:
    for line in lines:
        if "commercial" in line.lower():
            return _extract_after_colon(line)
        if "buche" in line.lower():
            return "BUCHE Kevin"
    return ""


def parse_devis(pdf_path: Path) -> ParsedDevis:
    lines = _extract_lines(pdf_path)
    warnings: List[str] = []

    joined_text = "\n".join(lines)
    srx_match = SRX_PATTERN.search(joined_text)
    devis_full = srx_match.group(0) if srx_match else ""
    if not devis_full:
        warnings.append("Numéro de devis introuvable (SRX...)")

    ref_index = _find_line(lines, ANCHORS["ref_affaire"])
    ref_affaire = _extract_after_colon(lines[ref_index]) if ref_index != -1 else ""

    client_index = _find_line(lines, ANCHORS["code_client"])
    client_nom = _get_next_line(lines, client_index) if client_index != -1 else ""
    if not client_nom:
        client_nom = _fallback_client(lines)
        warnings.append("Nom client estimé par fallback")

    commercial_index = _find_line(lines, ANCHORS["contact"])
    commercial_nom = _get_next_line(lines, commercial_index) if commercial_index != -1 else ""
    if not commercial_nom:
        commercial_nom = _fallback_commercial(lines)
        warnings.append("Commercial estimé par fallback")

    gamme_index = _find_line(lines, ANCHORS["modele"])
    esc_gamme = _extract_after_colon(lines[gamme_index]) if gamme_index != -1 else ""

    contremarche_index = _find_line(lines, ANCHORS["contremarche"])
    esc_contremarche = (
        _extract_after_colon(lines[contremarche_index]) if contremarche_index != -1 else ""
    )

    structure_index = _find_line(lines, ANCHORS["structure"])
    esc_structure = _extract_after_colon(lines[structure_index]) if structure_index != -1 else ""

    fourniture_index = _find_line(lines, ANCHORS["fourniture"])
    fourniture_ht = _search_price(lines[fourniture_index]) if fourniture_index != -1 else ""

    prestations_index = _find_line(lines, ANCHORS["prestations"])
    prestations_ht = _search_price(lines[prestations_index]) if prestations_index != -1 else ""

    prestations_section = _find_line(lines, ANCHORS["prestations_section"])
    pose_sold = False
    if prestations_section != -1:
        for line in lines[prestations_section:]:
            if not line.strip():
                break
            if "pose" in line.lower():
                pose_sold = True
                break

    essence = ""
    finition_marches = ""
    finition_structure = ""
    finition_mains = ""
    finition_contremarche = ""
    main_courante = ""
    nez_de_marche = ""
    poteaux_depart = ""
    tete_poteau = ""
    remplissage_rampant = ""
    remplissage_etage = ""
    remplissage_soubassement = ""

    for line in lines:
        lower = line.lower()
        if "marche : essence/finition" in lower:
            details = _extract_after_colon(line)
            if "/" in details:
                essence, finition_marches = [part.strip() for part in details.split("/", 1)]
            else:
                finition_marches = details
        elif "contremarche : essence/finition" in lower:
            details = _extract_after_colon(line)
            if "/" in details and not essence:
                essence, finition_contremarche = [part.strip() for part in details.split("/", 1)]
            else:
                finition_contremarche = details
        elif "structure/poteau : essence/finition" in lower:
            details = _extract_after_colon(line)
            if "/" in details and not essence:
                essence, finition_structure = [part.strip() for part in details.split("/", 1)]
            else:
                finition_structure = details
        elif "main courante" in lower and "essence/finition" in lower:
            details = _extract_after_colon(line)
            if "/" in details and not essence:
                essence, finition_mains = [part.strip() for part in details.split("/", 1)]
            else:
                finition_mains = details
        elif "main courante" in lower:
            main_courante = _extract_after_colon(line)
        elif "nez" in lower and "marche" in lower:
            nez_de_marche = _extract_after_colon(line)
        elif "poteau" in lower and "depart" in lower:
            poteaux_depart = _extract_after_colon(line)
        elif "tête" in lower or "tete" in lower:
            tete_poteau = _extract_after_colon(line)
        elif "remplissage" in lower:
            details = _extract_after_colon(line)
            if not remplissage_rampant:
                remplissage_rampant = details
            elif not remplissage_etage:
                remplissage_etage = details
            else:
                remplissage_soubassement = details

    result: Dict[str, object] = {
        "source_pdf": str(pdf_path),
        "devis_full": devis_full,
        "ref_affaire": ref_affaire,
        "client_nom": client_nom,
        "commercial_nom": commercial_nom,
        "fourniture_ht": fourniture_ht,
        "prestations_ht": prestations_ht,
        "pose_sold": pose_sold,
        "esc_gamme": esc_gamme,
        "esc_essence": essence,
        "esc_finition_marches": finition_marches,
        "esc_finition_structure": finition_structure,
        "esc_finition_mains_courante": finition_mains,
        "esc_finition_contremarche": finition_contremarche,
        "esc_main_courante": main_courante,
        "esc_nez_de_marche": nez_de_marche,
        "esc_poteaux_depart": poteaux_depart,
        "esc_tete_de_poteau": tete_poteau,
        "remplissage_rampant": remplissage_rampant,
        "remplissage_etage": remplissage_etage,
        "remplissage_soubassement": remplissage_soubassement,
        "esc_contremarche": esc_contremarche,
        "esc_structure": esc_structure,
        "parse_warning": " | ".join(warnings) if warnings else "",
    }

    return result, warnings
