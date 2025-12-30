# BDC-AUTO

Outil CLI pour générer automatiquement un Bon de Commande à partir d'un devis PDF RIAUX.

## Prérequis
- Python 3.11+
- Template PDF `bon de commande V1.pdf`

## Installation
```bash
python -m venv .venv
source .venv/bin/activate  # ou .venv\\Scripts\\activate sur Windows
pip install -r requirements.txt
```
Pour le développement et les tests :
```bash
pip install -r requirements-dev.txt
```

## Utilisation
```bash
python main.py --input "fixtures/CAS-001/source.pdf" \
  --template "Templates/bon de commande V1.pdf" \
  --output "out.pdf" \
  [--pose true|false] [--debug-json "debug.json"]
```
- Parsing déterministe via pdfplumber.
- Sanitize anti-RIAUX basé sur `config.json`.
- Remplissage PDF via pypdf (texte + cases à cocher).
- `--pose` permet de forcer la valeur détectée dans le devis (pose vendue ou non).
- `--debug-json` écrit le mapping final utilisé pour remplir le BDC.

La configuration (adresse dépôt, blacklist) se trouve dans `config.json`.

## Tests
```bash
python -m pytest -q
```

## Fixtures
Voir `fixtures/README.md` pour ajouter de nouveaux cas.
