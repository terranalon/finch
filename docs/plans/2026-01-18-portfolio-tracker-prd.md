# Finch - Product Requirements Document

**Date:** 2026-01-18
**Status:** Draft
**Author:** Product & Engineering

---

## 0. Product Identity

**Name:** Finch

**Name Meaning:**
- **Bird** - A view from above over all your assets
- **Fin** - Short for Finance
- **Finch** - Short for "Finance Check"

**Tagline:** "The portfolio tracker that actually tracks your portfolio"

---

## 1. Vision & Problem Statement

### Vision

Become the go-to portfolio tracker for Israeli investors who invest both locally and internationally.

### Problem Statement

Israeli retail investors increasingly diversify across multiple platforms - IBKR for US stocks, local brokers (Meitav, IBI, Psagot) for Israeli securities and pensions, banks for convenience, and crypto exchanges (Binance, Bit2C) for digital assets.

This creates a fragmented experience:
- No single view of total net worth
- Impossible to see overall asset allocation across all accounts
- Can't answer "am I beating the market?" across the full portfolio
- Manual spreadsheet tracking is error-prone and time-consuming

### Why Existing Solutions Fail

| Solution | Problem |
|----------|---------|
| Global apps (Kubera, Delta, Empower) | Don't support Israeli brokers or TASE securities |
| Israeli wealth apps | Go broad (bank accounts, expenses) but shallow - only track current balances, not transaction history or performance |
| Broker apps | Only show their own slice |
| Spreadsheets | Manual, error-prone, time-consuming |

### Our Solution

A portfolio tracker that goes narrow (investments only) but deep (full transaction history, performance metrics, automated imports). We support both Israeli and international brokers, handle multi-currency (ILS/USD), and give users a true consolidated view with historical tracking.

### Positioning

> "The portfolio tracker that actually tracks your portfolio"

Not just balances, but every transaction, dividend, and price movement across all your accounts.

---

## 2. Target User

### Primary Persona: The Israeli Global Investor

**Demographics:**
- Age 25-55, tech-savvy, comfortable with English and Hebrew
- Based in Israel, invests in both local and US/global markets
- Has accounts at 2-5+ financial institutions
- Portfolio size: ₪100K - ₪5M (broad range)

**Behavior:**
- Opened IBKR account to access US markets (lower fees, broader selection)
- Has pension/provident funds at Israeli brokers (Meitav, IBI, etc.)
- May hold stocks directly at Israeli bank brokerage
- Likely owns some crypto (Binance, Bit2C)
- Currently tracks everything in spreadsheets or doesn't track at all

**Pain Points:**
- "I have no idea what my actual net worth is without manually checking 4 different apps"
- "I don't know my real returns - each broker shows different numbers, different currencies"
- "Updating my spreadsheet takes an hour every month and I still make mistakes"
- "My Israeli broker shows returns in ILS, IBKR in USD - I can't compare"

**Goals:**
- Single dashboard showing everything in their preferred currency
- Know if they're beating the market (S&P 500, TA-125)
- Spend less time on manual tracking
- Understand asset allocation across all accounts

### Secondary Persona: The Crypto-Forward Investor

Same as above, but with larger crypto allocation across multiple exchanges. Needs unified view of traditional + crypto holdings.

### Note on Single-Broker Users

Even users with a single brokerage account may prefer our app because:
- Better UX than clunky broker apps
- Superior performance visualization
- Clean portfolio analytics the brokers don't provide

---

## 3. MVP Feature Scope

### 3.1 Authentication & Multi-tenancy

| Feature | Description |
|---------|-------------|
| Email/password registration | Standard signup flow with email verification |
| Google OAuth | One-click signup/login via Google |
| Password reset | Email-based password reset flow |
| User isolation | Each user sees only their data (row-level isolation) |
| Session management | JWT tokens (access + refresh), DB-stored for revocation |

### 3.2 Data Hierarchy

```
User (1) → Portfolios (many) → Accounts (many) → Holdings/Transactions
```

- **User:** Authentication identity
- **Portfolio:** Grouping of accounts (e.g., "Personal", "Company", "Kids' Education")
- **Account:** Brokerage account at a specific institution

Note: Entity concept removed for MVP simplicity. Can be added later as optional metadata.

### 3.3 Broker Integrations

#### API-Based (Automated Import)

| Broker | API Type | Data Available | Sync Frequency |
|--------|----------|----------------|----------------|
| IBKR | Flex Query | Positions, trades, dividends, cash | Hourly |
| Binance | REST API | Balances, trades, deposits/withdrawals | Hourly |
| Kraken | REST API | Balances, trades, ledger | Hourly |
| KuCoin | REST API | Balances, trades | Hourly |
| Bit2C | REST API | Balances, trades | Hourly |

#### File-Based (Manual Upload)

| Broker | Priority | Export Format | Notes |
|--------|----------|---------------|-------|
| Meitav | 1 | Excel | 89K accounts - largest Israeli broker |
| IBI | 2 | Excel/CSV | 52K accounts - fastest growing |
| Israeli Banks | 3 | Varies | 900K accounts across all banks |
| Psagot | 4 | Excel/CSV | Active, known brand |
| Altshuler Shaham | 5 | Excel/CSV | Declining but still has users |
| Excellence (Phoenix) | 6 | Excel/CSV | Lower priority |
| Bits of Gold | 7 | CSV | Israeli crypto |

#### Implementation Per Broker

Each broker integration includes:
1. **Parser module** - Converts broker-specific format to internal schema
2. **Validation rules** - Detects wrong file type, missing columns, date range issues
3. **Tutorial content** - Screenshots, step-by-step instructions, video link
4. **Deduplication logic** - Prevents re-importing same transactions
5. **Parser versioning** - Support multiple parser versions (e.g., `MeitavParserV1`, `MeitavParserV2`) when brokers change formats
6. **Encoding support** - Handle UTF-8, Windows-1255, and other Israeli encodings

#### Transaction Types Supported

- Buy, Sell
- Dividend
- Forex Conversion
- Cash Deposit, Cash Withdrawal
- **Stock Split** - Manual entry for corporate actions (prevents 90% crash when Yahoo updates split-adjusted prices)

#### File Upload Error Handling

When parsing fails:
- Show specific, helpful error message
- **"Send to support" button** - One-click file submission for debugging (with user consent)
- Suggest common fixes (wrong file type, missing date range, encoding issues)

#### Scope Note

**MVP targets self-directed trading accounts only.** Pension/Gemel funds have poor export options (PDF-heavy, no transaction history) and are deferred to post-MVP.

### 3.4 Portfolio Views & Analytics

| View | Description |
|------|-------------|
| Dashboard | Total net worth, asset allocation, top holdings, performance chart |
| Holdings | Detailed holdings per account with P&L |
| Positions | Aggregated positions across all accounts |
| Transactions | Full transaction history with filtering |
| Account Detail | Deep dive into specific account |

#### Dashboard Analytics

- Total net worth in multiple currencies (ILS/USD toggle)
- Asset allocation breakdown (stocks, ETFs, crypto, bonds)
- Top 10 holdings by market value
- Day/week/month/year change with P&L percentage
- Portfolio value over time (chart)
- Benchmark comparison (S&P 500, TA-125)

### 3.5 Multi-Currency Support

- Display currency switching (USD ↔ ILS)
- Proper FX handling with historical exchange rates
- Native currency stored in database, converted on read
- Support for: USD, ILS, EUR, GBP, CAD

### 3.6 Localization

| Language | Status |
|----------|--------|
| English | Primary, full support |
| Hebrew | Full support, RTL layout |

Frontend needs i18n infrastructure:
- String extraction to translation files
- Language switcher in UI
- RTL CSS support for Hebrew

### 3.7 Performance Analytics (Already Implemented)

The following performance features already exist and should be preserved:

- **TWR Calculation** - Modified Dietz method implemented in frontend (`Overview.jsx`)
- **Value vs Performance toggle** - Users can switch between raw portfolio value and TWR-adjusted returns
- **Cash flow handling** - Deposits/withdrawals are excluded from performance calculations
- **Benchmark comparison** - S&P 500 overlay on performance chart
- **Time range selection** - 1W, 1M, 3M, 1Y, ALL views

The shareable performance chart (MVP feature) will leverage this existing TWR implementation.

### 3.8 Social Features

- **Shareable performance chart** - Users can generate an image showing portfolio performance as percentages (no absolute values)
- Privacy-conscious: "I'm up 12% YTD" without revealing portfolio size
- Can include benchmark comparison ("Beat S&P by 3%")
- Uses existing Modified Dietz TWR calculation

---

## 4. User Experience Priorities

### The Onboarding Challenge

The biggest drop-off risk is between "user signs up" and "user sees their portfolio."

- **API brokers:** Smooth - enter credentials, we fetch data
- **File brokers:** Friction - user must export file manually and upload

Since Israeli brokers don't offer APIs, the file upload experience is critical.

### Guided Import Flows

For each file-based broker, we provide:

1. **Step-by-step wizard** with numbered instructions
2. **Screenshots** showing exactly where to click (updated if broker UI changes)
3. **Video walkthrough** option
4. **Supported file formats** clearly stated
5. **Validation on upload** with helpful error messages
   - Example: "This looks like a Meitav positions file, but we need the transactions file"

### Empty State

A new user with zero accounts sees:
- Clear call-to-action: "Add your first account"
- Supported brokers list (builds confidence)
- Quick-start option: "Have IBKR? Connect in 30 seconds"
- Security/privacy reassurance
- **Demo Portfolio** - One-click button to populate dashboard with sample data, letting users see the value before doing the hard work of importing

### Returning User Experience

For users with connected accounts:
- Dashboard loads fast with cached data
- Clear indication of last sync time
- Easy "refresh" for API accounts
- Prompt to re-upload files if data is stale (file-based accounts)

---

## 5. Technical Architecture

### Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI (Python 3.11+), SQLAlchemy 2.0 |
| Database | PostgreSQL 15 |
| Frontend | React 18, Vite, Tailwind CSS, TanStack Query |
| Hosting | Railway or Render |
| Scheduled Tasks | Platform cron + CLI scripts |

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │  Auth    │ │ Portfolio│ │ Dashboard│ │ Broker Import    │   │
│  │  Pages   │ │ Selector │ │  Views   │ │ Wizards          │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘   │
│                         i18n (EN/HE)                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Backend API                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │  Auth    │ │  User/   │ │ Portfolio│ │ Broker Parsers   │   │
│  │  Module  │ │ Session  │ │  Service │ │ (per broker)     │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        PostgreSQL                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │  Users   │ │Portfolios│ │ Accounts │ │ Holdings/Txns    │   │
│  │ Sessions │ │          │ │          │ │ Assets/Prices    │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Platform Cron Jobs                           │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────────┐  │
│  │ broker_import  │ │ refresh_prices │ │ daily_snapshot     │  │
│  │ (hourly)       │ │ (15 min)       │ │ (daily 9:30 PM)    │  │
│  └────────────────┘ └────────────────┘ └────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Multi-tenancy | Row-level isolation (`user_id` on all tables) | Simpler than schema-per-tenant, sufficient for scale |
| Auth | Custom JWT + bcrypt + Google OAuth | Full control, no external dependencies |
| Scheduling | Platform cron + CLI scripts | Simpler than Airflow, sufficient for current needs |
| File uploads | Async via FastAPI BackgroundTasks with progress tracking | Large files (5-year history) can take 10+ seconds |

### File Upload Progress Tracking

For large file imports, users need visibility into progress:

1. **Upload endpoint** returns a `task_id` immediately
2. **Background task** processes the file, updating progress in DB or cache
3. **Progress endpoint** (`GET /api/imports/{task_id}/status`) returns:
   - Status: `pending`, `processing`, `completed`, `failed`
   - Progress percentage (e.g., "Processing row 500 of 2000")
   - Result summary on completion (transactions imported, duplicates skipped)
4. **Frontend** polls progress endpoint or uses SSE for real-time updates

| Decision | Choice | Rationale |
|----------|--------|-----------|
| API credentials | Encrypted at rest (Fernet) | Security requirement |

### Scheduled Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| `broker_import` | Hourly | Fetch data for all users with API credentials |
| `refresh_prices` | Every 15 min (weekdays), hourly (weekends) | Update asset prices from Yahoo Finance |
| `daily_snapshot` | 9:30 PM UTC | Create end-of-day portfolio snapshots for all users |
| `tase_sync` | Daily 8 PM UTC | Sync Israeli securities from TASE Data Hub |

Tasks run as CLI scripts via platform cron, with full access to environment variables and database.

### Multi-Tenancy Updates Required

Existing single-user code needs updates:

| Component | Current | Needed |
|-----------|---------|--------|
| `daily_snapshot` | All accounts | Loop through all users, then their portfolios/accounts |
| `broker_import` | Per-account | Filter by users with API credentials stored |
| `refresh_prices` | Global | No change - assets are shared |
| `tase_sync` | Global | No change - shared reference data |

---

## 6. Data Model Changes

### New Tables

```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    password_hash VARCHAR,  -- NULL if Google OAuth only
    google_id VARCHAR UNIQUE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Sessions table (for JWT revocation)
CREATE TABLE sessions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    refresh_token_hash VARCHAR,
    expires_at TIMESTAMP,
    created_at TIMESTAMP
);

-- Portfolios table (new grouping level)
CREATE TABLE portfolios (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    name VARCHAR NOT NULL,
    description TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Modified Tables

```sql
-- Accounts: add portfolio_id, remove entity_id
ALTER TABLE accounts
    ADD COLUMN portfolio_id UUID REFERENCES portfolios(id),
    DROP COLUMN entity_id;

-- All existing tables: ensure user_id for row-level isolation
-- (holdings, transactions, etc. inherit user context through account → portfolio → user)
```

### Entity Table

The `entities` table can be deprecated or kept as optional metadata on accounts for users who want to track legal entity ownership.

---

## 7. Success Metrics

### Primary Metrics

| Metric | Definition | Target (3 months post-launch) |
|--------|------------|-------------------------------|
| Weekly Active Users (WAU) | Users who log in at least once per week | 40%+ of registered users |
| Broker Connection Rate | Users who connect at least 1 broker | 70%+ of registered users |
| Multi-Broker Users | Users with 2+ brokers connected | 30%+ of active users |
| Retention (Day 30) | Users active 30 days after signup | 25%+ |
| Referral Rate | Users who share/invite others | Track (no target yet) |

### Secondary Metrics (Product Health)

| Metric | Why It Matters | Target |
|--------|----------------|--------|
| File Upload Success Rate | Are our parsers working? | 95%+ |
| Time to First Portfolio View | Onboarding friction | <10 min |
| Support Requests per User | UX clarity | Lower is better |
| Parser Coverage Requests | Which brokers are users asking for? | Tracking only |

### Instrumentation

- Basic analytics (user actions, page views)
- Event tracking: `signup`, `broker_connected`, `file_uploaded`, `file_parse_success`, `file_parse_failure`
- Error logging with context (which broker, which file type)

---

## 8. Launch Plan

### Phase 0: Private Alpha

**Audience:** You + close friends
**Goal:** End-to-end validation

- Test full flow with real accounts
- Validate parsers with real files from each broker
- Fix critical bugs
- Refine onboarding tutorials

### Phase 1: Closed Beta

**Audience:** Invite-only, ~50 users
**Goal:** Product-market fit validation

- Recruit from Israeli investor communities (Facebook groups, forums, Reddit r/israelfinance)
- Focus on users with IBKR + Israeli broker combo
- Collect feedback aggressively (in-app feedback, interviews)
- Iterate on onboarding UX
- Monitor success metrics

### Phase 2: Open Beta

**Audience:** Public, free
**Goal:** Growth and stability

- Open registration
- Content marketing:
  - Hebrew blog posts: "How to track your IBKR + Meitav portfolio"
  - YouTube tutorials
  - Social media presence
- Monitor metrics, fix scaling issues
- Add brokers based on user requests

### Phase 3: Growth & Monetization

**Goal:** Sustainable business

- Implement referral program
- Evaluate monetization options based on learnings:
  - Freemium (free tier with limits)
  - Free trial → paid
- Continue feature development based on roadmap

---

## 9. Post-MVP Roadmap

### Tier 1: High Value, Likely Needed Soon

| Feature | Description | Rationale |
|---------|-------------|-----------|
| Mobile App | React Native or PWA | Users want to check portfolio on the go |
| Dividend Tracking View | Dedicated dividend income dashboard | Popular with income investors |
| Tax Report Helpers | Cost basis reports, dividend summaries | Major pain point, potential paid feature |
| Pension Support | Manual balance updates for pension/gemel funds | Israeli brokers have poor pension exports |

Note: TWR/Performance metrics already implemented using Modified Dietz method (see Section 3.7).

### Tier 2: Medium Value, Based on Demand

| Feature | Description | Rationale |
|---------|-------------|-----------|
| Additional Brokers | Schwab, Fidelity, eToro | If users request international brokers beyond IBKR |
| Real Estate Tracking | Manual entry for property values | Expands toward wealth management |
| Goal Tracking | "Retirement: 60% funded" | Engagement driver |
| Alerts & Notifications | Price alerts, large portfolio changes | Retention driver |
| Family Sharing | Spouse can view (read-only) | Common request |

### Tier 3: Future / Monetization

| Feature | Description | Rationale |
|---------|-------------|-----------|
| Premium Tier | Advanced analytics, more accounts, priority support | Revenue |
| Advisor Mode | Manage multiple clients | New market segment (RIAs) |
| API Access | Let users export data programmatically | Power users |
| Bank Account Integration | Full wealth picture | Compete with Israeli wealth apps |

### What NOT to Build

| Feature | Reason |
|---------|--------|
| Public portfolio sharing | Privacy concerns, not core value prop |
| Stock recommendations / robo-advisor | Regulatory complexity, not our focus |
| Trading execution | Stay read-only, avoid regulatory complexity |
| News feed integration | Distraction from core value |
| Complex options/derivatives tracking | Keep it simple for retail investors |

**Exception:** Anonymous performance sharing (% only) is allowed - it's privacy-conscious and supports word-of-mouth growth.

---

## 10. Open Questions

| Question | Context | Decision Needed By |
|----------|---------|-------------------|
| Which Israeli banks to prioritize? | Banks have 900K accounts but each has different export format | Before Phase 1 |
| Freemium vs free trial model? | Monetization strategy | Phase 3 |
| PWA vs React Native for mobile? | Technical decision for mobile app | Post-MVP |
| Self-hosted vs managed PostgreSQL? | Railway/Render offer managed, but self-hosted is cheaper | Before deployment |

---

## 11. Appendix

### A. Israeli Broker Market Data (2024-2025)

| Broker | Self-Directed Accounts | AUM | Notes |
|--------|------------------------|-----|-------|
| Meitav | 89,000 | ₪383B | Largest, added 30K in 2024 |
| IBI | 52,035 | ₪70B | Fastest growing, acquired Psagot funds |
| Altshuler Shaham | Declining | -40% AUM | Lost clients due to poor performance |
| Psagot | Active | — | Still operating, ₪10K minimum |

**Overall market:** 1M+ active trading accounts in Israel
- ~900K through banks
- ~150K through non-bank brokers

### B. Competitive Landscape

| Competitor | Strengths | Weaknesses |
|------------|-----------|------------|
| Kubera | Clean UI, supports many global brokers | No Israeli broker support |
| Delta | Good crypto tracking | Weak traditional brokerage support |
| Israeli wealth apps | Local market knowledge | Only track balances, not transactions |
| Spreadsheets | Flexible, free | Manual, error-prone, no automation |

### C. References

- [Calcalist - Investment Houses](https://www.calcalist.co.il/market/article/byi00cmakx)
- [Ynet - Battle for Investment Portfolios](https://www.ynet.co.il/capital/article/rjrvgyw61x)
- [MoneyPlan - Meitav Trade Review](https://moneyplan.co.il/מיטב-טרייד-חוות-דעת-וסקירה/)
- [TradingIL - IBI Trade Review](https://tradingil.co.il/אי-בי-אי-טרייד/)