# API Documentation

> This document provides a comprehensive reference for all REST API endpoints in the Portfolio Tracker application.

## Base URL

```
Development: http://localhost:8000/api
Production: TBD
```

## Authentication

Currently: No authentication (single-user deployment)
Future: JWT-based authentication for multi-tenant SaaS

## Endpoints Overview

### Dashboard
- `GET /api/dashboard/summary` - Portfolio summary with breakdowns

### Positions
- `GET /api/positions` - Aggregated holdings by asset

### Holdings
- `GET /api/holdings` - Holdings by account
- `POST /api/holdings` - Create manual holding
- `PUT /api/holdings/{id}` - Update holding
- `DELETE /api/holdings/{id}` - Delete holding

### Transactions
- `GET /api/transactions` - List transactions
- `POST /api/transactions` - Create manual transaction
- `POST /api/transactions/import` - Import CSV transactions

### IBKR Import
- `POST /api/ibkr/import/{account_id}` - Import from IBKR TWS (deprecated)
- `POST /api/ibkr/import-flex/{account_id}` - Import from IBKR Flex Query (preferred)
- `POST /api/ibkr/accounts/{account_id}/import-auto` - Auto-import using stored credentials

### Accounts
- `GET /api/accounts` - List accounts
- `POST /api/accounts` - Create account
- `PUT /api/accounts/{id}` - Update account
- `DELETE /api/accounts/{id}` - Delete account

### Assets
- `GET /api/assets` - Search assets
- `POST /api/assets` - Create custom asset
- `POST /api/assets/prices/update` - Refresh asset prices

### Historical Snapshots
- `GET /api/snapshots` - List snapshots
- `POST /api/snapshots/backfill` - Backfill historical snapshots
- `GET /api/snapshots/accounts/{account_id}/validate` - Validate reconstruction accuracy

## Detailed Endpoint Reference

### GET /api/dashboard/summary

**Description:** Retrieve portfolio summary with breakdowns by asset class, sector, and account.

**Query Parameters:**
- `currency` (required): `USD` | `ILS`
- `entity_id` (optional): Filter by entity ID

**Response:**
```json
{
  "total_net_worth": 1500000.00,
  "total_cost_basis": 1200000.00,
  "total_unrealized_pnl": 300000.00,
  "total_unrealized_pnl_pct": 25.0,
  "daily_change": 15000.00,
  "daily_change_pct": 1.0,
  "currency": "USD",
  "breakdown_by_asset_class": [...],
  "breakdown_by_sector": [...],
  "breakdown_by_account": [...]
}
```

### GET /api/positions

**Description:** Get positions aggregated by asset across all accounts.

**Query Parameters:**
- `display_currency` (optional, default: `USD`): Currency for displaying values

**Response:**
```json
[
  {
    "asset_id": 1,
    "symbol": "AAPL",
    "name": "Apple Inc.",
    "asset_class": "Stock",
    "current_price": 180.50,
    "total_quantity": 150.0,
    "total_cost_basis": 22500.00,
    "total_market_value": 27075.00,
    "total_pnl": 4575.00,
    "total_pnl_pct": 20.33,
    "account_count": 2,
    "accounts": [...]
  }
]
```

### POST /api/ibkr/import-flex/{account_id}

**Description:** Import data from IBKR using Flex Query API.

**Path Parameters:**
- `account_id` (integer): Target account ID

**Request Body:**
```json
{
  "flex_token": "your_flex_token_here",
  "flex_query_id": "123456"
}
```

**Response:**
```json
{
  "status": "completed",
  "positions": {
    "created": 10,
    "updated": 5
  },
  "transactions": {
    "imported": 250
  },
  "dividends": {
    "imported": 15
  },
  "cash": {
    "imported": 3
  }
}
```

---

## Future Enhancements

- Authentication endpoints (login, register, refresh token)
- WebSocket endpoints for real-time price updates
- Bulk operations endpoints
- Export endpoints (CSV, PDF reports)

---

**Last Updated:** 2026-01-09