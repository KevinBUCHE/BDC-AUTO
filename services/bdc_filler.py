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


def _resolve(obj):
    return obj.get_object() if hasattr(obj, "get_object") else obj


def _field_name(annotation: DictionaryObject) -> str:
    name = annotation.get("/T")
    if name:
        return str(name)
    parent = _resolve(annotation.get("/Parent"))
    if isinstance(parent, dict):
        pname = parent.get("/T")
        if pname:
            return str(pname)
    return ""


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
            key = _field_name(annotation)
            if key in updates:
                val = TextStringObject(updates[key])
                annotation[NameObject("/V")] = val
                annotation[NameObject("/DV")] = val
                parent = _resolve(annotation.get("/Parent"))
                if isinstance(parent, dict):
                    parent[NameObject("/V")] = val
                    parent[NameObject("/DV")] = val


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
        annotations = page.get("/Annots", [])
        for annotation_ref in annotations:
            annotation = _resolve(annotation_ref)
            if not isinstance(annotation, DictionaryObject):
                continue
            if annotation.get("/Subtype") != NameObject("/Widget"):
                continue
            key = _field_name(annotation)
            if not key:
                continue
            if key in text_updates:
                try:
                    writer.update_page_form_field_values(page, {key: text_updates[key]}, auto_regenerate=False)
                except Exception:
                    _manual_fill_text_fields(writer, {key: text_updates[key]})
            if key in checkbox_updates:
                on = NameObject("/Yes")
                off = NameObject("/Off")
                v = on if checkbox_updates[key] else off
                try:
                    annotation[NameObject("/V")] = v
                    annotation[NameObject("/AS")] = v
                    parent = _resolve(annotation.get("/Parent"))
                    if isinstance(parent, dict):
                        parent[NameObject("/V")] = v
                        parent[NameObject("/AS")] = v
                except Exception as exc:
                    warnings.append(f"Checkbox {key or '<sans nom>'} fallback sans /AP: {exc}")

    found_names = set()
    for page in writer.pages:
        annotations = page.get("/Annots", [])
        for annotation_ref in annotations:
            annotation = _resolve(annotation_ref)
            if not isinstance(annotation, DictionaryObject):
                continue
            if annotation.get("/Subtype") != NameObject("/Widget"):
                continue
            key = _field_name(annotation)
            if key:
                found_names.add(key)

    for checkbox_name in checkbox_updates:
        if checkbox_name not in found_names:
            warnings.append(f"Champ checkbox absent dans le template: {checkbox_name}")

    for text_name in text_updates:
        if text_name not in found_names:
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
