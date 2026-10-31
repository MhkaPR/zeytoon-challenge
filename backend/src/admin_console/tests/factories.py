"""Helpers for building valid domtrack traces and stubbing external stages in tests."""

import json


def _el(nid, tag, text=None, children=None, attrs=None):
    node = {
        "id": nid,
        "type": 2,
        "tagName": tag,
        "attributes": attrs or {},
        "childNodes": children or [],
    }
    if text is not None:
        node["childNodes"] = [{"id": nid * 1000 + 1, "type": 3, "textContent": text}]
    return node


def make_trace(rows=None, url="https://example.com/p"):
    """Build a minimal rrweb-style trace with a simple table domtrack can extract.

    Each cell carries a per-column class so domtrack's discovery sees distinct column
    paths (a plain ``<td>`` grid collapses to a single column).
    """
    rows = rows if rows is not None else [
        ["Plan 0", "100", "200"],
        ["Plan 1", "101", "201"],
        ["Plan 2", "102", "202"],
    ]
    body_children = []
    if rows:
        trs = []
        nid = 100
        for row in rows:
            cells = [
                _el(nid + i + 1, "td", text=str(cell), attrs={"class": f"col-{i}"})
                for i, cell in enumerate(row)
            ]
            trs.append(_el(nid, "tr", children=cells))
            nid += 100
        body_children.append(_el(1, "table", children=trs))
    root = _el(0, "body", children=body_children or [_el(5, "p", text="no tables")])
    return {
        "meta": {"url": url},
        "snapshot": {"node": root},
        "records": [],
        "events": [],
    }


def make_trace_bytes(rows=None, url="https://example.com/p"):
    return json.dumps(make_trace(rows=rows, url=url)).encode("utf-8")


def domtrack_table_result(columns=3, rows=None, score=1.0):
    """A canned ``domtrack tables extract`` result for stubbing the adapter."""
    rows = rows if rows is not None else [
        ["Plan 0", "100", "200"],
        ["Plan 1", "101", "201"],
        ["Plan 2", "102", "202"],
    ]
    cols = [
        {
            "id": f"col-{i}",
            "label": f"Column {i}",
            "path": f"table > tr > td.col-{i}",
            "atype": "text",
            "slot": None,
            "coverage": 1.0,
            "row_count": len(rows),
        }
        for i in range(columns)
    ]
    table_rows = [
        {f"col-{i}": row[i] for i in range(columns)} for row in rows
    ]
    return {
        "total_candidates": 1,
        "tables_returned": 1,
        "tables": [
            {
                "parent": {"id": 1, "tag": "table", "classes": []},
                "meta": {"row_count": len(rows), "columns": columns},
                "columns": cols,
                "rows": table_rows,
                "row_count": len(rows),
                "column_count": columns,
                "score": score,
            }
        ],
    }
