from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.annotations import AnnotationBuilder

from services import bdc_filler


TEXT_FIELDS = [
    "bdc_devis_annee_mois",
    "bdc_ref_affaire",
    "bdc_client_nom",
    "bdc_commercial_nom",
    "bdc_montant_fourniture_ht",
    "bdc_montant_pose_ht",
]

CHECKBOX_FIELDS = [
    "bdc_chk_avec-contre-marches",
    "bdc_chk_avec-sans-marches",
    "bdc_chk_autoliquidation",
]


def _create_template(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)

    for idx, name in enumerate(TEXT_FIELDS):
        annotation = AnnotationBuilder.text_widget(
            rect=(50, 750 - idx * 30, 300, 770 - idx * 30),
            field_name=name,
            font="Helvetica",
            font_size=10,
            text="",
        )
        writer.add_annotation(page_number=0, annotation=annotation)

    for idx, name in enumerate(CHECKBOX_FIELDS):
        annotation = AnnotationBuilder.checkbox(
            rect=(350, 750 - idx * 20, 365, 765 - idx * 20), field_name=name
        )
        writer.add_annotation(page_number=0, annotation=annotation)

    writer.write(path)


def test_fill_populates_fields(tmp_path: Path):
    template_path = tmp_path / "template.pdf"
    output_path = tmp_path / "output.pdf"

    _create_template(template_path)

    data = {
        "bdc_devis_annee_mois": "SRX2512AFF003105",
        "bdc_ref_affaire": "AFF-42",
        "bdc_client_nom": "Client Demo",
        "bdc_commercial_nom": "Commercial Test",
        "bdc_montant_fourniture_ht": "9 979,94",
        "bdc_montant_pose_ht": "1 200,00",
        "pose_sold": True,
        "bdc_chk_avec-contre-marches": True,
        "bdc_chk_avec-sans-marches": False,
        "bdc_chk_autoliquidation": True,
    }

    warnings = bdc_filler.fill_bdc(template_path, output_path, data)
    assert isinstance(warnings, list)

    reader = PdfReader(str(output_path))
    fields = reader.get_fields()

    for key in TEXT_FIELDS:
        assert fields[key]["/V"]

    assert fields["bdc_chk_avec-contre-marches"]["/V"] != fields[
        "bdc_chk_avec-sans-marches"
    ]["/V"]
    assert fields["bdc_chk_autoliquidation"]["/V"]
