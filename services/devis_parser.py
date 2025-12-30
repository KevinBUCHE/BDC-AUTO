from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple

import pdfplumber

SRX_PATTERN = re.compile(r"SRX(\d{4})([A-Z]{3})(\d{6})")
PRICE_PATTERN = re.compile(r"(\d[\d\s]*,\d{2})")


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


def parse_devis(pdf_path: Path) -> Tuple[Dict[str, object], List[str]]:
    lines = _extract_lines(pdf_path)
    warnings: List[str] = []

    joined_text = "\n".join(lines)
    srx_match = SRX_PATTERN.search(joined_text)
    devis_full = srx_match.group(0) if srx_match else ""
    if not devis_full:
        warnings.append("Numéro de devis introuvable (SRX...)")

    ref_index = _find_line(lines, "Réf affaire")
    ref_affaire = _extract_after_colon(lines[ref_index]) if ref_index != -1 else ""
    if not ref_affaire:
        warnings.append("Réf affaire introuvable")

    client_index = _find_line(lines, "Code client")
    client_nom = _get_next_line(lines, client_index) if client_index != -1 else ""
    if not client_nom:
        warnings.append("Nom client introuvable")

    commercial_index = _find_line(lines, "Contact commercial")
    commercial_nom = _get_next_line(lines, commercial_index) if commercial_index != -1 else ""
    if not commercial_nom:
        warnings.append("Contact commercial introuvable")

    gamme_index = _find_line(lines, "- Modèle")
    esc_gamme = _extract_after_colon(lines[gamme_index]) if gamme_index != -1 else ""

    contremarche_index = _find_line(lines, "- Contremarche")
    esc_contremarche = (
        _extract_after_colon(lines[contremarche_index]) if contremarche_index != -1 else ""
    )

    structure_index = _find_line(lines, "- Structure")
    esc_structure = _extract_after_colon(lines[structure_index]) if structure_index != -1 else ""

    tete_poteau_index = _find_line(lines, "Poteau")
    esc_tete_de_poteau = (
        _extract_after_colon(lines[tete_poteau_index]) if tete_poteau_index != -1 else ""
    )

    remplissage_index = _find_line(lines, "Remplissage")
    remplissage = _extract_after_colon(lines[remplissage_index]) if remplissage_index != -1 else ""

    marche_index = _find_line(lines, "Marche : essence/finition")
    esc_essence = ""
    esc_finition_marches = ""
    if marche_index != -1:
        details = _extract_after_colon(lines[marche_index])
        if "/" in details:
            essence_part, finition_part = details.split("/", 1)
            esc_essence = essence_part.strip()
            esc_finition_marches = finition_part.strip()
        else:
            esc_finition_marches = details

    contremarche_finish_index = _find_line(lines, "Contremarche : essence/finition")
    esc_finition_contremarche = ""
    if contremarche_finish_index != -1:
        contremarche_details = _extract_after_colon(lines[contremarche_finish_index])
        if "/" in contremarche_details and not esc_essence:
            esc_essence, esc_finition_contremarche = [
                part.strip() for part in contremarche_details.split("/", 1)
            ]
        else:
            esc_finition_contremarche = contremarche_details.strip()

    structure_finish_index = _find_line(lines, "Structure/Poteau : essence/finition")
    esc_finition_structure = ""
    if structure_finish_index != -1:
        structure_details = _extract_after_colon(lines[structure_finish_index])
        if "/" in structure_details and not esc_essence:
            esc_essence, esc_finition_structure = [
                part.strip() for part in structure_details.split("/", 1)
            ]
        else:
            esc_finition_structure = structure_details.strip()

    main_courante_index = _find_line(lines, "Main courante : essence/finition")
    esc_finition_mains_courante = ""
    if main_courante_index != -1:
        main_details = _extract_after_colon(lines[main_courante_index])
        if "/" in main_details and not esc_essence:
            esc_essence, esc_finition_mains_courante = [
                part.strip() for part in main_details.split("/", 1)
            ]
        else:
            esc_finition_mains_courante = main_details.strip()

    fourniture_index = _find_line(lines, "PRIX DE LA FOURNITURE HT")
    fourniture_ht = _search_price(lines[fourniture_index]) if fourniture_index != -1 else ""
    if not fourniture_ht:
        warnings.append("Montant fourniture HT introuvable")

    prestations_index = _find_line(lines, "PRIX PRESTATIONS ET SERVICES HT")
    prestations_ht = _search_price(lines[prestations_index]) if prestations_index != -1 else ""
    if not prestations_ht:
        warnings.append("Montant prestations HT introuvable")

    prestations_section = _find_line(lines, "PRESTATIONS")
    pose_sold = False
    if prestations_section != -1:
        for line in lines[prestations_section:]:
            if not line.strip():
                break
            if "pose" in line.lower():
                pose_sold = True
                break

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
        "esc_essence": esc_essence,
        "esc_finition_marches": esc_finition_marches,
        "esc_finition_structure": esc_finition_structure,
        "esc_finition_mains_courante": esc_finition_mains_courante,
        "esc_finition_contremarche": esc_finition_contremarche,
        "esc_tete_de_poteau": esc_tete_de_poteau,
        "remplissage_rampant": remplissage,
        "remplissage_etage": "",
        "remplissage_soubassement": "",
        "esc_contremarche": esc_contremarche,
        "esc_structure": esc_structure,
        "remplissage": remplissage,
        "parse_warning": " | ".join(warnings) if warnings else "",
    }

    return result, warnings
