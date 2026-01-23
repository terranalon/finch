---
description: Start the development server
---

# Start Development Server

Start all services for the Portfolio Tracker application.

## Steps

1. **Pre-flight checks** - Verify prerequisites before starting:
   - Check if Docker daemon is running
   - Check if required ports are available (5432, 8000, 5173)
   - Verify `backend/.env` file exists (copy from `backend/.env.example` if missing)

2. **Start services** - Run `docker compose up -d` from project root

3. **Health verification** - Wait for services to be healthy:
   - PostgreSQL: Check container health status
   - Backend: Verify API responds at http://localhost:8000/health or http://localhost:8000/docs
   - Frontend: Verify dev server at http://localhost:5173

4. **Report status** - Display:
   - Container status (`docker compose ps`)
   - Service URLs:
     - Frontend: http://localhost:5173
     - Backend API: http://localhost:8000
     - API Docs: http://localhost:8000/docs
   - Any warnings or issues detected

## Troubleshooting

If services fail to start:
- **Port in use**: Run `lsof -i :<port>` to identify the process, then stop it or change the port in docker-compose.yml
- **Missing .env**: Copy `backend/.env.example` to `backend/.env` and fill in required values
- **Database issues**: Run `docker compose down -v` to reset volumes, then start again
- **Build errors**: Run `docker compose build --no-cache` to rebuild images

## Related Commands

- Stop services: `docker compose down`
- View logs: `docker compose logs -f [service]`
- Restart single service: `docker compose restart <service>`
- Rebuild and start: `docker compose up -d --build`
