const express = require("express");
const {
  filterByDateRange,
  filterByCategory,
  sliceArray,
  validateDateFormat,
} = require("../utils/filters");

module.exports = function createCoreBankingRouter(stores) {
  const router = express.Router();

  // GET /api/core-banking/customers - List all customers with optional filters
  router.get("/customers", (req, res) => {
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

    results = sliceArray(results, req.query.limit);

    res.json({
      status: "ok",
      count: results.length,
      data: results,
    });
  });

  // GET /api/core-banking/customers/:id - Full customer object
  router.get("/customers/:id", (req, res) => {
    const customerId = req.params.id;
    const customer = stores.customers.map.get(customerId);

    if (!customer) {
      return res.status(404).json({
        status: "error",
        message: `Customer ${customerId} not found`,
      });
    }

    const accounts = stores.accounts.byCustomer.get(customerId) || [];

    res.json({
      status: "ok",
      data: {
        ...customer,
        accounts: accounts,
      },
    });
  });

  // GET /api/core-banking/accounts - All accounts with optional customer_id filter
  router.get("/accounts", (req, res) => {
    const { customer_id } = req.query;

    let results = [];
    if (customer_id) {
      results = stores.accounts.byCustomer.get(customer_id) || [];
    } else {
      results = Array.from(stores.accounts.byCustomer.values()).flat();
    }

    results = sliceArray(results, req.query.limit);

    res.json({
      status: "ok",
      count: results.length,
      data: results,
    });
  });

  // GET /api/core-banking/accounts/:account_id - Single account
  router.get("/accounts/:account_id", (req, res) => {
    const account = stores.accounts.byId.get(req.params.account_id);

    if (!account) {
      return res.status(404).json({
        status: "error",
        message: `Account ${req.params.account_id} not found`,
      });
    }

    res.json({
      status: "ok",
      data: account,
    });
  });

  // GET /api/core-banking/transactions - Transactions for a customer
  router.get("/transactions", (req, res) => {
    const { customer_id, from, to, category, limit } = req.query;

    if (!customer_id) {
      return res.status(400).json({
        status: "error",
        message: "customer_id is required",
      });
    }

    if (
      (from && !validateDateFormat(from)) ||
      (to && !validateDateFormat(to))
    ) {
      return res.status(400).json({
        status: "error",
        message: "Invalid date format. Use YYYY-MM-DD",
      });
    }

    let transactions = stores.transactions.map.get(customer_id) || [];

    transactions = filterByDateRange(transactions, "txn_date", from, to);
    if (category) {
      transactions = filterByCategory(transactions, category);
    }

    transactions = sliceArray(transactions, limit || 500);

    res.json({
      status: "ok",
      count: transactions.length,
      data: transactions,
    });
  });

  // GET /api/core-banking/transactions/summary - Aggregated transaction summary
  router.get("/transactions/summary", (req, res) => {
    const { customer_id, from, to } = req.query;

    if (!customer_id) {
      return res.status(400).json({
        status: "error",
        message: "customer_id is required",
      });
    }

    if (
      (from && !validateDateFormat(from)) ||
      (to && !validateDateFormat(to))
    ) {
      return res.status(400).json({
        status: "error",
        message: "Invalid date format. Use YYYY-MM-DD",
      });
    }

    let transactions = stores.transactions.map.get(customer_id) || [];
    transactions = filterByDateRange(transactions, "txn_date", from, to);

    const summary = {
      total_debit: 0,
      total_credit: 0,
      txn_count: transactions.length,
      avg_amount: 0,
      days_since_last_txn: null,
    };

    transactions.forEach((txn) => {
      if (txn.direction === "debit") {
        summary.total_debit += parseFloat(txn.amount) || 0;
      } else {
        summary.total_credit += parseFloat(txn.amount) || 0;
      }
    });

    if (transactions.length > 0) {
      summary.avg_amount =
        (summary.total_debit + summary.total_credit) / transactions.length;
      const lastTxnDate = new Date(transactions[0].txn_date);
      const today = new Date();
      summary.days_since_last_txn = Math.floor(
        (today - lastTxnDate) / (1000 * 60 * 60 * 24),
      );
    }

    res.json({
      status: "ok",
      data: summary,
    });
  });

  // GET /api/core-banking/salary-credits - Only salary credit transactions
  router.get("/salary-credits", (req, res) => {
    const { customer_id, months } = req.query;

    if (!customer_id) {
      return res.status(400).json({
        status: "error",
        message: "customer_id is required",
      });
    }

    let transactions = stores.transactions.map.get(customer_id) || [];
    transactions = filterByCategory(transactions, "salary_credit");

    // Filter by months if specified
    if (months) {
      const monthsInt = Math.min(parseInt(months), 12);
      const cutoffDate = new Date();
      cutoffDate.setMonth(cutoffDate.getMonth() - monthsInt);
      transactions = transactions.filter(
        (txn) => new Date(txn.txn_date) >= cutoffDate,
      );
    }

    res.json({
      status: "ok",
      count: transactions.length,
      data: transactions,
    });
  });

  // GET /api/core-banking/account-events - Account lifecycle events
  router.get("/account-events", (req, res) => {
    const { customer_id } = req.query;

    let results = [];
    if (customer_id) {
      results = stores.accountEvents.byCustomer.get(customer_id) || [];
    } else {
      results = stores.accountEvents.all;
    }

    results = sliceArray(results, req.query.limit);

    res.json({
      status: "ok",
      count: results.length,
      data: results,
    });
  });

  // GET /api/core-banking/kyc-updates - KYC field update history
  router.get("/kyc-updates", (req, res) => {
    const { customer_id, field_name, verification_status } = req.query;

    let results = [];
    if (customer_id) {
      results = stores.kycUpdates.byCustomer.get(customer_id) || [];
    } else {
      results = stores.kycUpdates.all;
    }

    if (field_name) {
      results = results.filter((u) => u.field_name === field_name);
    }
    if (verification_status) {
      results = results.filter((u) => u.verification_status === verification_status);
    }

    results = sliceArray(results, req.query.limit);

    res.json({
      status: "ok",
      count: results.length,
      data: results,
    });
  });

  // GET /api/core-banking/portfolio-stats - Portfolio-level statistics
  router.get("/portfolio-stats", (req, res) => {
    const customers = Array.from(stores.customers.map.values());

    const stats = {
      total_customers: customers.length,
      critical_count: customers.filter((c) => c.risk_tier === "critical").length,
      high_count: customers.filter((c) => c.risk_tier === "high").length,
      medium_count: customers.filter((c) => c.risk_tier === "medium").length,
      watch_count: customers.filter((c) => c.risk_tier === "watch").length,
      low_count: customers.filter((c) => c.risk_tier === "low").length,
      avg_churn_score: customers.length
        ? customers.reduce((acc, c) => acc + c.churn_score, 0) / customers.length
        : 0,
      outreach_sent_this_week: 47,
    };

    res.json({
      status: "ok",
      data: stats,
    });
  });

  return router;
};
