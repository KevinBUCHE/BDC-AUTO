# BDC-AUTO

Générateur BDC déterministe pour devis SRX (RIAUX) avec interface Tkinter et installateur Windows.

## Fonctionnalités
- Parsing déterministe via pdfplumber (ancres + regex SRX).
- Sanitization anti-RIAUX (blacklist configurable).
- Remplissage PDF via pypdf (champs texte + cases à cocher) avec validation des champs critiques.
- UI Tkinter minimale : sélection multi-devis, sélection/gestion du template, génération BDC, ouverture du dossier Output, log déroulant.
- Debug JSON généré pour chaque devis (`<SRX>_parsed.json`).

## Installation (utilisateur final)
1. Récupérez l’installateur `BDC_Generator_Setup.exe` depuis les artifacts CI.
2. Exécutez-le (mode *Current user*, pas de droits admin). L’application s’installe dans `%LOCALAPPDATA%\BDC Generator`.
3. Au premier lancement, les dossiers suivants sont créés automatiquement :
   - Templates : `%APPDATA%\BDC Generator\Templates`
   - Output : `%USERPROFILE%\Desktop\BDC_Output`
   - Config : `%APPDATA%\BDC Generator\config.json`
4. Placez le template `bon de commande V1.pdf` dans le dossier Templates (ou sélectionnez-le via le bouton dédié si vous l’avez ailleurs).

## Utilisation
1. Lancez "BDC Generator" (raccourcis Bureau et Menu Démarrer créés par l’installateur).
2. Cliquez sur **Choisir devis SRX (PDF)** et sélectionnez un ou plusieurs devis.
3. Vérifiez/choisissez le template via **Choisir template BDC** si nécessaire.
4. Cliquez sur **Générer BDC**. Les PDF générés et les JSON debug sont placés dans le dossier Output.
5. **Ouvrir dossier Output** ouvre le dossier de sortie.
6. Si un template `assets/bon de commande V1.pdf` est présent dans le dépôt, il sera copié automatiquement vers le dossier Templates lors de l’installation.

## Configuration
`config.json` (créé automatiquement) contient :
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

### Build local (portable + installateur)
```bash
python -m PyInstaller --noconfirm --noconsole --name "BDC Generator" main.py --add-data "config.json;." --add-data "assets;assets"
# Puis, avec Inno Setup installé :
ISCC installer\\bdc_generator.iss
```

## Fixtures
Voir `fixtures/README.md` pour ajouter de nouveaux cas de test.
