# Quickstart Validation: Company Wallet and Crawl Eligibility

This guide describes the validation scenarios for implementation. Commands are run from the
repository root. The current plan phase does not execute tests.

## Prerequisites

- Install project dependencies, including the locked `payment==0.0.9` wheel.
- Configure Django database, Redis, and test settings according to the project README.
- Add a test `PayPortal` using the payment package's mock backend; never use a live provider in
  automated validation.
- Apply Django migrations, including the `payment` app and new product wallet/catalog changes.

## Backend scenarios

1. Create a company and verify one product wallet exists; ensure no charge/crawl booleans are
   required for the wallet state.
2. Create a pending top-up using the mock payment backend. Confirm no wallet balance change
   before successful provider verification.
3. Verify one transaction as successful twice. Confirm one immutable wallet credit, identical
   returned balance, and no duplicate ledger row.
4. Configure the Constance minimum below, equal to, then above the company balance. Confirm
   eligibility boundary behavior and the reason response.
5. Publish plans for an eligible company and request main/search/detail/comparison contracts.
   Reduce eligibility; confirm all public reads exclude the plans while internal provenance
   remains.
6. Queue discovery/capture/replay while eligible, make the company ineligible before the
   worker executes, then run the task. Confirm it skips before any network/capture side effect
   and records the reason.
7. Restore eligibility and confirm new work may be scheduled and only still-valid approved
   plans can return to public surfaces.
8. Refresh adaptive discovery twice after introducing a new same-domain URL through the
   operator endpoint. Confirm `admin_console` delegates through `pipeline.interfaces`, new
   link insertion occurs in `pipeline`, and there are no duplicate normalized `(site,
   url_hash)` rows.
9. Submit valid same-domain, duplicate, malformed, and off-domain URLs as company owner and as
   a non-owner. Confirm validation, provenance, reuse, and authorization behavior.
10. Inspect database migration/backfill behavior for existing credit movements, company flags,
    site crawl queries, published plans, and the app ownership transfer. Confirm existing
    pipeline rows survive and pipeline models are registered under the `pipeline` app.
11. Import-boundary check: operator endpoints/services call `pipeline.interfaces`; `admin_console`
    does not import `pipeline.models`, task modules, or pipeline implementation modules.

## Frontend scenarios

- Company panel shows complete phone, wallet balance, minimum, eligibility reason, and top-up
  state. User profile/session UI displays the complete signed-in phone.
- Wallet top-up sends the owner to the provider redirect and handles pending, success, and
  failure outcomes without claiming a credit prematurely.
- Company owner can submit remaining plan URLs and sees validation or eligibility feedback.
- Operator can trigger discovery refresh and see ineligible skip reasons.
- Home/search/details/comparison show eligible published plans and remove plans after
  ineligibility/cache refresh.

## Relevant contracts

- [Payment and wallet](contracts/payment-wallet.md)
- [Company eligibility interface](contracts/companies-eligibility.md)
- [Public catalog and link submissions](contracts/public-catalog.md)
- [Data model](data-model.md)

## Final validation commands

Implementation should run focused pytest suites for `companies`, `catalog`, `pipeline`, and
`admin_console`, then the frontend's applicable test/build commands and Django migration/system
checks. Include migration-state and module-boundary validation. The exact files and commands
should be adjusted to the delivered implementation and reported with results in the
implementation completion summary.
