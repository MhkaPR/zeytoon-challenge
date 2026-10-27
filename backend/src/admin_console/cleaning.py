"""Automatic data-cleaning rules engine (FR-032, FR-033, research R12).

Cleaning standardizes mapped values so filters can be applied: units and numbers are
normalized, textual noise is stripped, and enum categories are canonicalized against the
plan schema. The rule set and every threshold live in constance
(``CLEANING_RULES`` / ``CLEANING_UNIT_FAMILIES``), read through
:mod:`admin_console.constants`, so operations tune behavior without a code change
(Principle XIII, FR-043).

The engine is automatic-first (FR-033): it returns, per value, a ``clean`` outcome with
the standardized value or an ``exception`` outcome with a machine-readable reason. Only
exceptions are surfaced to the operator; a record keeps every field it could clean and
stays publishable even when other fields raised exceptions.
"""

import re

from admin_console import constants
from admin_console.plan_schema import PLAN_SCHEMA

CLEAN = "clean"
EXCEPTION = "exception"

# Persian/Arabic-Indic digits and their ASCII equivalents.
_DIGIT_MAP = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"
)
# Thousand separators that appear in scraped plan tables.
_THOUSAND_SEPARATORS = (",", "٬", "،", " ", "\u00a0", "\u202f")
_NUMBER_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")
_UNIT_RE = re.compile(r"([A-Za-z\u0600-\u06FF]+)")


def _normalize_text(value):
    return re.sub(r"\s+", " ", str(value)).strip()


def _to_ascii_digits(value):
    return str(value).translate(_DIGIT_MAP)


def _unit_tables():
    families = constants.cleaning_unit_families() or {}
    tables = {}
    for family, spec in families.items():
        units = {str(k).upper(): float(v) for k, v in (spec.get("units") or {}).items()}
        aliases = {
            str(k).upper(): str(v).upper()
            for k, v in (spec.get("aliases") or {}).items()
        }
        tables[family] = {
            "base": str(spec.get("base", "")),
            "units": units,
            "aliases": aliases,
        }
    return tables


def _parse_number(text):
    """Extract the numeric part of ``text`` (``"1,234.5 GB"`` -> ``1234.5``)."""
    normalized = _to_ascii_digits(text)
    for separator in _THOUSAND_SEPARATORS:
        normalized = normalized.replace(separator, "")
    match = _NUMBER_RE.search(normalized)
    return float(match.group()) if match else None


def _parse_unit(text):
    """Return the trailing unit token of ``text`` uppercased, or ``""``."""
    normalized = _to_ascii_digits(text)
    matches = _UNIT_RE.findall(normalized.replace(",", ""))
    return matches[-1].upper() if matches else ""


def _clean_number(field, raw, rule, unit_tables):
    """Standardize a numeric value, converting its unit family to the base unit."""
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return float(raw), None
    text = _normalize_text(raw)
    if not text:
        return None, "missing_number"
    number = _parse_number(text)
    if number is None:
        return None, "unparsable_number"

    family = rule.get("unit_family") or field.unit_family
    table = unit_tables.get(family)
    if table:
        unit = _parse_unit(text) or str(table.get("base", "")).upper()
        unit = table["aliases"].get(unit, unit)
        factor = table["units"].get(unit)
        if factor is None:
            return None, f"unknown_unit:{unit}"
        number *= factor
    return number, None


def _clean_text(field, raw, rule):
    text = _normalize_text(raw)
    if not text:
        return None, "missing_text"
    for old, new in (rule.get("replace") or {}).items():
        text = text.replace(str(old), str(new))
    if rule.get("strip_currency"):
        text = re.sub(r"[^\w\s.%/-]", "", text).strip()
    return text, None


def _clean_enum(field, raw, rule):
    text = _normalize_text(raw)
    if not text:
        return None, "missing_enum"
    aliases = {str(k).strip().lower(): v for k, v in (rule.get("aliases") or {}).items()}
    values = {str(v).strip().lower(): v for v in field.values}
    key = text.lower()
    if key in aliases:
        return aliases[key], None
    if key in values:
        return values[key], None
    # Fall back to the first enum value whose canonical form is contained in the text.
    for lowered, canonical in values.items():
        if lowered and lowered in key:
            return canonical, None
    return text, f"unknown_category:{text}"


def clean_value(field, raw):
    """Clean one schema field value.

    Returns ``{"value": ..., "outcome": "clean"|"exception", "reason": str}``. A missing
    value on an optional field is a clean ``None``; a missing required value is an
    exception so the operator sees exactly what could not be resolved (FR-033).
    """
    rule = (constants.cleaning_rules() or {}).get(field.key) or {}
    unit_tables = _unit_tables()

    if raw is None or (isinstance(raw, str) and not raw.strip()):
        if field.required:
            return {"value": None, "outcome": EXCEPTION, "reason": "missing_required"}
        return {"value": None, "outcome": CLEAN, "reason": ""}

    if field.kind == "number":
        value, reason = _clean_number(field, raw, rule, unit_tables)
    elif field.kind == "enum":
        value, reason = _clean_enum(field, raw, rule)
    else:
        value, reason = _clean_text(field, raw, rule)

    if reason is None:
        return {"value": value, "outcome": CLEAN, "reason": ""}
    return {"value": None, "outcome": EXCEPTION, "reason": reason}


def clean_record(plan_type, values):
    """Clean a full record's ``{schema_field_key: raw}`` map.

    Returns ``(cleaned, exceptions)``: ``cleaned`` keeps every resolvable field;
    ``exceptions`` maps the leftover field keys to their reason. A field missing from
    ``values`` is treated as absent (required -> exception).
    """
    plan = PLAN_SCHEMA.get(plan_type)
    if plan is None:
        return dict(values or {}), {}

    cleaned = {}
    exceptions = {}
    for field in plan.fields:
        result = clean_value(field, (values or {}).get(field.key))
        if result["outcome"] == CLEAN:
            if result["value"] is not None:
                cleaned[field.key] = result["value"]
        else:
            exceptions[field.key] = result["reason"]
    return cleaned, exceptions
