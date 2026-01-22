# Portfolio Tracker - Architecture Documentation

> This document describes the overall system architecture, design patterns, and key architectural decisions.

## Overview

Portfolio Tracker is a full-stack investment dashboard built with FastAPI, React, and PostgreSQL. The system supports multi-currency, multi-asset tracking with both manual and automated data entry.

## Core Architectural Patterns

### Backend Architecture

**Pattern:** Clean Architecture with Service Layer
- **Models Layer**: SQLAlchemy ORM models representing database entities
- **Service Layer**: Business logic and data processing
- **Router Layer**: FastAPI endpoints handling HTTP requests/responses
- **Database Layer**: PostgreSQL with Alembic migrations

### Data Import Architecture

**Pattern:** Strategy Pattern for Multi-Broker Support
- Base parser interface for common CSV/API operations
- Broker-specific parsers (IBKR, Meitav, etc.)
- Unified import service orchestrating the import process

### Currency Conversion

**Pattern:** Repository Pattern with Caching
- Exchange rates stored in database for historical accuracy
- Service layer provides conversion methods
- Convert on-read, never store converted values

### FIFO Cost Basis Tracking

**Pattern:** Transaction Replay with Lot Tracking
- Holdings table maintains aggregate quantities and cost basis
- HoldingLots table tracks individual purchase lots
- Transactions replayed chronologically to reconstruct portfolio state

## Key Components

### IBKR Import System

**Current State:**
- TWS API: Limited to current session data, requires local IB Gateway
- Flex Query API: Complete historical data, cloud-ready HTTP API (preferred)

**Architecture Decision:** Migrate from TWS API to Flex Query API for cloud deployment compatibility.

### Historical Performance

**Current Approach:** Uses current holdings to calculate past values (inaccurate)

**Target Approach:** Transaction-based reconstruction
- Replay all transactions chronologically
- Reconstruct holdings for any historical date
- Calculate portfolio value using historical prices and exchange rates

## Documentation Roadmap

This document will be expanded with:
- Detailed service layer diagrams
- Database schema evolution
- API authentication patterns (future multi-tenant support)
- Caching strategies
- Performance optimization techniques

## Related Documentation

- [IBKR Import Plan](./IBKR_IMPORT_PLAN.md) - Detailed plan for fixing IBKR imports
- [API Documentation](./API_DOCUMENTATION.md) - REST API endpoint reference
- [Historical Performance](./HISTORICAL_PERFORMANCE.md) - Transaction reconstruction algorithm

---

**Last Updated:** 2026-01-09