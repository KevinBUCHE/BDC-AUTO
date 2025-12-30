from __future__ import annotations

from typing import Dict, List, Tuple


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
            if any(token in lowered_line for token in blacklist):
                warnings.append("Adresse RIAUX détectée et supprimée")
                continue
            cleaned_lines.append(line)
        return "\n".join(cleaned_lines).strip()

    for key in ("client_nom", "client_adresse"):
        if key in sanitized:
            sanitized[key] = clean_value(sanitized.get(key, ""))

    return sanitized, warnings
