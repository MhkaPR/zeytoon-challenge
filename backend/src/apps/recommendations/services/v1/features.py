"""Map published plan ``values`` to comparable recommendation features."""

from apps.catalog.filters import normalize_resource_value


class PlanFeatureMapper:
    """Produces one feature dict per plan, masking attributes the plan omits."""

    @staticmethod
    def _number(values, *keys):
        for key in keys:
            raw = values.get(key)
            if raw is None or raw == "" or isinstance(raw, bool):
                continue
            try:
                return float(raw)
            except (TypeError, ValueError):
                continue
        return None

    @staticmethod
    def _text(values, *keys):
        for key in keys:
            raw = values.get(key)
            if isinstance(raw, str) and raw.strip():
                return raw.strip()
        return None

    def map(self, record):
        values = record.get("values") or {}
        return {
            "id": record.get("id"),
            "published_at": record.get("published_at") or "",
            "price": self._number(values, "price_amount", "price"),
            "cpu": normalize_resource_value("cpu", values),
            "ram": normalize_resource_value("ram", values),
            "disk": normalize_resource_value("disk", values),
            "traffic": normalize_resource_value("traffic", values),
            "country": self._text(values, "location", "datacenter_location"),
            "os": self._text(values, "os", "operating_system"),
        }
