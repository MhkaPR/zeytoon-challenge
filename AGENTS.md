# Repository Guidelines

## Project Structure & Module Organization

This repository is a Django/DRF backend and Next.js frontend. Backend applications live under `backend/src/` (including `config/`, `accounts/`, `companies/`, and `admin_console/`); backend tests sit beside their apps, commonly in `<app>/tests/`. The frontend uses the App Router in `frontend/app/`, feature modules in `frontend/src/features/`, shared API/i18n utilities in `frontend/src/lib/`, and Vitest tests in `frontend/tests/`. Product specs and API contracts are in `specs/`; UI tokens and component guidance are in `DESIGN.md`.

## Build, Test, and Development Commands

- `uv sync` — install Python dependencies.
- `uv run pytest` — run the backend suite using the settings and test paths in `pyproject.toml`.
- `cd backend/src && python manage.py runserver` — start Django locally (run migrations first with `python manage.py migrate`).
- `cd frontend && yarn install && yarn dev` — install frontend dependencies and start Next.js.
- `cd frontend && yarn test` — run Vitest/Testing Library tests.
- `cd frontend && yarn lint` — run ESLint; `yarn build` — create a production build.
- `docker compose up --build` — start the full stack and supporting services.

## Coding Style & Naming Conventions

Follow the surrounding module's patterns. Python uses four-space indentation, `snake_case` modules/functions, and `PascalCase` classes; TypeScript/React uses `PascalCase` components and `camelCase` functions/variables. Keep frontend features grouped by domain and API access in `frontend/src/lib/api/`. Use the existing i18n catalogs for user-facing copy, preserve Persian-first RTL behavior, and follow `DESIGN.md` for UI tokens. ESLint is configured for the frontend; Black and flake8 are available for Python.

## Testing Guidelines

Backend tests use pytest and pytest-django; name test modules `test_*.py` and place them in the relevant app's `tests/` directory. Frontend tests use Vitest and Testing Library; use `*.test.tsx` under `frontend/tests/`. Run the relevant suite for changed behavior (`uv run pytest` or `cd frontend && yarn test`). No repository-wide coverage threshold is configured.

## Commit & Pull Request Guidelines

Recent commits use short, informal imperative summaries (for example, “add filter to backend”); keep subjects concise and action-oriented. A pull request should explain the user-visible or API change, link the relevant spec/issue when applicable, note migrations or configuration changes, and include test results. Add screenshots for visual frontend changes.

## Configuration & Security

Use environment variables for local secrets and service configuration; do not commit credentials, OTPs, tokens, or production data. Check `README.md` for local setup and proxy behavior, and keep backend/frontend configuration changes documented alongside the affected feature.
