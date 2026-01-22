FROM astrocrpublic.azurecr.io/runtime:3.1-9

# Add backend to Python path so DAGs can import from app.*
# Backend code will be mounted as a volume in docker-compose.override.yml
ENV PYTHONPATH="/opt/airflow/backend:${PYTHONPATH}"
