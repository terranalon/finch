---
description: Apply project coding standards
---

# Portfolio Tracker Coding Standards

When writing or modifying code in this project, ALWAYS follow these standards:

## Type Hints (Python 3.11+)
- ✅ Use built-in types: `dict`, `list`, `tuple`, `set`
- ❌ Do NOT import from `typing` module: `Dict`, `List`, `Tuple`, `Set`
- ✅ Use `from typing import Optional, Any` for advanced types only
- Examples:
  ```python
  # Good
  def process_data(items: list[str]) -> dict[str, int]:
      pass

  # Bad
  from typing import Dict, List
  def process_data(items: List[str]) -> Dict[str, int]:
      pass
  ```

## Airflow 3 SDK Imports
- ✅ Use `airflow.sdk` for Airflow 3
- ❌ Do NOT use deprecated `airflow.decorators` (Airflow 2 style)
- Examples:
  ```python
  # Good (Airflow 3)
  from airflow.sdk import dag, task

  # Bad (Airflow 2 - deprecated)
  from airflow.decorators import dag, task
  ```

## Logging
- ✅ Use `logging` module with proper logger instances
- ❌ Do NOT use `print()` statements
- Create logger at module level: `logger = logging.getLogger(__name__)`
- Use appropriate log levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- Examples:
  ```python
  # Good
  import logging
  logger = logging.getLogger(__name__)

  logger.info("Processing started")
  logger.warning("Rate limit approaching")
  logger.error(f"Failed to fetch data: {error}")

  # Bad
  print("Processing started")
  print(f"ERROR: {error}")
  ```

## SQL Queries
- ✅ Store SQL queries in separate files or constants
- ❌ Do NOT embed long SQL strings inline in business logic
- For DAGs/scripts: Use a `queries.py` file with constants
- For models: Consider `.sql` files for complex queries
- Examples:
  ```python
  # queries.py
  GET_ACTIVE_HOLDINGS = """
      SELECT DISTINCT a.id, a.symbol, a.currency
      FROM assets a
      INNER JOIN holdings h ON h.asset_id = a.id
      WHERE h.is_active = true
  """

  # usage in code
  from .queries import GET_ACTIVE_HOLDINGS
  result = session.execute(text(GET_ACTIVE_HOLDINGS))
  ```

## Linting with Ruff
- ✅ Project uses `ruff` for linting and formatting
- ✅ Run `ruff check .` to check for issues
- ✅ Run `ruff check --fix .` to auto-fix issues
- ✅ Run `ruff format .` to format code
- Configuration files:
  - Backend: `backend/pyproject.toml`
  - Airflow: `airflow/pyproject.toml`
- Ruff enforces:
  - Python 3.11+ syntax (`UP` rules)
  - Airflow 3 best practices (`AIR` rules for airflow/)
  - Import sorting, naming conventions, etc.

## General Python Standards
- Use descriptive variable names
- Follow PEP 8 style guide
- Maximum line length: 100 characters
- Use f-strings for string formatting
- Use type hints for all function signatures