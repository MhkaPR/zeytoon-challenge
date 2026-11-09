import numpy as np

from apps.recommendations.services.v1.semantic import NEUTRAL, SemanticEncoder

TITLES = [
    "سرور مجازی گیمینگ",
    "سرور اختصاصی گیمینگ",
    "سرور ماینکرفت",
    "هاستینگ وردپرس سریع",
    "هاستینگ وردپرس حرفه‌ای",
    "سرور ایمیل اختصاصی",
    "سرور ذخیره‌سازی بک‌آپ",
    "سرور GPU هوش مصنوعی",
]


def test_semantic_output_is_deterministic():
    first = SemanticEncoder(dimensions=10).fit(TITLES)
    second = SemanticEncoder(dimensions=10).fit(TITLES)
    values_a, masks_a = first.transform(TITLES)
    values_b, masks_b = second.transform(TITLES)
    assert np.array_equal(values_a, values_b)
    assert np.array_equal(masks_a, masks_b)


def test_semantic_dimensions_and_bounds():
    encoder = SemanticEncoder(dimensions=10).fit(TITLES)
    values, masks = encoder.transform(TITLES)
    assert values.shape == (len(TITLES), 10)
    assert masks.shape == (len(TITLES), 10)
    assert np.isfinite(values).all()
    assert values.min() >= 0.0
    assert values.max() <= 1.0


def test_empty_title_is_neutral_and_masked():
    encoder = SemanticEncoder(dimensions=10).fit(TITLES)
    values, masks = encoder.transform([""])
    assert np.allclose(values, NEUTRAL)
    assert np.allclose(masks, 0.0)


def test_small_corpus_pads_missing_dimensions():
    encoder = SemanticEncoder(dimensions=10).fit(TITLES[:2])
    values, masks = encoder.transform(TITLES[:2])
    assert values.shape == (2, 10)
    assert encoder.fitted_components == 2
    assert np.allclose(values[:, 2:], NEUTRAL)
    assert np.allclose(masks, 1.0)
