from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, BooleanObject, DictionaryObject, NameObject, TextStringObject
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


def _resolve(obj):
    return obj.get_object() if hasattr(obj, "get_object") else obj


def _checkbox_on_value(annotation: dict) -> NameObject:
    try:
        ap = _resolve(annotation.get("/AP"))
        if isinstance(ap, dict):
            n_dict = _resolve(ap.get("/N"))
            if isinstance(n_dict, dict):
                for key in n_dict.keys():
                    name_key = NameObject(key)
                    if name_key != NameObject("/Off"):
                        return name_key
    except Exception:
        pass
    return NameObject("/Yes")


def _set_checkbox(annotation: dict, value: bool) -> None:
    on_value = NameObject("/Yes")
    off_value = NameObject("/Off")
    try:
        on_value = _checkbox_on_value(annotation)
    except Exception:
        on_value = NameObject("/Yes")
    annotation[NameObject("/V")] = on_value if value else off_value
    annotation[NameObject("/AS")] = on_value if value else off_value
    parent = _resolve(annotation.get("/Parent"))
    if isinstance(parent, dict):
        parent[NameObject("/V")] = on_value if value else off_value


def _iter_acroform_fields(writer: PdfWriter) -> list[DictionaryObject]:
    acro = writer._root_object.get("/AcroForm")
    if acro is None:
        return []
    acro = _resolve(acro)
    fields = acro.get("/Fields", [])
    resolved: list[DictionaryObject] = []
    for field in fields:
        obj = _resolve(field)
        if isinstance(obj, DictionaryObject):
            resolved.append(obj)
    return resolved


def _manual_fill_text_fields(writer: PdfWriter, updates: Dict[str, str]) -> None:
    for page in writer.pages:
        annotations = page.get("/Annots", [])
        for annotation_ref in annotations:
            annotation = _resolve(annotation_ref)
            if not isinstance(annotation, DictionaryObject):
                continue
            if annotation.get("/Subtype") != NameObject("/Widget"):
                continue
            field_name = annotation.get("/T")
            key = str(field_name) if field_name else ""
            if key in updates:
                annotation[NameObject("/V")] = TextStringObject(updates[key])
                annotation[NameObject("/DV")] = TextStringObject(updates[key])


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

    acro_fields = _iter_acroform_fields(writer)

    for field in acro_fields:
        name = field.get("/T")
        key = str(name) if name else ""
        if key and key in text_updates:
            field[NameObject("/V")] = TextStringObject(text_updates[key])
            field[NameObject("/DV")] = TextStringObject(text_updates[key])
        if key and key in checkbox_updates:
            _set_checkbox(field, checkbox_updates[key])

    for page in writer.pages:
        annotations = page.get("/Annots", [])
        for annotation_ref in annotations:
            annotation = _resolve(annotation_ref)
            if not isinstance(annotation, DictionaryObject):
                continue
            if annotation.get("/Subtype") != NameObject("/Widget"):
                continue
            field_name = annotation.get("/T")
            key = str(field_name) if field_name else ""
            if key in text_updates:
                try:
                    # prefer pypdf helper, fallback manual
                    writer.update_page_form_field_values(
                        page, {key: text_updates[key]}, auto_regenerate=False
                    )
                except Exception:
                    annotation[NameObject("/V")] = TextStringObject(text_updates[key])
                    annotation[NameObject("/DV")] = TextStringObject(text_updates[key])
            if key in checkbox_updates:
                try:
                    _set_checkbox(annotation, checkbox_updates[key])
                except Exception as exc:
                    warnings.append(f"Checkbox {key or '<sans nom>'} fallback sans /AP: {exc}")

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
