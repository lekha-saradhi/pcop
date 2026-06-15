const express = require("express");
const {
  filterByDateRange,
  filterByMcc,
  filterByChannel,
  sliceArray,
  validateDateFormat,
} = require("../utils/filters");

module.exports = function createCardNetworkRouter(stores) {
  const router = express.Router();

  // GET /api/card-network/transactions - Card and ATM transactions
  router.get("/transactions", (req, res) => {
    const { customer_id, from, to, mcc_code, channel, limit } = req.query;

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

    let transactions = stores.cardTransactions.map.get(customer_id) || [];

    transactions = filterByDateRange(transactions, "txn_date", from, to);
    if (mcc_code) {
      transactions = filterByMcc(transactions, mcc_code);
    }
    if (channel) {
      transactions = filterByChannel(transactions, channel);
    }

    transactions = sliceArray(transactions, limit);

    res.json({
      status: "ok",
      count: transactions.length,
      data: transactions,
    });
  });

  // GET /api/card-network/mcc-summary - Grouped MCC counts
  router.get("/mcc-summary", (req, res) => {
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

    let transactions = stores.cardTransactions.map.get(customer_id) || [];
    transactions = filterByDateRange(transactions, "txn_date", from, to);

    // Group by MCC
    const mccSummary = {};
    transactions.forEach((txn) => {
      const mcc = txn.mcc_code;
      const desc = txn.mcc_description;
      const amount = parseFloat(txn.amount) || 0;

      if (!mccSummary[mcc]) {
        mccSummary[mcc] = {
          mcc_code: mcc,
          mcc_description: desc,
          count: 0,
          total_amount: 0,
        };
      }

      mccSummary[mcc].count += 1;
      mccSummary[mcc].total_amount += amount;
    });

    const result = Object.values(mccSummary).sort((a, b) => b.count - a.count);

    res.json({
      status: "ok",
      count: result.length,
      data: result,
    });
  });

  // GET /api/card-network/location-series - City frequency
  router.get("/location-series", (req, res) => {
    const { customer_id, days } = req.query;

    if (!customer_id) {
      return res.status(400).json({
        status: "error",
        message: "customer_id is required",
      });
    }

    const lookbackDays = Math.min(parseInt(days) || 1000, 3000);
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - lookbackDays);

    let transactions = (
      stores.cardTransactions.map.get(customer_id) || []
    ).filter((t) => new Date(t.txn_date) >= cutoffDate);

    // Group by city
    const citySummary = {};
    transactions.forEach((txn) => {
      const city = txn.merchant_city;

      if (!citySummary[city]) {
        citySummary[city] = {
          city: city,
          transaction_count: 0,
          last_seen: null,
        };
      }

      citySummary[city].transaction_count += 1;
      if (
        !citySummary[city].last_seen ||
        txn.txn_date > citySummary[city].last_seen
      ) {
        citySummary[city].last_seen = txn.txn_date;
      }
    });

    const result = Object.values(citySummary).sort(
      (a, b) => b.transaction_count - a.transaction_count,
    );

    res.json({
      status: "ok",
      count: result.length,
      data: result,
    });
  });

  // GET /api/card-network/stress-indicators - Stress-related MCC count
  router.get("/stress-indicators", (req, res) => {
    const { customer_id } = req.query;

    if (!customer_id) {
      return res.status(400).json({
        status: "error",
        message: "customer_id is required",
      });
    }

    const transactions = stores.cardTransactions.map.get(customer_id) || [];

    // Stress-related MCCs: payday, pawnbroker, money transfer
    const stressMccs = ["6051", "6211", "7995"]; // Examples
    const stressTxns = transactions.filter((t) =>
      stressMccs.includes(t.mcc_code),
    );

    res.json({
      status: "ok",
      data: {
        stress_related_mcc_count: stressTxns.length,
        overdraft_related_txns: 0, // Would need checking against account limits
      },
    });
  });

  return router;
};
