const express = require("express");
const cors = require("cors");
const path = require("path");
require("dotenv").config();

// Import loaders
const loadCustomers = require("./loaders/loadCustomers");
const loadAccounts = require("./loaders/loadAccounts");
const loadTransactions = require("./loaders/loadTransactions");
const loadCrmNotes = require("./loaders/loadCrmNotes");
const loadAppEvents = require("./loaders/loadAppEvents");
const loadCardTransactions = require("./loaders/loadCardTransactions");
const loadEnrichment = require("./loaders/loadEnrichment");
const loadAccountEvents = require("./loaders/loadAccountEvents");
const loadKycUpdates = require("./loaders/loadKycUpdates");

// Import routes
const createCoreBankingRouter = require("./routes/coreBanking");
const createCrmRouter = require("./routes/crm");
const createAppEventsRouter = require("./routes/appEvents");
const createCardNetworkRouter = require("./routes/cardNetwork");
const createEnrichmentRouter = require("./routes/enrichment");

const PORT = process.env.PORT || 3001;
const app = express();
let startTime = Date.now();

// Middleware
app.use(cors());
app.use(express.json());

// Request logging middleware
app.use((req, res, next) => {
  const start = Date.now();
  res.on("finish", () => {
    const duration = Date.now() - start;
    console.log(
      `${req.method} ${req.path} → ${res.statusCode} (${duration}ms)`,
    );
  });
  next();
});

// Load all data at startup
async function initializeServer() {
  try {
    console.log("[PCOP Demo Server] Loading data files...");

    // Load all data in parallel
    const [
      customers,
      accounts,
      transactions,
      crmNotes,
      appEvents,
      cardTransactions,
      enrichment,
      accountEvents,
      kycUpdates,
    ] = await Promise.all([
      loadCustomers(),
      loadAccounts(),
      loadTransactions(),
      loadCrmNotes(),
      loadAppEvents(),
      loadCardTransactions(),
      loadEnrichment(),
      loadAccountEvents(),
      loadKycUpdates(),
    ]);

    // Log load results
    console.log(
      `[PCOP Demo Server] customers.json     → ${customers.count} records`,
    );
    console.log(
      `[PCOP Demo Server] accounts.json      → ${accounts.count} records`,
    );
    console.log(
      `[PCOP Demo Server] transactions.csv   → ${transactions.count} records`,
    );
    console.log(
      `[PCOP Demo Server] crm_notes.json     → ${crmNotes.count} records`,
    );
    console.log(
      `[PCOP Demo Server] app_events.csv     → ${appEvents.count} records`,
    );
    console.log(
      `[PCOP Demo Server] card_transactions  → ${cardTransactions.count} records`,
    );
    console.log(
      `[PCOP Demo Server] enrichment.json    → ${enrichment.count} records`,
    );
    console.log(
      `[PCOP Demo Server] account_events.json → ${accountEvents.count} records`,
    );
    console.log(
      `[PCOP Demo Server] kyc_updates.json    → ${kycUpdates.count} records`,
    );

    // Create stores object
    const stores = {
      customers,
      accounts,
      transactions,
      crmNotes,
      appEvents,
      cardTransactions,
      enrichment,
      accountEvents,
      kycUpdates,
    };

    // Register route handlers with stores
    app.use("/api/core-banking", createCoreBankingRouter(stores));
    app.use("/api/crm", createCrmRouter(stores));
    app.use("/api/app-events", createAppEventsRouter(stores));
    app.use("/api/card-network", createCardNetworkRouter(stores));
    app.use("/api/enrichment", createEnrichmentRouter(stores));

    // Convenience route
    app.get("/api/customers", (req, res) => {
      const { segment, city, risk_tier } = req.query;
      let results = Array.from(stores.customers.map.values());

      if (segment) {
        results = results.filter((c) => c.segment === segment);
      }
      if (city) {
        results = results.filter((c) => c.city === city);
      }
      if (risk_tier) {
        results = results.filter((c) => c.risk_tier === risk_tier);
      }

      const limit = Math.min(parseInt(req.query.limit) || results.length, 1000);
      results = results.slice(0, limit);

      res.json({
        status: "ok",
        count: results.length,
        data: results,
      });
    });

    // Snapshot endpoint
    app.get("/api/customers/:id/snapshot", (req, res) => {
      const customerId = req.params.id;
      const customer = stores.customers.map.get(customerId);

      if (!customer) {
        return res.status(404).json({
          status: "error",
          message: `Customer ${customerId} not found`,
        });
      }

      const accounts = stores.accounts.byCustomer.get(customerId) || [];

      // Last 30 days transactions
      const thirtyDaysAgo = new Date();
      thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
      const recentTransactions = (
        stores.transactions.map.get(customerId) || []
      ).filter((t) => new Date(t.txn_date) >= thirtyDaysAgo);

      // CRM summary
      const crmNotesList = stores.crmNotes.byCustomer.get(customerId) || [];
      const complaints = crmNotesList.filter(
        (n) => n.note_type === "complaint",
      );
      const crmSummary = {
        total_complaints: complaints.length,
        unresolved_count: complaints.filter((c) => !c.resolved).length,
        last_complaint_at:
          complaints.length > 0 ? complaints[0].created_at : null,
      };

      // Engagement summary
      const loginEvents = (stores.appEvents.map.get(customerId) || []).filter(
        (e) => e.event_type === "login",
      );
      const engagementSummary = {
        days_since_last_login:
          loginEvents.length > 0
            ? Math.floor(
              (new Date() - new Date(loginEvents[0].event_timestamp)) /
              (1000 * 60 * 60 * 24),
            )
            : null,
        total_sessions_30d: new Set(
          (stores.appEvents.map.get(customerId) || [])
            .filter((e) => new Date(e.event_timestamp) >= thirtyDaysAgo)
            .map((e) => e.session_id)
            .filter(Boolean),
        ).size,
      };

      // Top 5 MCCs (last 60 days)
      const sixtyDaysAgo = new Date();
      sixtyDaysAgo.setDate(sixtyDaysAgo.getDate() - 60);
      const recentCardTxns = (
        stores.cardTransactions.map.get(customerId) || []
      ).filter((t) => new Date(t.txn_date) >= sixtyDaysAgo);

      const mccCounts = {};
      recentCardTxns.forEach((txn) => {
        const key = txn.mcc_code;
        if (!mccCounts[key]) {
          mccCounts[key] = {
            mcc_code: key,
            mcc_description: txn.mcc_description,
            count: 0,
          };
        }
        mccCounts[key].count += 1;
      });

      const topMccs = Object.values(mccCounts)
        .sort((a, b) => b.count - a.count)
        .slice(0, 5);

      const enrichment = stores.enrichment.map.get(customerId) || {};

      res.json({
        status: "ok",
        data: {
          customer,
          accounts,
          recent_transactions: recentTransactions,
          crm_summary: crmSummary,
          engagement_summary: engagementSummary,
          latest_card_mccs: topMccs,
          enrichment,
        },
      });
    });

    // Health check
    app.get("/health", (req, res) => {
      const uptime = Math.floor((Date.now() - startTime) / 1000);
      res.json({
        status: "ok",
        timestamp: new Date().toISOString(),
        uptime_s: uptime,
        records: {
          customers: customers.count,
          accounts: accounts.count,
          transactions: transactions.count,
          crm_notes: crmNotes.count,
          app_events: appEvents.count,
          card_transactions: cardTransactions.count,
          enrichment: enrichment.count,
          account_events: accountEvents.count,
          kyc_updates: kycUpdates.count,
        },
      });
    });

    // 404 handler
    app.use((req, res) => {
      res.status(404).json({
        status: "error",
        message: "Route not found",
      });
    });

    // Error handler
    app.use((err, req, res, next) => {
      console.error("Error:", err);
      res.status(500).json({
        status: "error",
        message: "Internal server error",
      });
    });

    // Start server
    app.listen(PORT, () => {
      console.log(
        `[PCOP Demo Server] All data loaded. Listening on port ${PORT}`,
      );
    });
  } catch (error) {
    console.error("[PCOP Demo Server] Failed to initialize:", error.message);
    process.exit(1);
  }
}

// Start the server
initializeServer();

module.exports = app;
