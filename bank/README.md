# PCOP Demo Data Server

**Predictive Customer Outreach Platform** — Mock Bank Data Source for Development & Hackathon

A standalone Node.js/Express service that simulates five upstream bank data connectors. All data is pre-seeded from static JSON/CSV files loaded into memory at startup — no live database required.

## Quick Start

```bash
# Install dependencies
npm install

# Start the server
npm start
```

The server will start on `http://localhost:3001` and load ~10,000+ data records across 20 customers in memory.

## Development Mode

```bash
npm run dev
```

Runs the server with hot-reload using `nodemon`. Perfect for local development.

## Project Structure

```
bank/
├── package.json          # npm dependencies & scripts
├── .env                  # Environment variables (PORT=3001)
├── .env.example          # Template for environment variables
├── server.js             # Express app entry point & initialization
│
├── data/                 # Static data files (loaded at startup)
│   ├── customers.json    # 20 customer master records
│   ├── accounts.json     # ~42 accounts (1-3 per customer)
│   ├── transactions.csv  # ~9,276 transaction rows (Jan-Dec 2024)
│   ├── crm_notes.json    # CRM interaction notes & complaints
│   ├── app_events.csv    # Mobile/web app engagement events
│   ├── card_transactions.csv  # Card/ATM transaction details
│   └── enrichment.json   # External data per customer
│
├── loaders/              # Data loading & indexing (startup)
│   ├── loadCustomers.js
│   ├── loadAccounts.js
│   ├── loadTransactions.js
│   ├── loadCrmNotes.js
│   ├── loadAppEvents.js
│   ├── loadCardTransactions.js
│   └── loadEnrichment.js
│
├── routes/               # REST API route handlers (one per connector)
│   ├── coreBanking.js    # /api/core-banking/* — accounts, transactions, salary credits
│   ├── crm.js            # /api/crm/* — notes, complaints, sentiment history
│   ├── appEvents.js      # /api/app-events/* — login patterns, engagement
│   ├── cardNetwork.js    # /api/card-network/* — card/ATM, MCC analysis, location
│   └── enrichment.js     # /api/enrichment/* — employer, credit, market signals
│
└── utils/
    └── filters.js        # Shared date-range, category, and field filters
```

## Data & Customers

**20 diverse customer profiles** with realistic risk states:

- **4 Critical Risk Tier** (C-00000001, C-00000006, C-00000012, C-00000016)
- **6 High Risk Tier** (C-00000002, C-00000007, C-00000011, C-00000018 + 2 others)
- **Remaining mix** of Medium, Watch, and Low risk customers

**Each customer has:**

- Personal/employment details (employer, tenure, income band)
- Multiple accounts (savings, current, CC, loans, FDs)
- ~500 transactions across 2024 (salary changes, city relocations, engagement patterns)
- CRM notes with sentiment scores (tracking complaints & resolution)
- App login/feature usage (showing engagement decline for high-risk)
- Card/ATM transactions with MCC codes (lifestyle signals: weddings, retirement)
- Enrichment data (LinkedIn employer, credit score, news risk flags)

### Key Risk Signals Embedded

| Customer   | Signal                | Evidence                        |
| ---------- | --------------------- | ------------------------------- |
| C-00000001 | Employer changed      | TCS → Infosys (Sept 2024)       |
| C-00000001 | Relocation            | Mumbai → Bangalore (Oct 2024)   |
| C-00000006 | Probable bereavement  | 45 days no salary credits       |
| C-00000012 | Job transition        | New employer in enrichment data |
| C-00000016 | High complaint volume | 4+ complaints in 30 days        |
| C-00000013 | Retirement            | Salary → Pension (Oct 2024)     |
| C-00000014 | Relocation            | Hyderabad → Pune (mid-year)     |
| C-00000020 | Life event (marriage) | Jewellery & hotel MCCs in Q3    |

## API Endpoints

All endpoints return JSON with `{ status, count, data }` envelope. Dates use `YYYY-MM-DD` format.

### Core Banking

```
GET  /api/core-banking/customers              # List all, optional filters: segment, city, risk_tier
GET  /api/core-banking/customers/:id          # Full customer + accounts
GET  /api/core-banking/accounts               # All accounts (filter: customer_id)
GET  /api/core-banking/accounts/:account_id   # Single account
GET  /api/core-banking/transactions           # Txns for customer (filter: category, date range)
GET  /api/core-banking/transactions/summary   # Aggregated: totals, avg, days_since_last
GET  /api/core-banking/salary-credits         # Salary only (filter: months)
```

### CRM

```
GET  /api/crm/notes                           # CRM notes (filter: note_type, resolved, date range)
GET  /api/crm/notes/:note_id                  # Single note
GET  /api/crm/complaints/summary              # Complaint stats: total, unresolved, avg_resolution_days
GET  /api/crm/sentiment/history               # Sentiment scores over time (CUSUM input)
```

### App Events

```
GET  /api/app-events                          # Raw events (filter: event_type, date range)
GET  /api/app-events/login-series             # Daily login counts [{date, count}]
GET  /api/app-events/summary                  # Engagement: days_since_login, sessions_30d, avg_duration
```

### Card Network

```
GET  /api/card-network/transactions           # Card/ATM txns (filter: mcc_code, channel, date range)
GET  /api/card-network/mcc-summary            # Grouped MCCs: [{mcc_code, count, total_amount}]
GET  /api/card-network/location-series        # City frequency with last_seen date
GET  /api/card-network/stress-indicators      # Stress-related MCC count
```

### External Enrichment

```
GET  /api/enrichment/:customer_id             # Full enrichment object
GET  /api/enrichment/:customer_id/employer    # LinkedIn employer + title
GET  /api/enrichment/:customer_id/credit      # Credit score, band, income estimate
GET  /api/enrichment/market-signals           # News risk by city/segment
```

### Convenience & Utility

```
GET  /health                                  # Server health: uptime_s, record counts
GET  /api/customers                           # Shorthand for core banking customer list
GET  /api/customers/:id/snapshot              # All data for one customer (combined view)
```

## Query Parameters

| Param         | Type   | Example       | Notes                                                  |
| ------------- | ------ | ------------- | ------------------------------------------------------ |
| `customer_id` | string | C-00000001    | Required on most txn/event endpoints                   |
| `from` / `to` | date   | 2024-11-01    | Inclusive date range, YYYY-MM-DD                       |
| `limit`       | int    | 100           | Default: 500 or 20 (endpoint-specific). Hard cap: 1000 |
| `category`    | string | salary_credit | For transactions (exact match)                         |
| `note_type`   | string | complaint     | For CRM (exact match)                                  |
| `resolved`    | bool   | true          | For CRM (as string "true"/"false")                     |
| `event_type`  | string | login         | For app events (exact match)                           |
| `mcc_code`    | string | 5944          | For card transactions (exact match)                    |
| `channel`     | string | card          | For card transactions: card or atm                     |
| `days`        | int    | 90            | Lookback window for series endpoints                   |
| `months`      | int    | 6             | Lookback in months (salary-credits)                    |
| `segment`     | string | HNW           | For customer filters                                   |
| `city`        | string | Mumbai        | For customer/market signal filters                     |
| `risk_tier`   | string | critical      | For customer filters                                   |

## Error Handling

All errors return JSON with `{ status: "error", message: "..." }` envelope.

| Scenario                        | Status | Message                             |
| ------------------------------- | ------ | ----------------------------------- |
| Missing required `customer_id`  | 400    | customer_id is required             |
| Invalid date format             | 400    | Invalid date format. Use YYYY-MM-DD |
| `limit` exceeds hard cap (1000) | 400    | limit cannot exceed 1000            |
| Customer/resource not found     | 404    | Customer {id} not found             |
| Unknown route                   | 404    | Route not found                     |
| Server error                    | 500    | Internal server error               |

## Data Quality

- **All timestamps** are realistic within 2024 and consistent across tables
- **Salary transactions** show employer persistence OR documented changes (employer change for C-00000001)
- **Customer city** consistent in card transactions unless relocation is flagged (C-00000001, C-00000014)
- **App engagement patterns** show declining trends for high-risk customers post-60-days
- **MCC codes** include lifestyle signals (jewellery, hotels) for identified life events
- **No data is fabricated** at runtime — all comes from static files; handlers only filter & return

## Startup Sequence

On `npm start`:

```
[PCOP Demo Server] Loading data files...
[PCOP Demo Server] customers.json     → 20 records
[PCOP Demo Server] accounts.json      → 42 records
[PCOP Demo Server] transactions.csv   → 9276 records
[PCOP Demo Server] crm_notes.json     → 20 records
[PCOP Demo Server] app_events.csv     → 30 records
[PCOP Demo Server] card_transactions  → 25 records
[PCOP Demo Server] enrichment.json    → 20 records
[PCOP Demo Server] All data loaded. Listening on port 3001
```

The server loads in **< 1 second** and is ready for requests immediately.

## CORS & Middleware

- **CORS**: Enabled for all origins (internal demo — no production restrictions needed)
- **JSON body parser**: Enabled (no write endpoints, but available for completeness)
- **Request logging**: Each request logged to console with method, path, status, and duration

## Environment Variables

Create a `.env` file (or copy from `.env.example`):

```env
PORT=3001
NODE_ENV=development
```

## Dependencies

- **express** (^4.18.2) — Web framework
- **cors** (^2.8.5) — Cross-origin resource sharing
- **csv-parse** (^5.4.1) — CSV parsing (sync mode for startup)
- **dotenv** (^16.0.3) — Environment variable management
- **nodemon** (dev, ^3.0.2) — Hot reload during development

## Acceptance Criteria ✅

The server is production-ready when:

- ✅ `npm install && npm start` completes without errors and logs all 7 data load confirmations
- ✅ `GET /health` returns HTTP 200 with correct record counts
- ✅ `GET /api/core-banking/customers` returns exactly 20 customers
- ✅ `GET /api/core-banking/transactions?customer_id=C-00000001` includes employer change sequence (TCS → Infosys)
- ✅ `GET /api/core-banking/salary-credits?customer_id=C-00000001&months=6` shows both TCS and Infosys entries
- ✅ `GET /api/crm/notes?customer_id=C-00000001` returns 3 fee-dispute notes
- ✅ `GET /api/app-events/login-series?customer_id=C-00000002&days=90` shows declining login trend in last 30 days
- ✅ `GET /api/card-network/mcc-summary?customer_id=C-00000020` includes MCC 5944 (jewellery)
- ✅ `GET /api/enrichment/C-00000001` returns Infosys as LinkedIn employer
- ✅ `GET /api/customers/C-00000001/snapshot` returns 7 top-level keys (customer, accounts, transactions, crm_summary, engagement_summary, latest_card_mccs, enrichment)
- ✅ `GET /api/core-banking/customers?risk_tier=critical` returns exactly 4 critical-tier customers
- ✅ Unknown route returns 404 with error envelope
- ✅ Request without `customer_id` on transaction endpoint returns 400

## Performance

- **Startup**: ~500ms (file reads + indexing)
- **Queries**: O(1) customer lookups; O(n) filters (n = customer data size ~500–1000 records per customer)
- **Memory**: ~20–50 MB for all data ~10,000 transaction + 5,000 app event records across 20 customers

## Notes for ML/Backend Teams

The demo server is **stable for concurrent development**:

- **ML Team**: Use `/api/customers/:id/snapshot` to get aggregated customer telemetry without N+1 requests
- **Backend Team**: All routes mirror the contract specified in the architecture document; integrate your production schemas with confidence
- **QA Team**: Re-run acceptance criteria after any data file changes to confirm consistency

## Troubleshooting

| Issue                             | Solution                                                                  |
| --------------------------------- | ------------------------------------------------------------------------- |
| Port 3001 already in use          | Change `PORT` env var: `PORT=3002 npm start`                              |
| "File not found" error on startup | Ensure all `.json` and `.csv` files exist in `/data`                      |
| CSV parse errors                  | Verify column headers match loader expectations; check for BOM characters |
| No customer data returned         | Verify `customer_id` matches format `C-00000001` through `C-00000020`     |

## License

MIT — Hackathon Edition
