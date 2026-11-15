"""Custom django-constance form fields for structured values."""

from __future__ import annotations

import json

from django import forms


class JSONField(forms.CharField):
    """Admin form field that edits a list/dict value as JSON text."""

    def prepare_value(self, value):
        if isinstance(value, (list, dict)):
            return json.dumps(value, ensure_ascii=False, indent=2)
        return value

    def to_python(self, value):
        value = super().to_python(value)
        if value in self.empty_values:
            return None
        if not isinstance(value, str):
            return value
        try:
            return json.loads(value)
        except (TypeError, ValueError) as exc:
            raise forms.ValidationError("Enter valid JSON.") from exc
