# Public Catalog and Link Submission Contract

## Public plan reads

All anonymous/end-user plan selectors, APIs, search indexing feeds, detail, and comparison
surfaces use `CatalogInterface` and return only records that are both publication-approved and
whose owning company is currently eligible through `CompaniesInterface`. A direct detail
lookup must apply the same rule as list/search pages. Cache keys or invalidation must include
eligibility transitions so a withdrawn plan cannot remain visible in stale public results.

## Publication lifecycle

- Extraction alone does not publish a public plan.
- A quality-approved plan can be public only when its company is eligible.
- Eligibility loss withdraws all company records while retaining internal plan/provenance data.
- Eligibility recovery can restore only quality-approved records still considered valid by
  existing catalog publication rules.

## Link discovery refresh

Operator-only request for a registered Site/company to refresh adaptive discovery. It requires
operator authorization and current company eligibility. The `admin_console` endpoint delegates
to `pipeline.interfaces`; the `pipeline` app reuses URL normalization, domain policy,
`url_hash` deduplication, and queueing. Existing links keep their current state; only new
candidates are added.

## Manual company URL submission

Authenticated company-owner request fields:

```json
{"url": "https://provider.example/plans/example"}
```

The server derives the company from an authorized company route, then delegates to
`pipeline.interfaces`, which validates the URL against
its registered domain and crawl policy, normalizes it, computes the same site-scoped hash,
records source `manual`, and adds/reuses the Link. Off-domain/malformed URLs return a field
error; duplicate normalized URLs return the existing link state. Ineligible companies cannot
submit work for immediate discovery/crawl processing (the response must communicate the
eligibility reason).

## Full phone display

Authorized account and company display responses include the complete stored phone number.
This does not change operational log redaction or disclose phones to anonymous public catalog
responses unless an existing product contract independently requires a company contact phone.
