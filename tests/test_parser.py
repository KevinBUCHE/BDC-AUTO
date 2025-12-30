from pathlib import Path
import json

from services import devis_parser, sanitize

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def load_cases():
    for case_dir in FIXTURES_DIR.iterdir():
        if case_dir.is_dir():
            expected_path = case_dir / "expected.json"
            source_path = case_dir / "source.pdf"
            if expected_path.exists() and source_path.exists():
                yield case_dir.name, source_path, expected_path


def test_parser_against_fixtures():
    cases = list(load_cases())
    assert cases, "Aucune fixture trouvée"

    for case_id, source_path, expected_path in cases:
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        parsed, warnings = devis_parser.parse_devis(source_path)
        sanitized, _ = sanitize.apply_sanitize(parsed, {"riaux_blacklist": []})

        for key in [
            "devis_full",
            "ref_affaire",
            "client_nom",
            "commercial_nom",
            "fourniture_ht",
            "prestations_ht",
            "pose_sold",
        ]:
            assert sanitized.get(key) == expected.get(key), f"{case_id}: {key} mismatch"

        assert isinstance(warnings, list)
