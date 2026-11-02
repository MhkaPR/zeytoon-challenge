# Company Eligibility Interface Contract

`CompaniesInterface` is the sole interface for other modules to ask about company wallet and
eligibility. The precise Python signatures are implementation decisions, but behavior and
ownership are fixed here.

## Eligibility read

Input: company identifier or an authorized company reference.

Output:

```json
{
  "company_id": 42,
  "eligible": false,
  "reason": "insufficient_balance",
  "balance": 0,
  "required_balance": 0
}
```

The result is computed from the wallet ledger/projection, current Constance minimum, company
verification, and archival state. A persisted `charge_status` or `crawl_enabled` field must
not override it.

## Mutation operations

- Initiate a company top-up through the configured `payment` portal.
- Verify a provider transaction and credit the wallet once only after verified success.
- Add an authorized wallet debit or adjustment only through an auditable wallet entry and
  permission-checked service.
- Trigger/reconcile eligibility when a wallet entry is committed or the Constance minimum
  changes.

Every successful mutation returns the updated balance and eligibility. Callers do not write
wallet or eligibility tables directly.

## Authorization

- Company users can read/fund only companies they own.
- Operators/admins retain existing role and object authorization rules.
- Other bounded-context modules can use read-only eligibility for processing/public policy,
  not customer mutation endpoints.

## Consumer requirements

- `pipeline` checks eligibility before discovery scheduling, task execution, capture, crawling,
  and replay. It records a skip reason when false.
- `admin_console` owns operator routes and authorization, and calls `pipeline.interfaces` to
  request discovery/replay actions or inspect pipeline state. It does not import pipeline
  models, tasks, or implementation modules.
- `catalog` filters public catalog reads using current eligibility and withdraws affected
  records through its own write service after eligibility changes.
- Cache/search invalidation is driven by eligibility transition, with bounded staleness in
  line with the product's five-minute search freshness target.
