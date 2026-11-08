# Backend Documentation

This directory documents the Django/DRF backend as it exists in the repository. The
documents are organized by concern and by Django app.

## Top-level documents

| Document | Purpose |
|---|---|
| [`architecture.md`](architecture.md) | System context, module layout, layering, cross-app contracts, persistence, and runtime services. |
| [`workflow.md`](workflow.md) | End-to-end request and business workflows across the backend. |

## App documents

| App | Documentation |
|---|---|
| `accounts` | [`accounts/architecture.md`](accounts/architecture.md), [`accounts/workflow.md`](accounts/workflow.md), [`accounts/api.md`](accounts/api.md), [`accounts/data-model.md`](accounts/data-model.md) |
| `companies` | [`companies/architecture.md`](companies/architecture.md), [`companies/workflow.md`](companies/workflow.md), [`companies/api.md`](companies/api.md), [`companies/data-model.md`](companies/data-model.md) |
| `catalog` | [`catalog/architecture.md`](catalog/architecture.md), [`catalog/workflow.md`](catalog/workflow.md), [`catalog/api.md`](catalog/api.md), [`catalog/data-model.md`](catalog/data-model.md) |
| `pipeline` | [`pipeline/architecture.md`](pipeline/architecture.md), [`pipeline/workflow.md`](pipeline/workflow.md), [`pipeline/data-model.md`](pipeline/data-model.md), [`pipeline/configuration.md`](pipeline/configuration.md) |
| `admin_console` | [`admin_console/architecture.md`](admin_console/architecture.md), [`admin_console/workflow.md`](admin_console/workflow.md), [`admin_console/api.md`](admin_console/api.md) |
| `recommendations` | [`recommendations/architecture.md`](recommendations/architecture.md), [`recommendations/workflow.md`](recommendations/workflow.md), [`recommendations/api.md`](recommendations/api.md), [`recommendations/data-model.md`](recommendations/data-model.md) |
| `core` | [`core/architecture.md`](core/architecture.md), [`core/workflow.md`](core/workflow.md) |
| `utils` | [`utils/architecture.md`](utils/architecture.md), [`utils/workflow.md`](utils/workflow.md) |
| `analytics` | [`analytics/architecture.md`](analytics/architecture.md), [`analytics/workflow.md`](analytics/workflow.md) |
| `normalizer` | [`normalizer/architecture.md`](normalizer/architecture.md), [`normalizer/workflow.md`](normalizer/workflow.md) |

## Source of truth

The code is authoritative. These documents describe the implementation under
`backend/src/`; when behavior changes, update the matching document in the same change.
