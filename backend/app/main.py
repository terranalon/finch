"""Main FastAPI application."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.rate_limiter import limiter

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Portfolio Tracker API",
    description="Investment portfolio tracking and analytics platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add rate limiter to app state and exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Portfolio Tracker API", "version": "0.1.0", "status": "running"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Import and include routers
from app.routers import (
    accounts,
    admin,
    assets,
    auth,
    broker_data,
    brokers,
    dashboard,
    holdings,
    market_data,
    mfa,
    portfolios,
    positions,
    prices,
    snapshots,
    transaction_views,
    transactions,
)

app.include_router(auth.router, prefix="/api")
app.include_router(mfa.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(accounts.router)
app.include_router(assets.router)
app.include_router(broker_data.router)
app.include_router(brokers.router)
app.include_router(dashboard.router)
app.include_router(holdings.router)
app.include_router(portfolios.router)
app.include_router(positions.router)
app.include_router(prices.router)
app.include_router(market_data.router)
app.include_router(snapshots.router)
app.include_router(transaction_views.router)  # Must come before transactions for path priority
app.include_router(transactions.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
