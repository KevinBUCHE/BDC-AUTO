import argparse
import json
import sys
from pathlib import Path

from services import bdc_filler, devis_parser, rules, sanitize


def load_config(config_path: Path | None = None) -> dict:
    candidates = []
    if config_path:
        candidates.append(config_path)
    else:
        candidates.append(Path(__file__).resolve().parent / "config.json")
        candidates.append(Path.cwd() / "config.json")
        if hasattr(sys, "_MEIPASS"):
            candidates.append(Path(getattr(sys, "_MEIPASS")) / "config.json")
        candidates.append(Path(sys.executable).resolve().parent / "config.json")

    for path in candidates:
        if path.exists():
            with path.open("r", encoding="utf-8") as config_file:
                return json.load(config_file)

    raise FileNotFoundError("config.json introuvable")


def parse_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    lowered = value.lower()
    if lowered in {"true", "1", "yes", "y"}:
        return True
    if lowered in {"false", "0", "no", "n"}:
        return False
    raise ValueError(f"Invalid boolean value: {value}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Génération automatique de bon de commande")
    parser.add_argument("--input", required=True, help="Chemin du devis PDF à analyser")
    parser.add_argument(
        "--template",
        required=True,
        help="Chemin du template PDF 'bon de commande V1.pdf'",
    )
    parser.add_argument("--output", required=True, help="Chemin du PDF de sortie")
    parser.add_argument(
        "--pose",
        required=False,
        help="Forcer la détection de pose vendue (true|false)",
    )
    parser.add_argument(
        "--debug-json",
        dest="debug_json",
        required=False,
        help="Écrit le JSON final utilisé pour remplir le BDC",
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    template_path = Path(args.template)
    output_path = Path(args.output)
    debug_json_path = Path(args.debug_json) if args.debug_json else None

    pose_override = parse_bool(args.pose) if args.pose is not None else None

    config = load_config()

    parsed_data, parse_warnings = devis_parser.parse_devis(input_path)
    sanitized_data, sanitize_warnings = sanitize.apply_sanitize(parsed_data, config)
    mapped_data, mapping_warnings = rules.apply_rules(
        sanitized_data, config, pose_override=pose_override
    )

    all_warnings = parse_warnings + sanitize_warnings + mapping_warnings

    if debug_json_path:
        debug_json_path.parent.mkdir(parents=True, exist_ok=True)
        with debug_json_path.open("w", encoding="utf-8") as debug_file:
            json.dump(mapped_data, debug_file, ensure_ascii=False, indent=2)

    fill_warnings = bdc_filler.fill_bdc(
        template_path=template_path,
        output_path=output_path,
        data=mapped_data,
    )

    all_warnings.extend(fill_warnings)

    if all_warnings:
        print("Warnings:")
        for warn in all_warnings:
            print(f"- {warn}")


if __name__ == "__main__":
    main()
