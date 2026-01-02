from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, BooleanObject, DictionaryObject, NameObject, NumberObject
from pypdf.generic import RectangleObject, TextStringObject

from services import bdc_filler
from services.bdc_filler import safe_extract_field_values


TEXT_FIELDS = [
    "bdc_devis_annee_mois",
    "bdc_ref_affaire",
    "bdc_client_nom",
    "bdc_commercial_nom",
    "bdc_montant_fourniture_ht",
]

CHECKBOX_FIELDS = [
    "bdc_chk_autoliquidation",
    "bdc_chk_livraison_poseur",
    "bdc_chk_livraison_client",
]


def _text_widget(field_name: str, rect: tuple[float, float, float, float]) -> DictionaryObject:
    return DictionaryObject(
        {
            NameObject("/FT"): NameObject("/Tx"),
            NameObject("/T"): TextStringObject(field_name),
            NameObject("/Rect"): RectangleObject(rect),
            NameObject("/V"): TextStringObject(""),
            NameObject("/Ff"): NumberObject(0),
            NameObject("/Subtype"): NameObject("/Widget"),
            NameObject("/Type"): NameObject("/Annot"),
        }
    )


def _checkbox_widget(field_name: str, rect: tuple[float, float, float, float]) -> DictionaryObject:
    return DictionaryObject(
        {
            NameObject("/FT"): NameObject("/Btn"),
            NameObject("/T"): TextStringObject(field_name),
            NameObject("/Rect"): RectangleObject(rect),
            NameObject("/V"): NameObject("/Off"),
            NameObject("/AS"): NameObject("/Off"),
            NameObject("/Ff"): NumberObject(0),
            NameObject("/Subtype"): NameObject("/Widget"),
            NameObject("/Type"): NameObject("/Annot"),
        }
    )


def _checkbox_widget_without_ap(field_name: str, rect: tuple[float, float, float, float]) -> DictionaryObject:
    widget = _checkbox_widget(field_name, rect)
    # Remove appearances to simulate templates lacking /AP or /N
    if "/AP" in widget:
        del widget[NameObject("/AP")]
    return widget


def _create_template(path: Path) -> None:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)

    fields: list[DictionaryObject] = []

    for idx, name in enumerate(TEXT_FIELDS):
        widget = _text_widget(name, (50, 750 - idx * 30, 300, 770 - idx * 30))
        fields.append(widget)
    for idx, name in enumerate(CHECKBOX_FIELDS):
        widget = _checkbox_widget(name, (350, 750 - idx * 20, 365, 765 - idx * 20))
        fields.append(widget)

    page[NameObject("/Annots")] = ArrayObject(fields)

    writer._root_object.update(
        {
            NameObject("/AcroForm"): writer._add_object(
                DictionaryObject(
                    {
                        NameObject("/Fields"): ArrayObject([writer._add_object(f) for f in fields]),
                        NameObject("/NeedAppearances"): BooleanObject(True),
                    }
                )
            )
        }
    )
    writer.write(path)


def _create_template_without_ap_checkbox(path: Path) -> None:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)

    fields: list[DictionaryObject] = []

    checkbox = _checkbox_widget_without_ap("bdc_chk_autoliquidation", (350, 750, 365, 765))
    fields.append(checkbox)

    page[NameObject("/Annots")] = ArrayObject(fields)

    writer._root_object.update(
        {
            NameObject("/AcroForm"): writer._add_object(
                DictionaryObject(
                    {
                        NameObject("/Fields"): ArrayObject([writer._add_object(f) for f in fields]),
                        NameObject("/NeedAppearances"): BooleanObject(True),
                    }
                )
            )
        }
    )
    writer.write(path)


def test_fill_populates_fields(tmp_path: Path):
    template_path = tmp_path / "template.pdf"
    output_path = tmp_path / "output.pdf"

    _create_template(template_path)

    data = {
        "bdc_devis_annee_mois": "SRX2512AFF003105",
        "bdc_ref_affaire": "AFF-42",
        "bdc_client_nom": "CLIENT DEMO",
        "bdc_commercial_nom": "Commercial Test",
        "bdc_montant_fourniture_ht": "9 979,94",
        "bdc_montant_pose_ht": "1 200,00",
        "pose_sold": True,
        "bdc_chk_autoliquidation": True,
        "bdc_chk_livraison_poseur": True,
        "bdc_chk_livraison_client": False,
    }

    warnings = bdc_filler.fill_bdc(template_path, output_path, data)
    assert isinstance(warnings, list)

    reader = PdfReader(str(output_path))
    fields = safe_extract_field_values(reader)

    for key in TEXT_FIELDS:
        assert fields[key]

    assert fields["bdc_chk_autoliquidation"] == fields["bdc_chk_livraison_poseur"]
    assert fields["bdc_chk_livraison_client"] != fields["bdc_chk_livraison_poseur"]


def test_fill_checkbox_without_ap_does_not_crash(tmp_path: Path):
    template_path = tmp_path / "template_no_ap.pdf"
    output_path = tmp_path / "output_no_ap.pdf"

    _create_template_without_ap_checkbox(template_path)

    data = {
        "bdc_chk_autoliquidation": True,
    }

    warnings = bdc_filler.fill_bdc(template_path, output_path, data)
    assert isinstance(warnings, list)

    reader = PdfReader(str(output_path))
    fields = safe_extract_field_values(reader)
    assert fields["bdc_chk_autoliquidation"] != NameObject("/Off")
