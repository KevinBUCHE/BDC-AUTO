from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Any

APP_NAME = "BDC Generator"
CONFIG_FILENAME = "config.json"
BASE_DIRNAME = "BDC Generator"
TEMPLATE_FILENAME = "bon de commande V1.pdf"

DEFAULT_BLACKLIST = [
    "BAZOUGES",
    "ACACIAS",
    "VAUGARNY",
    "35560",
    "PEROUSE",
    "ALLÉE DES ACACIAS",
    "ALLEE DES ACACIAS",
    "VAUGARNY",
    "BAZOUGES LA PEROUSE",
]


def _desktop_root() -> Path:
    desktop = Path(os.path.expanduser("~")) / "Desktop"
    return desktop / BASE_DIRNAME


def get_app_root() -> Path:
    return _desktop_root()


def get_templates_dir() -> Path:
    return get_app_root() / "Templates"


def get_output_dir(config: Dict[str, Any] | None = None) -> Path:
    if config and config.get("output_dir"):
        return Path(config["output_dir"])
    return get_app_root() / "Output"


def get_config_dir() -> Path:
    return get_app_root() / "Config"


def get_logs_dir() -> Path:
    return get_app_root() / "Logs"


def default_config() -> Dict[str, Any]:
    return {
        "template_path": str(get_templates_dir() / TEMPLATE_FILENAME),
        "output_dir": str(get_output_dir({})),
        "last_open_dir": str(Path.home()),
        "depot_address": "",
        "riaux_blacklist": DEFAULT_BLACKLIST,
    }


def ensure_directories(config: Dict[str, Any]) -> None:
    get_app_root().mkdir(parents=True, exist_ok=True)
    get_templates_dir().mkdir(parents=True, exist_ok=True)
    get_output_dir(config).mkdir(parents=True, exist_ok=True)
    get_config_dir().mkdir(parents=True, exist_ok=True)
    get_logs_dir().mkdir(parents=True, exist_ok=True)


def load_config(explicit_path: Path | None = None) -> Dict[str, Any]:
    config_path = explicit_path or (get_config_dir() / CONFIG_FILENAME)
    cfg: Dict[str, Any] = default_config()
    if config_path.exists():
        try:
            loaded = json.loads(config_path.read_text(encoding="utf-8"))
            cfg.update(loaded)
        except Exception:
            pass
    ensure_directories(cfg)
    save_config(cfg, config_path)
    return cfg


def save_config(config: Dict[str, Any], config_path: Path | None = None) -> None:
    path = config_path or (get_config_dir() / CONFIG_FILENAME)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def copy_default_template_if_available(config: Dict[str, Any], base_dir: Path) -> None:
    source_template = base_dir / "assets" / TEMPLATE_FILENAME
    destination = get_templates_dir() / TEMPLATE_FILENAME
    if source_template.exists() and not destination.exists():
        destination.write_bytes(source_template.read_bytes())
        config["template_path"] = str(destination)
        save_config(config)


def resolve_template_path(config: Dict[str, Any]) -> Path:
    template_path = Path(config.get("template_path", ""))
    if template_path.exists():
        return template_path
    fallback = get_templates_dir() / TEMPLATE_FILENAME
    return fallback
