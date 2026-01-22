# Portfolio Tracker

A full-stack investment portfolio tracking and analytics platform supporting multi-currency, multi-asset tracking with manual and automated data entry.

## Technology Stack

**Backend:**
- FastAPI (Python 3.11+)
- PostgreSQL 15
- SQLAlchemy 2.0
- Alembic (migrations)
- Polars (data processing)
- yfinance & CoinGecko (market data)
- uv (fast dependency manager)

**Frontend:**
- React 18 + Vite
- Tailwind CSS
- TanStack Query (React Query)
- Recharts
- Axios

**DevOps:**
- Docker + Docker Compose

## Getting Started

### Prerequisites

- Docker and Docker Compose installed
- Git (optional)

### Quick Start

1. **Clone the repository** (if using git):
   ```bash
   git clone <repo-url>
   cd portfolio_tracker
   ```

2. **Set up environment files**:
   ```bash
   # Backend
   cp backend/.env.example backend/.env

   # Frontend
   cp frontend/.env.example frontend/.env
   ```

3. **Start all services**:
   ```bash
   docker-compose up --build
   ```

4. **Access the application**:
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Development Workflow

#### Backend Development

```bash
# Enter backend container
docker-compose exec backend bash

# Add a new dependency
uv pip install <package-name>

# Add a dev dependency
uv pip install --group dev <package-name>

# Run database migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "description"

# Run tests
pytest

# Check logs
docker-compose logs backend -f
```

**Local Development (without Docker):**
```bash
cd backend

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r pyproject.toml

# Run the backend
uvicorn app.main:app --reload
```

#### Frontend Development

```bash
# Enter frontend container
docker-compose exec frontend sh

# Install new package
npm install <package-name>

# Check logs
docker-compose logs frontend -f
```

#### Database Access

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U portfolio_user -d portfolio_tracker

# View tables
\dt

# Backup database
docker-compose exec postgres pg_dump -U portfolio_user portfolio_tracker > backup.sql
```

## Project Structure

```
portfolio_tracker/
├── backend/
│   ├── app/
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic models
│   │   ├── routers/         # API endpoints
│   │   ├── services/        # Business logic
│   │   ├── tasks/           # Scheduled jobs
│   │   ├── config.py        # Configuration
│   │   ├── database.py      # DB setup
│   │   └── main.py          # FastAPI app
│   ├── alembic/             # Database migrations
│   ├── tests/               # Unit tests
│   └── pyproject.toml       # Dependencies (managed by uv)
│
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── hooks/           # Custom hooks
│   │   ├── pages/           # Page components
│   │   ├── services/        # API client
│   │   ├── utils/           # Utilities
│   │   └── contexts/        # React contexts
│   └── package.json
│
├── docker-compose.yml
├── IMPLEMENTATION_PLAN.md   # Detailed implementation plan
└── README.md
```

## Features (Planned)

- Multi-currency support (USD, ILS)
- Multi-asset tracking (stocks, crypto, real estate, bonds, etc.)
- FIFO cost basis tracking for tax reporting
- Automated CSV import from brokers (IBKR, Meitav)
- Real-time and manual price updates
- Portfolio analytics and breakdowns
- Historical performance tracking

## Development Status

Phase 1: Foundation Setup ✅ **COMPLETED**
- Docker Compose configuration
- Backend project structure (FastAPI)
- Frontend project structure (React + Vite + Tailwind)
- Alembic configuration
- Environment setup

Phase 2-13: See [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md)

## Useful Commands

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (⚠️ deletes database data)
docker-compose down -v

# Rebuild containers
docker-compose up --build

# View running containers
docker-compose ps

# Restart a specific service
docker-compose restart backend
docker-compose restart frontend
docker-compose restart postgres
```

## Environment Variables

### Backend (.env)
```env
DATABASE_URL=postgresql://portfolio_user:dev_password@postgres:5432/portfolio_tracker
EXCHANGE_RATE_API_KEY=your_key_here
COINGECKO_API_KEY=optional
LOG_LEVEL=INFO
DEBUG=True
```

### Frontend (.env)
```env
VITE_API_BASE_URL=http://localhost:8000/api
```

## Troubleshooting

**Port already in use:**
```bash
# Check what's using the port
lsof -i :5432  # PostgreSQL
lsof -i :8000  # Backend
lsof -i :5173  # Frontend

# Stop the process or change port in docker-compose.yml
```

**Database connection issues:**
```bash
# Check PostgreSQL is healthy
docker-compose ps

# View PostgreSQL logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres
```

**Frontend not loading:**
```bash
# Rebuild frontend container
docker-compose up --build frontend

# Check if node_modules are corrupted
docker-compose exec frontend rm -rf node_modules
docker-compose restart frontend
```

## Contributing

This is a single-user application currently in development. See [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) for the full roadmap.

## License

Private project - All rights reserved