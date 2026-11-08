# Pipeline — Problem, Idea, and Solution

This document explains the reasoning behind the automated site-maintenance
pipeline. It is a design narrative, not a workflow reference and not an API or
code guide. For the mechanical stages and data model, see
[`pipeline/architecture.md`](pipeline/architecture.md),
[`pipeline/workflow.md`](pipeline/workflow.md), and
[`pipeline/data-model.md`](pipeline/data-model.md).

## 1. The problem

The product depends on a continuously accurate catalog of hosting, CDN, and
virtual-server plans. Those plans live on provider websites that are:

- **heterogeneous** — every host structures its pricing pages differently, and
  many change their markup, navigation, and promotional layout without notice;
- **dynamic** — prices, discounts, resource limits, and plan names change over
  time, often behind JavaScript-rendered pages;
- **untrusted as a data source** — a page is a human-facing artifact, not a
  schema, so the same concept (for example "traffic") can appear as a column, a
  tooltip, a footnote, or a marketing sentence;
- **numerous** — the number of candidate links per provider is large, and only a
  small fraction are actual price tables.

Manual curation does not scale. A human can read one page correctly, but cannot
reliably watch dozens of providers, detect silent changes, and reconcile the
result into a clean catalog every day. A naive scraper does not solve this
either: it breaks on layout changes, it cannot tell a pricing table from a
comparison table, and it silently publishes wrong numbers when it guesses.

The real problem is therefore not "scrape a page". It is **maintaining a
trustworthy catalog from an unreliable, changing, semantically messy source**,
with enough auditability that an operator can understand and correct what the
system did.

## 2. The idea

Treat each provider link as an independent, staged production line rather than a
single scrape. Each stage has one job, produces an inspectable artifact, and can
fail without corrupting the rest of the catalog. The pipeline deliberately mixes
two kinds of intelligence:

- **Deterministic policy** for everything that can be decided by rules: which
  links are worth visiting, whether a table looks like a price table, how to
  normalize a price, when to retire a plan, and when to raise an alert.
- **Language-model inference** only where meaning must be recovered from
  unstructured text: labeling the columns of a table and mapping them onto a
  known plan schema.

The guiding principle is that the LLM is a *reader*, not an *authority*. It
extracts data; it does not decide which links to crawl, invent selectors, write
formulas, or publish directly. Every model output is validated against a schema
and passed through deterministic normalization before it can reach the catalog.

The second principle is **observability by construction**. Captures are stored as
artifacts, not discarded; classifications and extracted plans are persisted;
replays produce diffs; failures are counted and surfaced. The system is designed
so that "why did the catalog change?" has an answer.

## 3. The solution

### 3.1 A staged, per-link pipeline

Each link advances through a sequence of states: discovered, captured,
extracted, plans extracted, and published. Side states capture the honest
non-success outcomes — no price tables, waiting for LLM budget, flagged for
review, or dead-lettered after repeated failure. Because state is explicit, a
link can be retried, inspected, or replayed without re-running the entire
provider.

Isolating work per link is a deliberate choice. One broken provider page cannot
block another, and a bad extraction can be rolled back or corrected at the link
level instead of forcing a full re-crawl.

### 3.2 Discovery under deterministic policy

Link discovery uses an adaptive crawler to explore a provider site, but the
decision about what to keep is made by rules: only HTTP(S), same-host when a host
is given, a deny-list of file extensions and non-commercial path segments, and a
cap on total links. This keeps discovery broad enough to find pricing pages while
staying predictable and cheap to reason about. The crawler is a search tool; the
policy is the gatekeeper.

### 3.3 Capture as an artifact

The pipeline captures pages server-side in a headless browser for a fixed
duration, producing a trace that records the rendered page over time. The trace
body is stored in object storage; only metadata and a content hash live in the
database. This separation keeps the database lean while preserving the raw
evidence needed for debugging and replay.

A fixed-duration capture is a pragmatic tradeoff: it is simpler and more
predictable than event-driven capture, and it is sufficient for pages that render
their price tables shortly after load. It trades some efficiency for
reproducibility.

### 3.4 From tables to plans

Table extraction produces candidate tables. A regex-based classifier, driven by
admin-managed patterns, decides which tables look like price tables. This is
intentionally rule-based: price tables have recognizable shapes, and deterministic
classification is explainable and cheap. The LLM is then used in two focused
passes — first to label what each table column means, then to extract plans into a
validated schema (hosting, CDN, or virtual server).

Structured output is the key safety mechanism. The model must return data that
fits a known schema; incomplete or inconsistent plans are dropped rather than
guessed. Prices are normalized deterministically from the source row, so the
model never owns numeric interpretation. This keeps the failure mode "we skipped
a plan" instead of "we published a wrong price".

### 3.5 Publishing and retirement

Publishing is an upsert by natural key: a plan that already exists is updated, a
new one is created, and plans that disappear from a link are retired. The catalog
therefore reflects the current state of the source rather than an ever-growing
append log. Operator exclusions are respected at publish time, giving humans a
final veto without editing the extraction logic.

### 3.6 Replay, diffing, and alerting

Replay re-captures a link and compares the new trace against the previous one,
classifying changes as content or structural. If a change touches a price table,
the pipeline re-extracts and republishes; otherwise it records the change without
disturbing the catalog. Failure rates over a trailing window drive alerts, so
repeated breakage becomes visible instead of silent.

This turns change detection into a first-class concern. The system does not just
produce data; it produces evidence about how the source is behaving.

### 3.7 Cost and resilience controls

LLM usage is gated by a cost ledger with daily, monthly, and total budgets. When
budget is exhausted, work parks in an explicit waiting state instead of failing
or overspending. Retries use backoff, exhausted work is dead-lettered, and
idempotency keys make repeated model calls safe. These controls make an
expensive, unreliable external dependency behave like a managed resource.

## 4. Why this design

- **Auditability over cleverness.** Every stage leaves an artifact or a record,
  so operators can reconstruct what happened.
- **Determinism where possible, inference where necessary.** Rules are used for
  policy, classification, normalization, and publishing; the LLM is confined to
  semantic extraction.
- **Failure isolation.** Per-link state means one bad page degrades one link, not
  the catalog.
- **Honest states.** "No price tables" and "awaiting budget" are real outcomes,
  not errors disguised as success.
- **Reversibility.** Replay and diffing make change reviewable, and retirement
  keeps the catalog aligned with reality.

## 5. Tradeoffs and limitations

- **LLM cost and latency.** Semantic extraction is the expensive part. Budget
  gating and idempotency reduce waste, but extraction is still slower and costlier
  than pure parsing.
- **Statistical crawling.** Adaptive statistical discovery is cheaper and more
  predictable than embedding-based exploration, but it may miss unusually
  structured sites.
- **Fixed-duration capture.** Simple and reproducible, but not optimal for pages
  that need interaction or late rendering.
- **Regex classification.** Explainable and fast, but it depends on operators
  maintaining patterns as sites evolve.
- **Per-link isolation.** Improves robustness and debuggability at the cost of
  some throughput and cross-link coordination.
- **Schema coverage.** Plans that do not fit a known schema are skipped. This
  favors correctness over recall.

The pipeline is therefore optimized for trustworthy, explainable maintenance of a
catalog, not for maximum scraping throughput. That is the central design bet.
