"""
Hosting / server plan recommender
=================================
- Every plan is a point in a discretized space (values in [0, 1]).
- Every feature has an "exists" flag + a value; the value is masked when the
  plan does not have that feature (e.g. a CDN plan has no RAM).
- Every user is a continuous point in the same space with a per-dimension
  uncertainty, updated by a simple Kalman-style filter after each signal.
- Recommendation = nearest plans, measured only on the plan's active dimensions.

Requires: numpy, pandas, scikit-learn
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.preprocessing import KBinsDiscretizer

# signal -> (measurement noise r, sign).  Smaller r = stronger signal.
SIGNALS = {
    "vendor_click": (0.3, +1),   # clicked "go to vendor site"
    "compare":      (0.5, +1),   # added to compare / saved
    "details":      (1.0, +1),   # opened plan details
    "quick_close":  (1.0, -1),   # closed the plan page quickly
}


# --------------------------------------------------------------------------
# 1. Plan space: discretize + existence flags + one-hot + masks
# --------------------------------------------------------------------------
class PlanSpace:
    def __init__(self, numeric=("cpu", "ram", "storage", "traffic"),
                 categorical=("country", "os"), price_col="price",
                 n_bins=5, strategy="uniform"):
        self.numeric = list(numeric)
        self.categorical = list(categorical)
        self.price_col = price_col
        self.n_bins = n_bins
        self.strategy = strategy      # "uniform" or "quantile" (use with many plans)

    # -- helpers ----------------------------------------------------------
    def _new_binner(self):
        return KBinsDiscretizer(n_bins=self.n_bins, encode="ordinal",
                                strategy=self.strategy)

    @staticmethod
    def _scale(kb, values):
        codes = kb.transform(values.reshape(-1, 1)).ravel()
        return codes / max(kb.n_bins_[0] - 1, 1)          # levels -> [0, 1]

    # -- fit --------------------------------------------------------------
    def fit(self, plans: pd.DataFrame) -> "PlanSpace":
        self.kb = {}
        price = np.log1p(plans[self.price_col].to_numpy(float))   # log scale
        self.kb["price"] = self._new_binner().fit(price.reshape(-1, 1))
        for f in self.numeric:
            raw = plans[f].to_numpy(float)
            raw = raw[~np.isnan(raw)]
            self.kb[f] = self._new_binner().fit(raw.reshape(-1, 1)) if len(raw) else None
        self.categories = {c: sorted(plans[c].dropna().unique()) for c in self.categorical}
        self.names = self.transform(plans)[2]
        return self

    # -- transform --------------------------------------------------------
    def transform(self, plans: pd.DataFrame):
        """returns V (values), M (mask: 1 = dimension is meaningful), names"""
        n = len(plans)
        ones = np.ones(n)
        vals, masks, names = [], [], []

        def add(name, v, m):
            names.append(name); vals.append(np.asarray(v, float)); masks.append(np.asarray(m, float))

        price = np.log1p(plans[self.price_col].to_numpy(float))
        add("price", self._scale(self.kb["price"], price), ones)

        for f in self.numeric:
            raw = plans[f].to_numpy(float)
            has = ~np.isnan(raw)
            v = np.zeros(n)
            if has.any() and self.kb[f] is not None:
                v[has] = self._scale(self.kb[f], raw[has])
            add(f"has_{f}", has, ones)       # existence flag: always meaningful
            add(f, v, has)                   # value: only if the feature exists

        for c in self.categorical:
            has = plans[c].notna().to_numpy()
            add(f"has_{c}", has, ones)
            for cat in self.categories[c]:
                add(f"{c}={cat}", (plans[c] == cat).to_numpy(), has)

        return np.column_stack(vals), np.column_stack(masks), names

    # -- helpers for users ------------------------------------------------
    def prior(self, V, M):
        """starting point for a new user: masked column mean of all plans"""
        s = M.sum(0)
        return np.where(s > 0, (V * M).sum(0) / np.maximum(s, 1), 0.5)

    def explicit_vector(self, col, value):
        """vector for an explicit choice, e.g. filter country == 'DE'"""
        d = len(self.names)
        v, m = np.zeros(d), np.zeros(d)
        m[self.names.index(f"has_{col}")] = 1
        v[self.names.index(f"has_{col}")] = 1
        for cat in self.categories[col]:
            i = self.names.index(f"{col}={cat}")
            m[i] = 1
            v[i] = float(cat == value)
        return v, m


# --------------------------------------------------------------------------
# 2. User state: point x + per-dimension uncertainty s
# --------------------------------------------------------------------------
class UserState:
    def __init__(self, x0, q=0.1, s0=1.0, neg_factor=0.5):
        self.x = np.array(x0, float)
        self.s = np.full_like(self.x, s0)
        self.q, self.s0, self.neg = q, s0, neg_factor

    def update(self, v, m, r, sign=+1):
        a = np.asarray(m, bool)                       # only the active dimensions move
        self.s[a] += self.q                           # 1) predict: taste may drift
        K = self.s[a] / (self.s[a] + r)               # 2) Kalman gain
        factor = 1.0 if sign > 0 else -self.neg       # 3) move toward / away
        self.x[a] = np.clip(self.x[a] + factor * K * (v[a] - self.x[a]), 0, 1)
        self.s[a] = (1 - K) * self.s[a]               # 4) uncertainty shrinks

    def idle(self, days, q_gap=0.05):
        """user came back after some days: uncertainty grows again"""
        self.s = np.minimum(self.s + q_gap * days, self.s0)


# --------------------------------------------------------------------------
# 3. Recommender
# --------------------------------------------------------------------------
class Recommender:
    def __init__(self, plans: pd.DataFrame, **space_kwargs):
        self.plans = plans.reset_index(drop=True)
        self.space = PlanSpace(**space_kwargs).fit(self.plans)
        self.V, self.M, _ = self.space.transform(self.plans)
        self.index = {n: i for i, n in enumerate(self.plans["name"])}

    def new_user(self, **kw) -> UserState:
        return UserState(self.space.prior(self.V, self.M), **kw)

    def signal(self, user: UserState, plan_name: str, kind: str):
        r, sign = SIGNALS[kind]
        i = self.index[plan_name]
        user.update(self.V[i], self.M[i], r, sign)

    def explicit(self, user: UserState, col: str, value, r=0.5):
        """explicit filter selected by the user, treated as a strong signal"""
        v, m = self.space.explicit_vector(col, value)
        user.update(v, m, r, +1)

    def distances(self, x):
        diff2 = ((self.V - x) ** 2) * self.M
        return np.sqrt(diff2.sum(1) / self.M.sum(1))   # mean over ACTIVE dims only

    def recommend(self, user: UserState, k=3, filters=None, explore=0.0, seed=None):
        """
        filters: hard filters applied before ranking, e.g.
                 {"country": ["DE"], "ram": lambda s: s >= 4}
        explore: >0 -> Thompson-like sampling; uncertain users get more diverse results
        """
        x = user.x.copy()
        if explore > 0:
            rng = np.random.default_rng(seed)
            x = np.clip(x + explore * np.sqrt(user.s) * rng.standard_normal(len(x)), 0, 1)

        ok = np.ones(len(self.plans), bool)
        for col, cond in (filters or {}).items():
            ok &= (cond(self.plans[col]) if callable(cond)
                   else self.plans[col].isin(cond)).to_numpy()

        out = self.plans[["name"]].copy()
        out["distance"] = self.distances(x)
        return out[ok].sort_values("distance").head(k).reset_index(drop=True)


# --------------------------------------------------------------------------
# Demo: two plans of each type (VPS, CDN, domain)
# --------------------------------------------------------------------------
if __name__ == "__main__":
    nan = np.nan
    plans = pd.DataFrame([
        # name,        price, cpu, ram, storage, traffic, country, os
        ("VPS-A",       10,    1,   2,   40,    1000,    "DE",  "linux"),
        ("VPS-B",       40,    4,   16,  200,   5000,    "DE",  "windows"),
        ("CDN-A",        5,    nan, nan, nan,   500,     nan,   nan),
        ("CDN-B",       20,    nan, nan, nan,   5000,    nan,   nan),
        ("Domain-A",     2,    nan, nan, nan,   nan,     nan,   nan),
        ("Domain-B",     4,    nan, nan, nan,   nan,     nan,   nan),
    ], columns=["name", "price", "cpu", "ram", "storage", "traffic", "country", "os"])

    rec = Recommender(plans, n_bins=5)
    user = rec.new_user(q=0.1)

    print("Before any signal:")
    print(rec.recommend(user, k=6).to_string(index=False), "\n")

    rec.signal(user, "CDN-B", "details")
    rec.signal(user, "CDN-B", "compare")
    rec.signal(user, "CDN-A", "details")
    rec.signal(user, "VPS-B", "quick_close")

    print("After 4 signals:")
    print(rec.recommend(user, k=6).to_string(index=False), "\n")

    print("Mean uncertainty:", round(float(user.s.mean()), 3))
    print("\nWith hard filter ram >= 4 (CDN/domain have no RAM -> excluded):")
    print(rec.recommend(user, k=3, filters={"ram": lambda s: s >= 4}).to_string(index=False))

    print("\nWith exploration (uncertain dims get sampled):")
    print(rec.recommend(user, k=3, explore=0.3, seed=1).to_string(index=False))
