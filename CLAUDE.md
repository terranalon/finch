# Portfolio Tracker

Full-stack portfolio tracking for multiple brokers (IBKR, Kraken, Meitav, Bit2C, Binance).
Python 3.11+ | FastAPI | React | PostgreSQL | Airflow 3 | Docker

## Critical Rules

- **Never commit directly to main** -- always use feature branches and PRs
- **Always launch Opus subagents** for complex reasoning tasks
- Run `ruff check --fix . && ruff format .` in `backend/` before committing

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
