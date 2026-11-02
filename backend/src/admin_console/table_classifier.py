"""Rule-based table classification using admin-managed regular expressions."""

import re

from django.conf import settings

from admin_console.models import ClassificationRegex


class TableClassifier:
    """Classify tables using admin-managed keyword and number regexes."""

    def __init__(self):
        self.minimum_matching_rows = max(2, settings.PRICE_TABLE_MIN_MATCHING_ROWS)
        self.keyword_patterns = self._load_patterns(ClassificationRegex.Kind.KEYWORD)
        self.number_patterns = self._load_patterns(ClassificationRegex.Kind.NUMBER)

    @staticmethod
    def _load_patterns(kind):
        patterns = []
        for entry in ClassificationRegex.objects.filter(kind=kind, is_active=True):
            try:
                patterns.append(re.compile(entry.pattern, re.IGNORECASE))
            except re.error:
                # Invalid patterns should be rejected in admin; skip malformed legacy
                # values so one bad record cannot stop the pipeline.
                continue
        return patterns

    def detect(self, table):
        """Return the decision and number of matching rows; headers are ignored.

        A row matches when a configured keyword and number occur in any of its cells. The
        patterns need not occur in the same cell.
        """
        matching_rows = sum(
            self._row_matches(row.cells or {}) for row in table.rows.all()
        )
        return matching_rows >= self.minimum_matching_rows, matching_rows

    def _row_matches(self, cells):
        values = [str(value) for value in cells.values() if value is not None]
        has_keyword = any(
            pattern.search(value)
            for pattern in self.keyword_patterns
            for value in values
        )
        has_number = any(
            pattern.search(value)
            for pattern in self.number_patterns
            for value in values
        )
        return has_keyword and has_number
