# Payment and Company Wallet Contract

## Ownership

- The installed `payment` package owns configured provider portals and provider transaction
  creation, verification, redirect URL, and refund behavior.
- The product `companies` module owns company wallets, immutable wallet entries, wallet balance
  projection, top-up intent, and eligibility.
- A successful provider transaction is a prerequisite for wallet credit, but the provider
  transaction row is not the wallet balance.

## Top-up flow

1. An authenticated company owner requests a top-up amount for an owned company.
2. The API validates positive amount, currency/unit contract, ownership, and configured portal.
3. The backend creates a payment-library `Transaction` linked to that company's wallet,
   associates the authenticated user where the package flow requires it, and invokes the
   selected backend's `create(callback_url, ...)` operation.
4. On successful initiation, return the provider redirect target and an opaque transaction
   reference; never return portal API keys.
5. The callback/return path identifies the transaction, verifies it with the configured
   provider backend, and checks the package's final successful status.
6. In one database transaction, create one wallet credit keyed uniquely by provider
   transaction identity. Duplicate callbacks return the existing outcome and do not create a
   second credit.
7. Recompute eligibility and trigger public visibility/cache reconciliation.

Provider callbacks are untrusted input. Do not credit from query parameters or a browser
redirect alone. Provider verification and payment state must be authoritative.

## Stable result shape (application-owned API)

Wallet read response:

```json
{
  "company_id": 42,
  "balance": 0,
  "required_balance": 0,
  "eligible": false,
  "eligibility_reason": "insufficient_balance",
  "entries": []
}
```

Amounts above are placeholders; the API contract must document its chosen unit. The wallet
response is company-owner scoped. Operator views require current operator authorization.

Top-up creation response:

```json
{
  "transaction_id": "opaque-provider-transaction-reference",
  "redirect_url": "https://provider.example/checkout/...",
  "status": "pending"
}
```

Verification response:

```json
{
  "transaction_id": "opaque-provider-transaction-reference",
  "status": "successful",
  "wallet_credited": true,
  "balance": 0,
  "eligible": true
}
```

Do not expose raw gateway response payloads, credentials, card details beyond the package's
safe status fields, or full phone numbers in logs. Full phone is allowed in the authenticated
company/account display response as explicitly required.

## Constance setting

`COMPANY_WALLET_MINIMUM_BALANCE`: non-negative amount in the same unit used by the wallet and
payment transactions. It is database-backed and editable by an administrator in Django admin
through django-constance. A changed value triggers a reconciliation job and is used by every
eligibility check immediately.

## Error outcomes

- Unknown/not-owned company: return existing not-found authorization behavior.
- Invalid amount or unsupported portal: field-level client error.
- Provider initiation failure: no wallet entry; return payment initiation failure.
- Pending/failed/canceled provider result: no wallet credit and eligibility unchanged.
- Duplicate successful callback: idempotent success response with the existing wallet entry.
- Internal verification error: no wallet credit; auditable retryable outcome without secrets.
