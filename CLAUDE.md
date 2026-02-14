# Portfolio Tracker

Full-stack portfolio tracking for multiple brokers (IBKR, Kraken, Meitav, Bit2C, Binance).
Python 3.11+ | FastAPI | React | PostgreSQL | Airflow 3 | Docker

## Critical Rules

- **Never commit directly to main** -- always use feature branches and PRs
- **Always launch Opus subagents** for complex reasoning tasks
- Run `ruff check --fix . && ruff format .` in `backend/` before committing
- Run `uv run ty check` in `backend/` before creating a PR -- type errors block CI

## Architecture

Routers -> Services -> Repositories -> Models (not all layers required for simple CRUD).

- **Routers** define endpoints and depend on auth/session via FastAPI `Depends()`
- **Services** orchestrate business logic across multiple repositories
- **Repositories** encapsulate SQLAlchemy queries with `find_*` (nullable) / `get_*` (raises) naming
- **Broker integration** uses a registry pattern: `BaseBrokerParser` ABC + `BrokerParserRegistry` factory

## Key Directories

```
backend/app/
  routers/          # FastAPI route handlers
  services/         # Business logic + broker integrations
    brokers/        # Per-broker parsers (ibkr/, kraken/, meitav/, bit2c/, binance/)
    repositories/   # Data access layer
  models/           # SQLAlchemy ORM (Mapped[] style)
  schemas/          # Pydantic request/response models
  dependencies/     # Auth, DB session, service account injection
  tasks/            # Background tasks
frontend/src/
  pages/            # Route-level page components
  components/       # Reusable React components
  contexts/         # React context providers
  hooks/            # Custom React hooks
  lib/              # API client utilities
```

## Commands

| Command | Purpose |
|---------|---------|
| `/serve` | Start the development server |
| `/plan` | Create implementation plan |
| `/tdd` | Test-driven development |
| `/code-review` | Review code quality |
| `/commit` | Git commit |
| `/verify` | Run checks |

## Docker Operations

The backend runs inside Docker containers. **Do not** run uvicorn directly on the host.

```bash
docker compose up -d                    # Start all services
docker compose restart backend          # Restart backend (picks up code changes)
docker compose logs backend --tail 50 -f  # View backend logs
docker compose up -d --build backend    # Rebuild after dependency changes
curl -s http://localhost:8000/health    # Check container health
```

If Docker daemon is not running: `open -a Docker` (macOS)

## Testing

```bash
# Backend (inside Docker)
docker compose exec backend pytest
docker compose exec backend pytest tests/unit/ -x
# Backend (local, for faster iteration)
DATABASE_HOST=localhost uv run --extra dev python -m pytest
# Frontend
cd frontend && npm test
```

Backend tests use transaction rollback for isolation. Auth tests use in-memory SQLite.
Test fixtures: `db` (session), `test_user`, `test_portfolio`, `auth_client`.

## Database

SQLAlchemy 2.0 with `Mapped[]` column declarations. Alembic for migrations:

```bash
docker compose exec backend alembic upgrade head              # Apply migrations
docker compose exec backend alembic revision --autogenerate -m "description"  # Generate
docker compose exec backend alembic downgrade -1              # Rollback one
```

## Code Quality (enforced by CI)

Pre-commit hooks and GitHub CI enforce these checks on all backend code:

| Check | Tool | Pre-commit | CI |
|-------|------|------------|-----|
| Formatting | `ruff format` | Auto-fix | Hard gate |
| Linting | `ruff check` | Auto-fix | Hard gate |
| Type checking | `ty check` | Hard gate | Hard gate |

Before creating a PR, verify locally:

```bash
cd backend
ruff check --fix . && ruff format .
uv run ty check
```

### CI workflows

Two GitHub Actions workflows run on every PR:

| Workflow | File | What it does |
|----------|------|-------------|
| **Backend Checks** | `backend-checks.yml` | Format, lint (changed files only), type check (full project) |
| **Backend Tests** | `test.yml` | Full pytest suite against Postgres |

Both workflows trigger on **all PRs** (no path filters). A lightweight `detect-changes` job
runs first and checks whether `backend/` files were modified. If not, the expensive job is
skipped -- skipped jobs count as passing for branch protection.

**What to expect when creating a PR:**
- Backend changes: all 4 jobs run (`detect-changes` x2, `lint-format-typecheck`, `backend-tests`)
- Non-backend changes: only `detect-changes` x2 run (~3s each), everything else skips green

### Type annotation conventions

- All function parameters and return types must be annotated
- Use `str | None` (not `Optional[str]`) for nullable types
- Add null narrowing (`if x is None: raise/return`) before accessing attributes on nullable values
- Use `# ty: ignore[rule-name]` only for confirmed false positives (document why in a comment)
- SQLAlchemy forward reference strings (`Mapped["Model"]`) are suppressed globally via `unresolved-reference = "ignore"` in ty config

### Pre-commit setup (one-time)

```bash
uv tool install pre-commit
pre-commit install
```

## Code Conventions

- **Imports**: stdlib -> third-party -> `app.*` (absolute, never relative)
- **Types**: Python 3.10+ syntax (`str | None`, `list[str]`, not `Optional`/`List`)
- **Naming**: `find_*` returns `T | None`; `get_*` raises if missing; `find_or_create_*` returns `tuple[T, bool]`
- **Circular imports**: use `TYPE_CHECKING` guard for type-only imports
- **Pydantic V2**: avoid `Field()` on `date` types (Python 3.14 compatibility issue)

## Git Worktrees

Use `.worktrees/` directory for isolated feature work. Cleanup order matters:

1. Merge the PR first (so the branch is "merged")
2. Remove the worktree: `git worktree remove .worktrees/<name>`
3. Delete the local branch: `git branch -d <branch-name>`
4. Pull main to get merged changes: `git pull origin main`

The `-d` flag (lowercase) only deletes if the branch is merged, preventing accidental data loss.

## Troubleshooting

### Airflow DAGs failing with 500 errors to backend

Check for port conflicts: `lsof -i :8000` (should show ONLY Docker, not Python processes).
Kill any non-Docker processes on port 8000. This happens when uvicorn was run directly on the host.
