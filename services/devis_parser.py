from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Tuple

import pdfplumber

SRX_PATTERN = re.compile(r"SRX(\d{4})([A-Z]{3})(\d{6})")
PRICE_PATTERN = re.compile(r"(\d[\d\s]*,\d{2})")
CP_VILLE_PATTERN = re.compile(r"\b\d{5}\s+[A-ZÉÈÂÊÎÔÛÄËÏÖÜÀÂÇ\- ]+")
CLIENT_EXCLUDE = {"sas", "rcs", "naf", "capital"}
REF_LINE_REGEX = (
    r"(?:réf\.?\s*affaire|ref\.?\s*affaire|référence\s*affaire|r.{0,2}f\s*affaire)\s*[: ]\s*"
    r"([A-Z0-9][A-Z0-9\-_\/]{1,30})"
)


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
REF_LABELS = ["réf affaire", "ref affaire", "référence affaire", "réf. affaire"]
NBSP = "\u00a0"


class ParsedDevis(Tuple[Dict[str, object], List[str]]):
    pass


def _extract_lines(pdf_path: Path) -> List[str]:
    lines: List[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for raw_line in text.splitlines():
                cleaned = _normalize_line(raw_line)
                if cleaned:
                    lines.append(cleaned)

    if os.getenv("BDC_DEBUG_PARSER") == "1":
        debug_path = pdf_path.with_suffix(".debug_lines.txt")
        debug_path.write_text("\n".join(lines), encoding="utf-8")
        for preview in lines[:30]:
            print(f"[BDC_DEBUG] {preview}")
    return lines


def _find_line(lines: List[str], anchor: str) -> int:
    for idx, line in enumerate(lines):
        if anchor.lower() in line.lower():
            return idx
    return -1


def _find_first_of(lines: List[str], labels: List[str]) -> int:
    for label in labels:
        idx = _find_line(lines, label)
        if idx != -1:
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


def _norm_text(value: str) -> str:
    value = value.replace("\u202f", " ").replace(NBSP, " ")
    value = re.sub(r"\s+", " ", value).strip()
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).lower()


def _normalize_line(value: str) -> str:
    value = value.replace("\u202f", " ").replace(NBSP, " ").replace("：", ":")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _fallback_client(lines: List[str]) -> str:
    for idx, line in enumerate(lines):
        if CP_VILLE_PATTERN.search(line):
            # walk upwards to find a likely client name, skipping metadata lines
            for up in range(idx - 1, -1, -1):
                candidate = lines[up].strip()
                lower = candidate.lower()
                if any(excl in lower for excl in CLIENT_EXCLUDE):
                    continue
                if candidate and not CP_VILLE_PATTERN.search(candidate):
                    return candidate
    for line in lines:
        if line.isupper() and len(line.split()) >= 2 and not CP_VILLE_PATTERN.search(line):
            return line.strip()
    return ""


def _fallback_commercial(lines: List[str]) -> str:
    for idx, line in enumerate(lines):
        if "commercial" in line.lower():
            # try next non-empty line that isn't a CP/Ville
            for next_idx in range(idx + 1, min(len(lines), idx + 3)):
                candidate = lines[next_idx].strip()
                if not candidate:
                    continue
                if CP_VILLE_PATTERN.search(candidate):
                    continue
                return candidate
            return _extract_after_colon(line)
        if "buche" in line.lower():
            return "BUCHE Kevin"
    return ""


def parse_devis(pdf_path: Path) -> ParsedDevis:
    lines = _extract_lines(pdf_path)
    warnings: List[str] = []

    joined_text = "\n".join(lines)
    ref_affaire = ""
    for idx, line in enumerate(lines):
        normalized_line = _normalize_line(line)
        match_line = re.search(REF_LINE_REGEX, normalized_line, flags=re.IGNORECASE)
        if match_line:
            ref_affaire = (match_line.group(1) or "").strip()
            if not ref_affaire:
                for j in range(idx + 1, len(lines)):
                    nxt = lines[j].strip()
                    if nxt:
                        ref_affaire = nxt
                        break
            break

    srx_match = SRX_PATTERN.search(joined_text)
    devis_full = srx_match.group(0) if srx_match else ""
    if not devis_full:
        warnings.append("Numéro de devis introuvable (SRX...)")

    if not ref_affaire:
        for idx, line in enumerate(lines):
            normalized_line = _normalize_line(line)
            normalized = _norm_text(normalized_line)
            if "ref affaire" in normalized or "reference affaire" in normalized:
                regex_line = re.search(
                    r"(?:réf\.?\s*affaire|ref\.?\s*affaire|référence\s*affaire)\s*[: ]\s*([A-Z0-9][A-Z0-9\\-_/]{1,30})",
                    normalized_line,
                    flags=re.IGNORECASE,
                )
                if regex_line:
                    ref_affaire = regex_line.group(1).strip()
                elif ":" in normalized_line:
                    ref_affaire = normalized_line.split(":", 1)[1].strip()
                else:
                    tail_match = re.search(r"(?i)\baffaire\b\s*(.+)$", normalized_line)
                    ref_affaire = tail_match.group(1).strip() if tail_match else ""
                if not ref_affaire:
                    for j in range(idx + 1, len(lines)):
                        nxt = lines[j].strip()
                        if nxt:
                            ref_affaire = nxt
                            break
                break

    if not ref_affaire:
        for idx, line in enumerate(lines):
            normalized_line = _normalize_line(line)
            normalized = _norm_text(normalized_line)
            if "ref affaire" in normalized or "reference affaire" in normalized:
                regex_line = re.search(
                    r"(?:réf\.?\s*affaire|ref\.?\s*affaire|référence\s*affaire)\s*[: ]\s*([A-Z0-9][A-Z0-9\\-_/]{1,30})",
                    normalized_line,
                    flags=re.IGNORECASE,
                )
                if regex_line:
                    ref_affaire = regex_line.group(1).strip()
                elif ":" in normalized_line:
                    ref_affaire = normalized_line.split(":", 1)[1].strip()
                else:
                    tail_match = re.search(r"(?i)\baffaire\b\s*(.+)$", normalized_line)
                    ref_affaire = tail_match.group(1).strip() if tail_match else ""
                if not ref_affaire:
                    for j in range(idx + 1, len(lines)):
                        nxt = lines[j].strip()
                        if nxt:
                            ref_affaire = nxt
                            break
                break

    ref_affaire = ref_affaire.strip(" )]}\u00a0")
    for token in ("CODE", "CLIENT", "CONTACT"):
        if token in ref_affaire.upper():
            ref_affaire = ref_affaire.split(" ")[0]
            break

    client_index = _find_line(lines, ANCHORS["code_client"])
    client_nom = _get_next_line(lines, client_index) if client_index != -1 else ""
    if not client_nom:
        client_nom = _fallback_client(lines)
        warnings.append("Nom client estimé par fallback")

    commercial_index = _find_line(lines, ANCHORS["contact"])
    commercial_nom = ""
    if commercial_index != -1:
        for idx in range(commercial_index + 1, min(len(lines), commercial_index + 6)):
            cand = lines[idx].strip()
            if not cand:
                continue
            if CP_VILLE_PATTERN.search(cand):
                continue
            commercial_nom = cand
            break
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
    if not pose_sold and prestations_ht:
        digits = prestations_ht.replace(" ", "").replace(",", ".")
        try:
            pose_sold = float(digits) > 0
        except ValueError:
            pose_sold = False

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
