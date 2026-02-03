# Portfolio Tracker

Full-stack portfolio tracking for multiple brokers (IBKR, Kraken, Meitav, Bit2C).
Python 3.11+ | FastAPI | React | PostgreSQL | Airflow 3 | Docker

## Critical Rules

- **Never commit directly to main** - Always use feature branches and PRs
- **Always launch Opus subagents** for complex reasoning tasks
- Run `ruff check --fix . && ruff format .` before committing

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
# Start all services (db + backend)
docker compose up -d

# Restart backend only (picks up code changes)
docker compose restart backend

# View backend logs
docker compose logs backend --tail 50 -f

# Rebuild backend after dependency changes
docker compose up -d --build backend

# Check container health
curl -s http://localhost:8000/health
```

If Docker daemon is not running, start Docker Desktop first:
```bash
open -a Docker  # macOS
```

## Git Worktrees

Use `.worktrees/` directory for isolated feature work. Cleanup order matters:

1. Merge the PR first (so the branch is "merged")
2. Remove the worktree: `git worktree remove .worktrees/<name>`
3. Delete the local branch: `git branch -d <branch-name>`
4. Pull main to get merged changes: `git pull origin main`

The `-d` flag (lowercase) only deletes if the branch is merged, preventing accidental data loss.

## Troubleshooting

### Airflow DAGs failing with 500 errors to backend

If Airflow tasks fail to authenticate with the backend (500 errors), check for port conflicts:

```bash
lsof -i :8000  # Should show ONLY Docker, not Python processes
```

If you see Python processes alongside Docker, kill them:
```bash
kill <PID>  # Kill any non-Docker processes on port 8000
```

This happens when uvicorn was run directly on the host and left zombie processes.
