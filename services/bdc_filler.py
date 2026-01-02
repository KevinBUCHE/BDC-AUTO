from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, BooleanObject, DictionaryObject, NameObject, TextStringObject
from pypdf.generic._data_structures import IndirectObject

from services.rules import CRITICAL_FIELDS


def _resolve(obj):
    return obj.get_object() if hasattr(obj, "get_object") else obj


def _prepare_acroform(writer: PdfWriter) -> None:
    acroform_ref = writer._root_object.get("/AcroForm")
    acroform = _resolve(acroform_ref) if acroform_ref else DictionaryObject()
    writer._root_object[NameObject("/AcroForm")] = acroform
    if "/Fields" not in acroform or not isinstance(acroform.get("/Fields"), ArrayObject):
        acroform[NameObject("/Fields")] = ArrayObject()
    acroform[NameObject("/NeedAppearances")] = BooleanObject(True)


def _field_name_any(obj: DictionaryObject) -> str:
    name = obj.get("/T")
    return str(name) if name else ""


def _field_name(annotation: DictionaryObject) -> str:
    name = _field_name_any(annotation)
    if name:
        return name
    parent = _resolve(annotation.get("/Parent"))
    if isinstance(parent, dict):
        return _field_name_any(parent)
    return ""


def _field_ft(field: DictionaryObject, widget: DictionaryObject) -> NameObject | None:
    ft = field.get("/FT") if isinstance(field, dict) else None
    if not ft:
        ft = widget.get("/FT")
    return ft if isinstance(ft, NameObject) else None


def _get_field_and_widget(annot: DictionaryObject) -> tuple[DictionaryObject, DictionaryObject]:
    widget = annot
    parent = _resolve(widget.get("/Parent"))
    field = parent if isinstance(parent, dict) else widget
    return field, widget


def iter_widgets(reader_or_writer) -> List[DictionaryObject]:
    widgets: List[DictionaryObject] = []
    for page in reader_or_writer.pages:
        for annot_ref in page.get("/Annots", []):
            annot = _resolve(annot_ref)
            if isinstance(annot, DictionaryObject) and annot.get("/Subtype") == NameObject("/Widget"):
                widgets.append(annot)
    return widgets


def _checkbox_states(widget: DictionaryObject) -> tuple[NameObject, NameObject, bool]:
    warning = False
    off_state = NameObject("/Off")
    on_state: NameObject | None = None
    ap = _resolve(widget.get("/AP"))
    if isinstance(ap, dict):
        n_dict = _resolve(ap.get("/N"))
        if isinstance(n_dict, dict):
            for key in n_dict.keys():
                key_name = key if isinstance(key, NameObject) else NameObject(str(key))
                if key_name != off_state:
                    on_state = key_name
                    break
        else:
            warning = True
    else:
        warning = True
    if on_state is None:
        on_state = NameObject("/Yes")
    return on_state, off_state, warning


def safe_extract_field_values(reader: PdfReader) -> Dict[str, object]:
    values: Dict[str, object] = {}
    for widget in iter_widgets(reader):
        field, resolved_widget = _get_field_and_widget(widget)
        name = _field_name_any(field) or _field_name_any(resolved_widget)
        if not name:
            continue
        val = field.get("/V") or resolved_widget.get("/V")
        values[name] = val
    return values


def fill_bdc(template_path: Path, output_path: Path, data: Dict[str, object]) -> List[str]:
    warnings: List[str] = []

    reader = PdfReader(str(template_path))
    writer = PdfWriter()
    writer.clone_reader_document_root(reader)
    _prepare_acroform(writer)

    text_updates: Dict[str, str] = {}
    checkbox_updates: Dict[str, bool] = {}
    found_names: set[str] = set()
    allowed_fields = set(key for key in data.keys() if isinstance(key, str) and key.startswith("bdc_"))

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
            field, widget = _get_field_and_widget(annotation)
            key = _field_name_any(field) or _field_name_any(widget)
            if not key:
                continue
            if key not in allowed_fields and key not in text_updates and key not in checkbox_updates:
                continue
            found_names.add(key)
            if key in text_updates:
                val = TextStringObject(text_updates[key])
                field[NameObject("/V")] = val
                field[NameObject("/DV")] = val
                widget[NameObject("/V")] = val
                widget[NameObject("/DV")] = val
            if key in checkbox_updates:
                on, off, state_warning = _checkbox_states(widget)
                if state_warning:
                    warnings.append(f"Checkbox {key} sans /AP /N: fallback état {on}")
                v = on if checkbox_updates[key] else off
                field[NameObject("/V")] = v
                widget[NameObject("/V")] = v
                widget[NameObject("/AS")] = v
                kids = field.get("/Kids")
                if kids:
                    for kid_ref in kids:
                        kid = _resolve(kid_ref)
                        if isinstance(kid, DictionaryObject):
                            kid[NameObject("/AS")] = v
                            kid[NameObject("/V")] = v

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
    validation_fields = safe_extract_field_values(validation_reader)

    for field in CRITICAL_FIELDS:
        if field not in validation_fields:
            warnings.append(f"Champ critique absent: {field}")
            continue
        value = validation_fields[field]
        if value in (None, "", NameObject(""), NameObject("/Off")):
            raise ValueError(f"Le champ critique {field} n'est pas rempli")

    return warnings
