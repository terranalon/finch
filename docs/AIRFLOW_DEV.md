# Airflow Local Development (Astro CLI)

## Container Architecture
- **App containers** (`docker-compose.yml`): `portfolio_tracker_backend`, `portfolio_tracker_frontend`, `portfolio_tracker_db`
- **Airflow containers** (Astro-managed): `airflow_*-scheduler-1`, `airflow_*-api-server-1`, `airflow_*-triggerer-1`, `airflow_*-dag-processor-1`, `airflow_*-postgres-1`

These are separate - restarting app containers does NOT restart Airflow.

## Common Operations

```bash
# Restart Airflow containers (use this, not `astro dev restart` which needs TTY)
docker restart $(docker ps --format "{{.Names}}" | grep airflow)

# List DAGs
docker exec airflow_*-scheduler-1 airflow dags list

# Test a task directly (best way to run one-off tasks)
docker exec airflow_*-scheduler-1 airflow tasks test <dag_id> <task_id> <date>

# Trigger a DAG
docker exec airflow_*-scheduler-1 airflow dags trigger <dag_id>

# List pools
docker exec airflow_*-scheduler-1 airflow pools list
```

## Gotchas
- `astro dev parse` often fails due to Docker permission issues and mocked env vars - don't rely on it
- `astro dev restart` requires interactive TTY - use `docker restart` instead
- Airflow 3 CLI syntax differs from Airflow 2 (e.g., `airflow dags list-runs` changed)
- DAG files are mounted from `airflow/dags/` - changes are picked up automatically but container restart may be needed for new imports
- **Airflow 3 prohibits direct ORM access** from tasks - use CLI (`subprocess.run(["airflow", ...])`) or REST API instead of `create_session()` or importing models
- Stale import errors are cached in `import_error` table - clear with: `docker exec airflow_*-postgres-1 psql -U postgres -d postgres -c "DELETE FROM import_error WHERE filename LIKE '%<file>%';"`

## Astronomer Task Isolation (Important!)
Astronomer Runtime isolates tasks from Airflow's metadata database by setting `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN` to `airflow-db-not-allowed:///` during task execution.

**Inside tasks, you CANNOT:**
- Run `airflow` CLI commands (e.g., `airflow pools set`, `airflow pools list`)
- Access Airflow metadata tables directly
- Use `localhost:8080` to reach the Airflow API server

**For Airflow admin operations (pools, variables, connections):**
- Create them manually via Airflow UI (Admin -> Pools/Variables/Connections)
- Or run CLI commands from the host machine:
  ```bash
  docker exec <scheduler-container> airflow pools set db_write_pool 2 "Description"
  ```

## Database Connections
- App uses `postgres:5432` (Docker network)
- Airflow DAGs use `host.docker.internal:5432` (cross-network access)
- Shared DB module at `airflow/dags/shared_db.py` handles this translation
