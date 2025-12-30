from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, BooleanObject, DictionaryObject, NameObject
from pypdf.generic._data_structures import IndirectObject

from services.rules import CRITICAL_FIELDS


def _prepare_acroform(writer: PdfWriter) -> None:
    acroform_ref = writer._root_object.get("/AcroForm")
    if acroform_ref is None:
        acroform = DictionaryObject()
        writer._root_object[NameObject("/AcroForm")] = acroform
    else:
        acroform = acroform_ref.get_object() if isinstance(acroform_ref, IndirectObject) else acroform_ref
        if not isinstance(acroform, DictionaryObject):
            acroform = DictionaryObject()
            writer._root_object[NameObject("/AcroForm")] = acroform

    if "/Fields" not in acroform:
        acroform[NameObject("/Fields")] = ArrayObject()

    acroform[NameObject("/NeedAppearances")] = BooleanObject(True)


def _checkbox_on_value(annotation: dict) -> NameObject:
    appearances = annotation.get("/AP", {}).get("/N", {})
    for key in appearances.keys():
        if key != NameObject("/Off"):
            return NameObject(key)
    return NameObject("/Yes")


def _set_checkbox(annotation: dict, value: bool) -> None:
    on_value = _checkbox_on_value(annotation)
    annotation.update({NameObject("/V"): on_value if value else NameObject("/Off")})
    annotation.update({NameObject("/AS"): on_value if value else NameObject("/Off")})


def fill_bdc(template_path: Path, output_path: Path, data: Dict[str, object]) -> List[str]:
    warnings: List[str] = []

    reader = PdfReader(str(template_path))
    writer = PdfWriter()
    writer.clone_reader_document_root(reader)
    _prepare_acroform(writer)

    form_fields = reader.get_fields() or {}

    text_updates: Dict[str, str] = {}
    checkbox_updates: Dict[str, bool] = {}

    for key, value in data.items():
        if key == "pose_sold":
            continue
        if isinstance(value, bool):
            checkbox_updates[key] = value
        elif key.startswith("bdc_"):
            text_updates[key] = "" if value is None else str(value)

    for page in writer.pages:
        if text_updates:
            updates = {k: v for k, v in text_updates.items() if k in form_fields}
            if updates:
                try:
                    writer.update_page_form_field_values(page, updates, auto_regenerate=False)
                except TypeError:
                    writer.update_page_form_field_values(page, updates)
        if checkbox_updates:
            annotations = page.get("/Annots", [])
            for annotation_ref in annotations:
                annotation = annotation_ref.get_object() if hasattr(annotation_ref, "get_object") else annotation_ref
                if annotation.get("/Subtype") != NameObject("/Widget"):
                    continue
                field_name = annotation.get("/T")
                if not field_name:
                    continue
                decoded = str(field_name)
                if decoded in checkbox_updates:
                    _set_checkbox(annotation, checkbox_updates[decoded])

    for checkbox_name in checkbox_updates:
        if checkbox_name not in form_fields:
            warnings.append(f"Champ checkbox absent dans le template: {checkbox_name}")

    for text_name in text_updates:
        if text_name not in form_fields:
            warnings.append(f"Champ texte absent dans le template: {text_name}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as output_stream:
        writer.write(output_stream)

    validation_reader = PdfReader(str(output_path))
    validation_fields = validation_reader.get_fields() or {}

    for field in CRITICAL_FIELDS:
        if field not in validation_fields:
            warnings.append(f"Champ critique absent: {field}")
            continue
        value = validation_fields[field].get("/V")
        if value in (None, "", NameObject("")):
            raise ValueError(f"Le champ critique {field} n'est pas rempli")

    return warnings
