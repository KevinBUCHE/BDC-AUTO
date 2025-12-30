# BDC-AUTO

Générateur BDC déterministe pour devis SRX (RIAUX) avec interface Tkinter et packaging Windows (PyInstaller).

## Fonctionnalités
- Parsing déterministe via pdfplumber (ancres + regex SRX) avec fallbacks robustes.
- Sanitization anti-RIAUX (blacklist configurable).
- Remplissage PDF via pypdf (champs texte + cases à cocher) avec validation des champs critiques.
- UI Tkinter minimale : sélection multi-devis, sélection/gestion du template, génération BDC, ouverture du dossier Output, log déroulant.
- Debug JSON généré pour chaque devis (`<SRX>_parsed.json`).

## Arborescence utilisateur (créée automatiquement)
```
Desktop/BDC Generator/
  Templates/       # placez ici bon de commande V1.pdf
  Output/          # PDFs générés + JSON debug
  Config/config.json
  Logs/
```
Si `assets/bon de commande V1.pdf` est présent dans le dépôt, il sera copié automatiquement dans `Templates/` au premier lancement.

## Utilisation
1. Lancez **BDC Generator**.
2. Cliquez sur **Choisir devis SRX (PDF)** et sélectionnez un ou plusieurs devis.
3. Vérifiez/choisissez le template via **Choisir template BDC** si nécessaire.
4. Cliquez sur **Générer BDC**. Les PDF générés et les JSON debug sont placés dans `Output/`.
5. **Ouvrir dossier Output** ouvre le dossier de sortie.
6. En usage portable: téléchargez l'artifact, dézippez, placez `bon de commande V1.pdf` dans `Templates/`, puis double-cliquez `RUN.bat` (drag & drop PDF possible). Le BDC et le JSON debug sont dans `Output/`.

## Checklist fichiers à fournir (usage réel)
- Template officiel : copiez `bon de commande V1.pdf` dans `Templates/`.
- Devis SRX : choisissez votre PDF via l’UI ou déposez-le sur `RUN.bat` (portable). Pour vos propres tests manuels, rangez-les dans `samples/` (non versionné).
- Configuration : ajustez `config.json` (ou `Config/config.json`) pour la liste noire ou l’adresse de dépôt.

## Configuration
`Config/config.json` (créé automatiquement) contient :
- `template_path`
- `output_dir`
- `last_open_dir`
- `depot_address`
- `riaux_blacklist`

## Développement
```bash
python -m venv .venv
source .venv/bin/activate  # ou .venv\\Scripts\\activate sous Windows
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

### Build local (portable)
```bash
pyinstaller --noconfirm --clean --onedir --windowed --name "BDC Generator" main.py
```

## Fixtures
Voir `fixtures/README.md` pour ajouter de nouveaux cas de test.
