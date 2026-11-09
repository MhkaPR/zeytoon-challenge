"""Title-derived semantic components for the recommendation plan space.

Mirrors the ``pca.py`` prototype: character n-gram hashing followed by PCA. Components
are min-max scaled into ``[0, 1]`` so they can share the existing distance and Kalman
update with explicit plan attributes.
"""

from __future__ import annotations

import numpy as np
from sklearn.decomposition import PCA
from sklearn.feature_extraction.text import HashingVectorizer

from apps.recommendations import conf

NEUTRAL = 0.5


class SemanticEncoder:
    """Fits plan titles into a fixed number of semantic dimensions."""

    def __init__(
        self,
        dimensions=None,
        n_features=None,
        ngram_range=None,
        random_state=None,
    ):
        self.dimensions = int(
            conf.semantic_dimensions() if dimensions is None else dimensions
        )
        self.n_features = int(
            conf.semantic_n_features() if n_features is None else n_features
        )
        self.ngram_range = tuple(
            conf.semantic_ngram_range() if ngram_range is None else ngram_range
        )
        self.random_state = int(
            conf.semantic_random_state() if random_state is None else random_state
        )
        self.vectorizer = None
        self.pca = None
        self.component_min = None
        self.component_max = None
        self.fitted_components = 0

    @staticmethod
    def _clean(title):
        return " ".join(str(title or "").split())

    def fit(self, titles):
        cleaned = [self._clean(title) for title in titles]
        self.vectorizer = HashingVectorizer(
            analyzer="char_wb",
            ngram_range=self.ngram_range,
            n_features=self.n_features,
            alternate_sign=False,
            norm="l2",
        )
        matrix = self.vectorizer.transform(cleaned).toarray()
        if matrix.shape[0] < 2 or not matrix.any():
            self.pca = None
            self.component_min = None
            self.component_max = None
            self.fitted_components = 0
            return self
        n_components = min(self.dimensions, matrix.shape[0], matrix.shape[1])
        self.fitted_components = max(int(n_components), 0)
        if self.fitted_components == 0:
            self.pca = None
            self.component_min = None
            self.component_max = None
            return self

        self.pca = PCA(
            n_components=self.fitted_components,
            random_state=self.random_state,
            svd_solver="full",
        ).fit(matrix)
        scores = self.pca.transform(matrix)
        self.component_min = scores.min(axis=0)
        self.component_max = scores.max(axis=0)
        return self

    def transform(self, titles):
        titles = list(titles)
        values = np.full((len(titles), self.dimensions), NEUTRAL, dtype=float)
        masks = np.zeros((len(titles), self.dimensions), dtype=float)
        if self.pca is None or not titles:
            return values, masks

        cleaned = [self._clean(title) for title in titles]
        matrix = self.vectorizer.transform(cleaned).toarray()
        scores = self.pca.transform(matrix)
        span = self.component_max - self.component_min
        scaled = np.where(
            span > 0,
            (scores - self.component_min) / np.where(span > 0, span, 1.0),
            NEUTRAL,
        )
        scaled = np.clip(scaled, 0.0, 1.0)
        width = min(self.fitted_components, self.dimensions)
        values[:, :width] = scaled[:, :width]
        for index, title in enumerate(cleaned):
            if not title:
                values[index, :] = NEUTRAL
                continue
            masks[index, :] = 1.0
        return values, masks
