"""Excel-compatibility unit tests for the formula engine (US6, FR-028, research R10)."""

import pytest

from admin_console import formulas


@pytest.mark.parametrize(
    "expression",
    [
        "=SUM(A2:A9)",
        "=IF(B2>0,B2,0)",
        '=ROUND(VALUE(SUBSTITUTE(C2,",","")),0)',
        "=A2&B2",
        "=Price*2",
        "=(A2+B2)*2",
    ],
)
def test_valid_spreadsheet_formulas_are_accepted(expression):
    assert formulas.validate_formula(expression) == expression


@pytest.mark.parametrize(
    "expression, columns, expected",
    [
        ("=SUM(A2:A9)", {"A2:A9": [1, 2, 3, 4]}, 10.0),
        ("=IF(B2>0,B2,0)", {"B2": 5}, 5),
        ("=IF(B2>0,B2,0)", {"B2": -3}, 0),
        ('=ROUND(VALUE(SUBSTITUTE(C2,",","")),0)', {"C2": "1,234.6"}, 1235.0),
        ("=Price*2", {"PRICE": 4}, 8.0),
        ("=Price*2", {"price": 4}, 8.0),
        ("=A2&B2", {"A2": "ab", "B2": "cd"}, "abcd"),
    ],
)
def test_evaluation_is_deterministic(expression, columns, expected):
    assert formulas.evaluate(expression, columns) == expected
    # Deterministic across repeated calls.
    assert formulas.evaluate(expression, columns) == expected


@pytest.mark.parametrize(
    "expression",
    [
        "=SUM(",  # unbalanced parentheses
        "garbage",  # not a formula
        "=1+",  # trailing operator
        "",  # empty is valid, handled separately below
    ],
)
def test_syntactically_invalid_formulas_are_rejected(expression):
    if expression == "":
        assert formulas.validate_formula(expression) == ""
        return
    with pytest.raises(formulas.FormulaError):
        formulas.validate_formula(expression)


@pytest.mark.parametrize(
    "expression",
    [
        "=NOPE(1)",  # unknown function
        '=EVAL("1")',  # eval-style
        '=__import__("os")',  # host access attempt
        "=1+NOPE(A2)",  # unknown function nested
        "=LAMBDA(x,x)(1)",  # non-spreadsheet construct
    ],
)
def test_non_spreadsheet_and_eval_style_inputs_are_rejected(expression):
    with pytest.raises(formulas.FormulaError):
        formulas.validate_formula(expression)


def test_empty_formula_is_allowed():
    assert formulas.validate_formula("") == ""
    assert formulas.validate_formula(None) == ""
    assert formulas.evaluate("", {"A2": 1}) is None
    assert formulas.evaluate(None, {"A2": 1}) is None
