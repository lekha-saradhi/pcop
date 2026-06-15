const express = require("express");

module.exports = function createEnrichmentRouter(stores) {
  const router = express.Router();

  // Reorder routes to ensure `/market-signals` is matched before dynamic routes

  // GET /api/enrichment/market-signals - Market signals by city/segment
  router.get("/market-signals", (req, res) => {
    console.log("[Market Signals] Request received with query:", req.query);
    const { city, segment } = req.query;

    const signals = [];

    if (
      !stores.enrichment ||
      !stores.enrichment.map ||
      stores.enrichment.map.size === 0
    ) {
      console.error("[Market Signals] Enrichment data is not loaded or empty.");
      return res.status(500).json({
        status: "error",
        message: "Enrichment data is not loaded. Please check the data source.",
      });
    }

    console.log("[Market Signals] Enrichment data loaded. Filtering...");
    stores.enrichment.map.forEach((enrichment, customerId) => {
      const customer = stores.customers.map.get(customerId);
      if (!customer) {
        console.warn(
          `[Market Signals] No customer found for customerId: ${customerId}`,
        );
        return;
      }

      console.log(
        `[Market Signals] Customer found: ${JSON.stringify(customer)}`,
      );

      // Temporarily return all signals without filtering
      if (enrichment.news_risk_flag) {
        signals.push({
          customer_id: customerId,
          city: customer.city,
          segment: customer.segment,
          news_risk_flag: enrichment.news_risk_flag,
          news_summary: enrichment.news_summary,
        });
      }
    });

    console.log("[Market Signals] Filtered signals:", signals);
    if (signals.length === 0) {
      console.warn(
        "[Market Signals] No market signals found for the given filters.",
      );
      return res.status(404).json({
        status: "error",
        message: "No market signals found for the given filters.",
      });
    }

    res.json({
      status: "ok",
      count: signals.length,
      data: signals,
    });
  });

  // Dynamic routes

  // GET /api/enrichment/:customer_id - Full enrichment object
  router.get("/:customer_id", (req, res) => {
    const customerId = req.params.customer_id;
    const enrichment = stores.enrichment.map.get(customerId);

    if (!enrichment) {
      return res.status(404).json({
        status: "error",
        message: `Enrichment data for customer ${customerId} not found`,
      });
    }

    res.json({
      status: "ok",
      data: enrichment,
    });
  });

  // GET /api/enrichment/:customer_id/employer - Employer info only
  router.get("/:customer_id/employer", (req, res) => {
    const customerId = req.params.customer_id;
    const enrichment = stores.enrichment.map.get(customerId);

    if (!enrichment) {
      return res.status(404).json({
        status: "error",
        message: `Enrichment data for customer ${customerId} not found`,
      });
    }

    res.json({
      status: "ok",
      data: {
        linkedin_employer: enrichment.linkedin_employer,
        linkedin_title: enrichment.linkedin_title,
        linkedin_updated_at: enrichment.linkedin_updated_at,
      },
    });
  });

  // GET /api/enrichment/:customer_id/credit - Credit info only
  router.get("/:customer_id/credit", (req, res) => {
    const customerId = req.params.customer_id;
    const enrichment = stores.enrichment.map.get(customerId);

    if (!enrichment) {
      return res.status(404).json({
        status: "error",
        message: `Enrichment data for customer ${customerId} not found`,
      });
    }

    res.json({
      status: "ok",
      data: {
        credit_score: enrichment.credit_score,
        credit_score_band: enrichment.credit_score_band,
        income_estimate: enrichment.income_estimate,
      },
    });
  });

  return router;
};
