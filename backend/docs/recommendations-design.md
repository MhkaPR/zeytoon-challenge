# Recommendations — Problem, Idea, and Solution

This document explains the reasoning behind the recommendation system. It is a
design narrative, not a workflow reference and not an API or code guide. For the
mechanical behavior and data model, see
[`recommendations/architecture.md`](recommendations/architecture.md),
[`recommendations/workflow.md`](recommendations/workflow.md), and
[`recommendations/data-model.md`](recommendations/data-model.md).

## 1. The problem

The catalog contains many plans that differ across price, CPU, RAM, disk,
traffic, country, operating system, and title. Visitors arrive with no explicit
preferences and no history, and most never rate or configure anything. The system
must still produce a useful, stable ordering of plans that feels relevant to each
viewer.

Several constraints make this harder than a standard recommender problem:

- **Cold start.** Most viewers are anonymous on their first visit, so there is
  nothing to personalize from.
- **No explicit feedback.** Interest must be inferred from behavior such as
  visiting a destination, opening plan details, or seeing a search result.
- **Heterogeneous, incomplete data.** Plans do not all declare the same
  attributes. Comparing plans on missing fields would unfairly penalize them.
- **Multiple interests.** A single viewer may care about several kinds of plans
  at once, so a single averaged preference vector can blur distinct intents.
- **Stable pagination.** Recommendations are computed before pagination, and the
  order must be deterministic so that pages do not shuffle between requests.
- **Privacy and lifecycle.** Anonymous interest must be usable, mergeable into an
  account on login, and disposable on logout.

The goal is not to predict ratings. It is to **rank plans by likely relevance
under uncertainty, without explicit feedback, while remaining interpretable and
cheap to operate**.

## 2. The idea

Represent both plans and viewers as points in a shared, normalized feature space.
Plans are fixed points derived from their attributes. A viewer is a set of
interest positions with per-dimension uncertainty, updated as signals arrive.
Recommendation is then a distance problem: rank plans by how close they are to
the viewer's interests, while ignoring dimensions the plan does not declare.

Three ideas make this work:

- **Masked comparison.** Each plan carries a mask indicating which dimensions it
  actually declares. Distance is computed only on shared dimensions, so a plan is
  never punished for a missing attribute.
- **Uncertainty-aware updates.** A viewer's interest is not a fixed vector but a
  position with confidence. New signals move the position more when confidence is
  low and less when it is high, which is a Kalman-style update.
- **Multiple interests.** Rather than collapsing everything into one vector, the
  system keeps a small set of interest clusters. A signal updates the nearest
  cluster or starts a new one, so a viewer can hold several distinct intents.

The design favors interpretability and low operational cost over deep models.
Every ranking decision can be explained in terms of feature distance, and the
system runs with ordinary Python numeric tooling rather than a training pipeline.

## 3. The solution

### 3.1 A shared, versioned plan space

Each published plan is mapped into a normalized space. Numeric attributes such as
price, CPU, RAM, disk, and traffic are converted into quantile bins; categorical
attributes such as country and operating system become one-hot dimensions;
presence flags capture which resources and categories a plan declares; and plan
titles contribute semantic components derived from hashed character n-grams
reduced by PCA.

The fitted space is cached and versioned by a hash of the plan data and semantic
configuration. When the catalog changes, a new version is built; a failed refresh
leaves the previous version intact. This keeps ranking consistent and avoids
recomputing the space on every request.

### 3.2 Viewer interest as uncertain positions

A viewer's state is a position plus per-dimension uncertainty. When a signal
arrives, uncertainty grows slightly to model drift, then the position moves toward
the observed plan in proportion to how uncertain the viewer is. Positive signals
pull interest toward a plan; negative signals push away with a configurable
factor.

This produces a natural cold-start-to-personalization curve: early signals move
interest significantly, later signals refine it gently. It also means the system
can express "I am not sure yet" rather than pretending to know a new visitor's
preferences.

### 3.3 Multiple interest clusters

Instead of one averaged vector, the system keeps up to a small maximum number of
interest positions. A new signal updates the nearest cluster when it is close
enough, and otherwise creates a new cluster. This preserves distinct intents —
for example, a cheap shared host and a larger virtual server — instead of blending
them into a meaningless midpoint.

### 3.4 Cold-start prior

When a viewer has no usable profile, interest is initialized to the masked mean of
all plans in the space. This is a neutral, data-derived prior: the first page is
not random, and it reflects the center of the catalog rather than an arbitrary
default. Because the prior is deterministic, anonymous first visits are stable.

### 3.5 Masked distance ranking

Plans are ranked by a masked distance to the viewer's interests. Only dimensions
both sides declare contribute to the distance. Ties are broken deterministically
by distance, then recency, then identifier, which keeps pagination stable.

Ranking happens before pagination in the catalog, so the ordering is applied to
the full candidate set rather than to a single page. This is essential for
consistent results across pages.

### 3.6 Signals and their lifecycle

Interest is recorded as append-only signals of a few kinds — destination visits,
details views, and search impressions — with a per-minute cap to prevent
accidental flooding. Signals are attributed to either an anonymous visitor or an
account.

On login, an anonymous profile is merged into the account profile and the visitor
state is tombstoned so it cannot be reused. On logout, the visitor state is
cleared. This keeps personalization useful across sessions without retaining
anonymous state longer than necessary.

### 3.7 Refresh and maintenance

The plan space and interest clusters are refreshed by scheduled commands. This
separates expensive fitting work from request handling, keeps ranking fast, and
allows the space to evolve as the catalog changes without recomputing on every
request.

## 4. Why this design

- **Interpretable.** Relevance is a distance in a known feature space, not an
  opaque model score.
- **Cold-start friendly.** A deterministic prior gives every new visitor a
  sensible starting page.
- **Fair to incomplete data.** Masking prevents missing attributes from acting as
  hidden penalties.
- **Multi-interest aware.** Clusters preserve distinct intents better than a
  single averaged vector.
- **Stable and cheap.** Versioned caching and deterministic tie-breaking keep
  ranking consistent and operationally simple.
- **Privacy-conscious.** Anonymous state is explicit, mergeable, and disposable.

## 5. Tradeoffs and limitations

- **Lightweight over deep learning.** The system cannot learn complex nonlinear
  preferences the way a trained model might; it trades that capacity for
  explainability and low operational cost.
- **Behavioral inference.** Signals are noisy proxies for intent, and the quality
  of personalization depends on how meaningful those signals are.
- **Cluster limits.** A small maximum number of clusters keeps the model simple
  but may under-represent viewers with many diverse interests.
- **Masked distance.** Masking avoids unfair penalties but can make plans with
  sparse attributes easier to match, which may favor them unintentionally.
- **Prior bias.** The masked mean reflects the catalog's center; if the catalog is
  skewed, the cold-start ordering inherits that skew.
- **Refresh lag.** Cached, scheduled fitting means recommendations reflect the
  catalog at the last refresh rather than instantly.

The recommendation system is therefore optimized for explainable, stable,
privacy-conscious personalization under heavy cold start, not for maximum
predictive power. That is the central design bet.
