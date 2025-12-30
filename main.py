from __future__ import annotations

import json
import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext

from services import bdc_filler, devis_parser, rules, sanitize
from services import config as app_config


class BDCApp:
    def __init__(self, root: tk.Tk, initial_files: list[Path] | None = None):
        self.root = root
        self.root.title("BDC Generator")
        self.root.geometry("720x520")

        self.config = app_config.load_config()
        app_config.copy_default_template_if_available(self.config, Path(__file__).parent)

        self.selected_files: list[Path] = list(initial_files or [])

        self._build_ui()
        self._log(f"Prêt. Dossier base: {app_config.get_app_root()}")
        self._log("Sélectionnez un devis SRX.")

        if self.selected_files:
            self._log(f"Pré-sélection: {', '.join(p.name for p in self.selected_files)}")

    def _build_ui(self) -> None:
        frame = tk.Frame(self.root, padx=10, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        btn_select = tk.Button(frame, text="Choisir devis SRX (PDF)", command=self.choose_devis)
        btn_select.grid(row=0, column=0, sticky="w", padx=5, pady=5)

        btn_template = tk.Button(frame, text="Choisir template BDC", command=self.choose_template)
        btn_template.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        btn_generate = tk.Button(frame, text="Générer BDC", command=self.generate_bdc)
        btn_generate.grid(row=1, column=0, sticky="w", padx=5, pady=5)

        btn_open_output = tk.Button(frame, text="Ouvrir dossier Output", command=self.open_output_dir)
        btn_open_output.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        self.log_area = scrolledtext.ScrolledText(frame, height=20, state=tk.DISABLED)
        self.log_area.grid(row=2, column=0, columnspan=3, sticky="nsew", padx=5, pady=10)

        frame.columnconfigure(2, weight=1)
        frame.rowconfigure(2, weight=1)

    def _log(self, message: str) -> None:
        self.log_area.configure(state=tk.NORMAL)
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.configure(state=tk.DISABLED)
        self.log_area.see(tk.END)

    def choose_devis(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Choisir devis SRX",
            filetypes=[("PDF", "*.pdf"), ("Tous les fichiers", "*.*")],
            initialdir=self.config.get("last_open_dir", str(Path.home())),
        )
        if not paths:
            return
        self.selected_files = [Path(p) for p in paths]
        self.config["last_open_dir"] = str(Path(paths[0]).parent)
        app_config.save_config(self.config)
        self._log(f"Sélectionné(s): {', '.join(Path(p).name for p in paths)}")

    def choose_template(self) -> None:
        path = filedialog.askopenfilename(
            title="Choisir template BDC",
            filetypes=[("PDF", "*.pdf"), ("Tous les fichiers", "*.*")],
            initialdir=str(Path(self.config.get("template_path", app_config.get_templates_dir()))),
        )
        if not path:
            return
        destination = app_config.get_templates_dir() / Path(path).name
        destination.write_bytes(Path(path).read_bytes())
        self.config["template_path"] = str(destination)
        app_config.save_config(self.config)
        self._log(f"Template mis à jour: {destination}")

    def open_output_dir(self) -> None:
        output_dir = Path(self.config.get("output_dir", app_config.get_output_dir(self.config)))
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            if os.name == "nt":
                os.startfile(str(output_dir))  # type: ignore[attr-defined]
            elif os.name == "posix":
                import subprocess

                subprocess.Popen(["xdg-open", str(output_dir)])
        except Exception as exc:
            messagebox.showerror("Erreur", f"Impossible d'ouvrir le dossier: {exc}")

    def generate_bdc(self) -> None:
        if not self.selected_files:
            messagebox.showwarning("Aucun devis", "Sélectionnez au moins un devis PDF.")
            return
        threading.Thread(target=self._generate_worker, daemon=True).start()

    def _generate_worker(self) -> None:
        template_path = app_config.resolve_template_path(self.config)
        if not template_path.exists():
            self._log(
                f"Template introuvable. Placez 'bon de commande V1.pdf' dans {app_config.get_templates_dir()}."
            )
            return

        output_dir = Path(self.config.get("output_dir", app_config.get_output_dir(self.config)))
        output_dir.mkdir(parents=True, exist_ok=True)

        for pdf_path in self.selected_files:
            try:
                self._log(f"Traitement de {pdf_path.name}...")
                parsed, parse_warnings = devis_parser.parse_devis(pdf_path)
                sanitized, sanitize_warnings = sanitize.apply_sanitize(parsed, self.config)
                mapped, mapping_warnings = rules.apply_rules(sanitized, self.config)

                srx = mapped.get("bdc_devis_annee_mois", pdf_path.stem)
                debug_path = output_dir / f"{srx}_parsed.json"
                debug_path.write_text(json.dumps(mapped, ensure_ascii=False, indent=2), encoding="utf-8")

                output_pdf = output_dir / f"{srx}_BDC.pdf"
                fill_warnings = bdc_filler.fill_bdc(template_path, output_pdf, mapped)

                all_warnings = parse_warnings + sanitize_warnings + mapping_warnings + fill_warnings
                if all_warnings:
                    for warn in all_warnings:
                        self._log(f"Warning: {warn}")

                self._log(f"BDC généré: {output_pdf}")
            except Exception as exc:  # noqa: BLE001
                self._log(f"Erreur pour {pdf_path.name}: {exc}")
                messagebox.showerror("Erreur", f"{pdf_path.name}: {exc}")


def ensure_first_run_setup() -> None:
    cfg = app_config.load_config()
    app_config.ensure_directories(cfg)


def main() -> None:
    ensure_first_run_setup()
    initial_files = [Path(arg) for arg in sys.argv[1:] if Path(arg).exists()]
    root = tk.Tk()
    BDCApp(root, initial_files=initial_files)
    root.mainloop()


if __name__ == "__main__":
    main()
