"""Excel/spreadsheet-compatible formula validation and evaluation (FR-028, research R10).

Formulas use spreadsheet syntax (cell/column references, ``+ - * / ^``, comparisons,
string concatenation with ``&``, and a whitelisted function set with ``,`` argument
separators) so a saved expression is valid to paste into Excel/LibreOffice/Sheets.

Nothing is hand-rolled and nothing is ``eval``-ed: parsing and evaluation are delegated
to the maintained ``formulas`` library (Principle XII). We only narrow it to a
whitelisted function/operator set at the boundary and bind the free variables to the
resolved column values, so evaluation is deterministic and has no host access.
"""

import functools
import re

from accounts.exceptions import ApiError
from formulas import Parser
from formulas.tokens import function as _function_tokens

#: Functions an operator may use in a combination formula (FR-028).
ALLOWED_FUNCTIONS = frozenset(
    {
        "SUM",
        "MIN",
        "MAX",
        "AVERAGE",
        "IF",
        "ROUND",
        "VALUE",
        "SUBSTITUTE",
        "TEXT",
        "CONCATENATE",
        "ABS",
        "INT",
        "LEN",
        "TRIM",
    }
)

#: Excel operators/cell syntax we accept; every other token class is rejected.
_ALLOWED_TOKEN_NAMES = frozenset(
    {"Function", "Number", "String", "Range", "OperatorToken", "Parenthesis", "Separator"}
)

_REQUIRED_PREFIX = "="


class FormulaError(ApiError):
    def __init__(self, message, fields=None):
        super().__init__("invalid_field", message, fields=fields or {})


def _iter_tokens(node):
    """Yield every token in the library's flat AST list (it is a nested list/tuple)."""
    if isinstance(node, (list, tuple)):
        for child in node:
            yield from _iter_tokens(child)
    else:
        yield node


def _token_name(token):
    return type(token).__name__


def _assert_allowed(tokens, expression):
    for token in tokens:
        name = _token_name(token)
        if name not in _ALLOWED_TOKEN_NAMES:
            raise FormulaError(
                "The formula contains an unsupported construct.",
                {"formula": expression, "construct": name},
            )
        if isinstance(token, _function_tokens.Function):
            function_name = str(getattr(token, "name", "")).upper()
            if function_name not in ALLOWED_FUNCTIONS:
                raise FormulaError(
                    f"Unknown or unsupported function: {function_name}.",
                    {"formula": expression, "function": function_name},
                )


def _parse(expression):
    """Parse ``expression`` with the library; raise :class:`FormulaError` on failure."""
    try:
        ast, _builder = Parser().ast(expression)
    except FormulaError:
        raise
    except Exception as exc:  # library raises FormulaError/ParenthesesError/TokenError
        raise FormulaError(
            "The formula is not a valid spreadsheet expression.",
            {"formula": expression, "detail": str(exc)},
        ) from exc
    return ast


def validate_formula(formula):
    """Validate ``formula`` and return the normalized ``=...`` string (FR-028).

    An empty formula is allowed (the raw source value is used unchanged).
    """
    if formula is None or not str(formula).strip():
        return ""
    text = str(formula).strip()
    if not text.startswith(_REQUIRED_PREFIX):
        raise FormulaError("A formula must start with '='.", {"formula": text})
    ast = _parse(text)
    _assert_allowed(list(_iter_tokens(ast)), text)
    return text


@functools.lru_cache(maxsize=2048)
def _compile(expression):
    """Compile and cache the library's evaluator for a validated ``=...`` expression."""
    try:
        _ast, builder = Parser().ast(expression)
        return builder.compile()
    except Exception as exc:
        raise FormulaError(
            "The formula could not be prepared for evaluation.",
            {"formula": expression, "detail": str(exc)},
        ) from exc


def _normalize_key(value):
    return str(value).strip().lower()


def _strip_sheet(reference):
    return reference.split("!", 1)[-1]


def _candidate_keys(reference):
    """Yield the lookup keys that may identify the column for a token reference."""
    body = _strip_sheet(reference).strip()
    yield body
    if ":" in body:
        body = body.split(":", 1)[0].strip()
        yield body
    # `A2` / `$A$2` -> column letter `A`; `Price` stays `Price`.
    yield re.sub(r"[^A-Za-z_\u0600-\u06FF]", "", body)


def _bind_inputs(func, columns):
    lookup = {_normalize_key(key): value for key, value in (columns or {}).items()}
    bindings = {}
    for reference in func.inputs:
        value = None
        for candidate in _candidate_keys(reference):
            key = _normalize_key(candidate)
            if key and key in lookup:
                value = lookup[key]
                break
        bindings[str(reference)] = value
    return bindings


def evaluate(formula, columns):
    """Evaluate a validated formula over ``columns`` (label/id/name -> value).

    The expression must already be spreadsheet-valid; every free reference is resolved
    case-insensitively against ``columns``. Deterministic, no host access.
    """
    if formula is None or not str(formula).strip():
        return None
    text = str(formula).strip()
    if not text.startswith(_REQUIRED_PREFIX):
        text = _REQUIRED_PREFIX + text
    func = _compile(text)
    try:
        return func(**_bind_inputs(func, columns))
    except FormulaError:
        raise
    except Exception as exc:
        raise FormulaError(
            "The formula could not be evaluated against the row.",
            {"formula": text, "detail": str(exc)},
        ) from exc


def references(formula):
    """Return the free input references (cell/range tokens) a formula depends on.

    Validates the formula first, so callers can resolve each reference to a source column
    without ever re-parsing the expression themselves.
    """
    text = validate_formula(formula)
    if not text:
        return []
    return list(_compile(text).inputs.keys())
