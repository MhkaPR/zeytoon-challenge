# Phase 0 Research: Company Wallet and Crawl Eligibility

This research uses repository evidence and the installed `payment==0.0.9` wheel. The
unanswered bug-list item 11 is explicitly outside the current design scope; the rest of the
technical unknowns are resolved.

## R0. Separate pipeline app from operator console

- **Decision**: Add a Django app named `pipeline`. Move ingestion lifecycle models (Site,
  Link, CaptureSession, Trace, extracted-table/classification/plan-processing, replay, and
  pipeline alert/budget state), tasks, services, discovery, capture/extraction, replay
  adapters, events, constants, LLM integration and budget logic, schema generation, table
  classification, artifact storage, worker recovery, and scheduled pipeline commands into
  `pipeline`. This explicitly includes the existing `llm.py`. Keep
  `admin_console` responsible for operator/admin endpoints, request validation, authorization,
  and presentation. Console use cases call `pipeline.interfaces`; they do not import pipeline
  models, task bodies, or implementation modules. Move pipeline tests to the pipeline app.
  Preserve existing database tables and rows through explicit migrations/state operations.
- **Current-folder mapping**: Move `admin_console/models.py`, `tasks.py`, `discovery.py`,
  `domtrack_client.py`, `artifacts.py`, `constants.py`, `events.py`, `llm.py`,
  `plan_schema.py`, `replay.py`, and `table_classifier.py` into `pipeline`. Split
  `services.py`: approval queue/verification orchestration remains in `admin_console`; all
  site/link/capture/extraction/classification/labeling/publishing/replay/budget operations
  move to `pipeline.services`. Move model registrations from `admin_console/admin.py` to
  `pipeline/admin.py`. Keep `admin_console/api.py`, `serializers.py`, `urls.py`, and app config
  as the operator surface, refactoring views to call `pipeline.interfaces` rather than
  importing pipeline models or implementation modules. Move pipeline data reads in
  `admin_console/interfaces.py` to `pipeline.interfaces`; retain only console-owned interface
  logic there if any. Split tests by ownership: verification/operator API tests remain in
  `admin_console`; pipeline behavior tests move to `pipeline`.
- **Rationale**: The repository currently groups pipeline internals and operator endpoints
  under `admin_console`, coupling domain processing to its management UI. A separate app
  establishes clear ownership while preserving the modular monolith and interface boundary.
- **Alternatives considered**: (a) Rename the whole `admin_console` app — rejected because
  operator routes and authorization remain a separate surface; (b) add wrappers while leaving
  implementations in place — rejected because it does not meet the requested ownership split;
  (c) create a separate deployable service — rejected by the modular-monolith constitution.
- **Migration note**: Django migrations encode app labels as well as table names. Preserve
  existing rows and stable table names during transition; explicitly handle model state,
  foreign keys, content types/permissions, generic references, task paths, and worker recovery.
  Do not let the split become an accidental drop/recreate of pipeline tables.

## R1. Payment package boundary

- **Decision**: Use the installed `payment` Django app for provider transactions only. Add
  `payment.apps.PaymentConfig` to `INSTALLED_APPS`, retain its migrations/admin, and use its
  `PayPortal` and `Transaction` models and transaction methods (`create`, `verify`,
  `get_redirect_url`, `refund`). Add a product-owned company wallet and append-only wallet
  ledger in `companies`. Associate an initiated provider transaction with the company wallet
  through the library transaction's generic linked-object fields where appropriate; keep an
  explicit durable provider transaction reference on the wallet-credit record for idempotency.
- **Rationale**: Inspection of the installed wheel shows `PayPortal` stores a configured
  backend and API key; `Transaction` stores provider transaction ID, amount, status, portal,
  optional user, and a generic linked object. `Transaction.create()` delegates to a backend;
  `verify()` asks the backend to confirm status. Zibal is registered as a backend. The package
  does not implement a company balance or wallet ledger, so those remain product domain data.
- **Alternatives considered**: (a) Treat library transactions as wallet balance — rejected,
  because the package has no wallet balance/projection model; (b) implement provider HTTP
  requests in `companies` — rejected, since the package already supports Zibal and provider
  lifecycle; (c) build another payment abstraction — rejected as unnecessary duplication.
- **Package-specific constraints to honor**: `Transaction.amount` has a 1000-unit step
  validator; `portal.api_key` is sensitive; `Transaction.verify()` may raise/provider-fail and
  must not imply wallet credit until successful verification and a successful state. Library
  state changes alone are not the wallet ledger. Review package behavior and callback routes
  during implementation before selecting the exact verification endpoint flow.

## R2. Wallet owner and eligibility

- **Decision**: Keep wallet, immutable movements, and derived eligibility under `companies`,
  replacing `charge_status`, `crawl_enabled`, and the existing ad-hoc credit ledger model and
  endpoints. Expose stable methods through `CompaniesInterface`; other apps do not query
  company or wallet tables directly. Store the required minimum balance in the existing
  database-backed django-constance configuration and surface it through Constance's Django
  admin integration.
- **Rationale**: The repository already centralizes company ownership, credit services, and
  module boundaries in `companies`; the constitution requires runtime thresholds in Constance.
  Persisted boolean flags can diverge from the authoritative balance and threshold, so
  eligibility should be derived from the balance and current configured minimum.
- **Alternatives considered**: (a) Put wallet models in `payment` — rejected because that
  library is provider-focused and external dependency ownership should not absorb product
  company data; (b) keep `charge_status`/`crawl_enabled` authoritative — rejected by the
  requirement and stale-state risk; (c) put threshold on each Company — rejected because the
  requirement states one administrator-configured runtime value.

## R3. Public plan visibility

- **Decision**: `catalog` remains the public plan owner and must enforce company eligibility
  for every public selector/API/page. Add a sanctioned `CompaniesInterface` eligibility
  operation and a `CatalogInterface` public read contract. Associate catalog records to the
  source company through a supported catalog-owned relation or resolve their site provenance
  via a declared interface; do not make catalog import `pipeline` or `admin_console` internals
  or query their tables.
  Withdrawals are performed through catalog services when eligibility transitions to false,
  with read-time eligibility filtering as the safety boundary.
- **Rationale**: Current `PublishedRecord` stores opaque integer site/link/trace provenance
  and is keyed by `(source, site, natural_key)`, while company owns the one-to-one Site
  association conceptually. Public selectors must not trust an `is_published` flag alone
  after balance changes. The modular monolith requires interface-only calls, and this change
  needs an explicit ownership-safe path from catalog records to company eligibility.
- **Alternatives considered**: (a) Have `catalog` query company/admin_console tables —
  rejected by constitution; (b) rely only on background unpublishing — rejected because a
  worker delay or stale cache could expose plans; (c) move published records into companies —
  rejected because catalog owns publication and search semantics.

## R4. Crawl, discovery, replay, and eligibility race handling

- **Decision**: Gate at both scheduling/queue creation and task execution. The `pipeline`
  app calls `CompaniesInterface` for eligibility before discovery and before each worker's
  external side effect. A task queued while eligible rechecks immediately before work and
  exits with a structured skip reason if the company is no longer eligible. Recheck on replay
  scheduler selection. Re-evaluate and invalidate affected catalog/search caches after each
  wallet ledger change or Constance threshold update.
- **Rationale**: Existing background execution uses Django Tasks and a database worker
  (currently `admin_console.tasks` and `db_worker`, which move into `pipeline`); queued work
  can outlive the condition that created it.
  Gate only at enqueue time leaves a race. A database transaction/lock around ledger update
  and eligibility event keeps the source-of-truth transition ordered; final task-side check
  limits stale queued work.
- **Alternatives considered**: (a) Only hide plans in UI — rejected because API/caches remain
  accessible; (b) only skip at queue-time — rejected because money may change before task
  execution; (c) use `crawl_enabled` as operator override — rejected by the feature requirement
  to remove that flag.

## R5. Link refresh and owner-submitted URLs

- **Decision**: Move and reuse existing `admin_console.discovery` and link normalization/deduplication
  paths. Make discovery refresh explicitly re-runnable rather than only on first discovery;
  expose an operator action for refresh and an owner-authorized company endpoint for submitted
  URLs. Persist manual provenance in existing Link source. Both flows require company
  eligibility, domain policy, URL normalization, and the `(site, url_hash)` uniqueness rule.
- **Rationale**: Existing `Link` has a `source` field and unique constraint on `(site,
  url_hash)`, while the current `run_site_pipeline_task` only discovers when
  `last_discovered_at is None`. This task moves into `pipeline` and gains an explicit refresh
  path. A common validator prevents manual
  and automatic URLs from having different safety/deduplication behavior.
- **Alternatives considered**: (a) create separate manual-link tables — rejected because
  links already retain source; (b) re-run extraction on every known URL — rejected because
  refresh should add newly discovered links without duplicating or resetting existing work.

## R6. Constance administration

- **Decision**: Add an integer/decimal runtime key for minimum company wallet balance under
  `CONSTANCE_CONFIG` and ensure the existing database backend and Constance admin are
  installed/enabled. Use the same monetary unit as the provider library transaction amount,
  documenting that unit in admin help text and API contracts. Changing the threshold triggers
  eligibility reconciliation for all companies and corresponding public plan/crawl state.
- **Rationale**: Existing settings already configure Constance's database backend and include
  runtime values, but the required company wallet balance key is not currently present. A
  threshold change can make many companies eligible/ineligible without a wallet transaction,
  so reconciliation is required.
- **Alternatives considered**: (a) environment-only setting — rejected because it requires a
  redeploy and does not satisfy the admin runtime configuration; (b) per-company threshold —
  rejected by the requested global setting.

## R7. Full phone display and operational privacy

- **Decision**: Return full phone values in authorized account/session, company panel, and
  backend/admin display payloads, and remove masking presentation helpers at those display
  boundaries. Keep the existing structured logging filter and log-specific masked values.
- **Rationale**: Current account and company selectors/API responses mask phone numbers; the
  user has explicitly requested full phone display. Existing logging protections are separate
  and remain in force under the constitution's sensitive-data requirements.
- **Alternatives considered**: (a) expose full numbers to logs — rejected because display
  authorization does not justify operational log exposure; (b) mask only backend — rejected
  because the requirement explicitly applies to frontend and backend displays.

## R8. Site crawl query field

- **Decision**: Remove `Site.crawl_query` and its schema migration/field uses; retain the
  existing globally administered `LINK_CRAWL_QUERY_FA` and `LINK_CRAWL_QUERY_EN` Constance
  values used by adaptive discovery.
- **Rationale**: The current settings already define shared crawl queries, while Site's
  `crawl_query` is an additional unused/ambiguous value, as confirmed by the specification.
- **Alternatives considered**: Keep per-site override — rejected absent a stated need for
  differentiated query terms.

## R9. Remaining clarification

- **Decision**: Plan only the numbered requirements supplied through item 10. Item 11 is
  blank and remains out of scope until the user provides it.
- **Rationale**: No behavior can be safely inferred from an empty list marker.
- **Alternatives considered**: Invent a likely requirement — rejected.
