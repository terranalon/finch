# Portfolio Tracker

Full-stack portfolio tracking for multiple brokers (IBKR, Kraken, Meitav, Bit2C).
Python 3.11+ | FastAPI | React | PostgreSQL | Airflow 3 | Docker

## Critical Rules

- **Always launch Opus subagents** for complex reasoning tasks
- Run `ruff check --fix . && ruff format .` before committing

## Reference Docs

- [Broker Integration Guidelines](docs/BROKER_INTEGRATION.md) - Dual-entry accounting, fee handling, decimal precision
- [Airflow Development](docs/AIRFLOW_DEV.md) - Container architecture, common operations, gotchas

## Commands

| Command | Purpose |
|---------|---------|
| `/serve` | Start the development server |
| `/plan` | Create implementation plan |
| `/tdd` | Test-driven development |
| `/code-review` | Review code quality |
| `/commit` | Git commit |
| `/verify` | Run checks |
