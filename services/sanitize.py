from __future__ import annotations

import re
from typing import Dict, List, Tuple

PRICE_CLEAN_RE = re.compile(r"[^\d,]")


def _group_thousands(euros: str) -> str:
    euros_digits = re.sub(r"\D", "", euros)
    if not euros_digits:
        return ""
    rev = euros_digits[::-1]
    parts = [rev[i : i + 3] for i in range(0, len(rev), 3)]
    return " ".join(p[::-1] for p in parts[::-1])


def normalize_price(value: str) -> str:
    if not value:
        return ""
    cleaned = PRICE_CLEAN_RE.sub("", value)
    parts = cleaned.split(",")
    euros = parts[0] if parts else ""
    cents = parts[1] if len(parts) > 1 else "00"
    euros_fmt = _group_thousands(euros)
    cents_fmt = cents[:2].ljust(2, "0")
    if not euros_fmt:
        return ""
    return f"{euros_fmt},{cents_fmt}"


def apply_sanitize(data: Dict[str, str], config: Dict[str, object]) -> Tuple[Dict[str, str], List[str]]:
    sanitized = dict(data)
    warnings: List[str] = []

    blacklist = [entry.lower() for entry in config.get("riaux_blacklist", [])]

    def clean_value(value: str | None) -> str:
        if not value:
            return ""
        cleaned_lines: List[str] = []
        for line in value.splitlines():
            lowered_line = line.lower()
            if any(token.lower() in lowered_line for token in blacklist):
                warnings.append("Adresse RIAUX détectée et supprimée")
                continue
            cleaned_lines.append(line)
        return "\n".join(cleaned_lines).strip()

    for key in ("client_nom", "client_adresse"):
        if key in sanitized:
            sanitized[key] = clean_value(sanitized.get(key, ""))

    for price_key in ("fourniture_ht", "prestations_ht"):
        sanitized[price_key] = normalize_price(str(sanitized.get(price_key, "")))

    return sanitized, warnings
