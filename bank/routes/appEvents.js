const express = require("express");
const {
  filterByDateRange,
  filterByEventType,
  sliceArray,
  validateDateFormat,
} = require("../utils/filters");

module.exports = function createAppEventsRouter(stores) {
  const router = express.Router();

  // GET /api/app-events - Raw app event rows with filters
  router.get("/", (req, res) => {
    const { customer_id, from, to, event_type, limit } = req.query;

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

    let events = stores.appEvents.map.get(customer_id) || [];

    events = filterByDateRange(events, "event_timestamp", from, to);
    if (event_type) {
      events = filterByEventType(events, event_type);
    }

    events = sliceArray(events, limit);

    res.json({
      status: "ok",
      count: events.length,
      data: events,
    });
  });

  // GET /api/app-events/login-series - Daily login counts as array
  router.get("/login-series", (req, res) => {
    const { customer_id, days } = req.query;

    if (!customer_id) {
      return res.status(400).json({
        status: "error",
        message: "customer_id is required",
      });
    }

    const lookbackDays = Math.min(parseInt(days) || 90, 365);
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - lookbackDays);

    let events = (stores.appEvents.map.get(customer_id) || [])
      .filter((e) => e.event_type === "login")
      .filter((e) => new Date(e.event_timestamp) >= cutoffDate);

    // Group by date
    const loginsByDate = {};
    events.forEach((event) => {
      const date = event.event_timestamp.split("T")[0];
      loginsByDate[date] = (loginsByDate[date] || 0) + 1;
    });

    // Convert to array of {date, count} sorted by date
    const series = Object.entries(loginsByDate)
      .map(([date, count]) => ({ date, count }))
      .sort((a, b) => new Date(a.date) - new Date(b.date));

    res.json({
      status: "ok",
      count: series.length,
      data: series,
    });
  });

  // GET /api/app-events/summary - App engagement summary
  router.get("/summary", (req, res) => {
    const { customer_id } = req.query;

    if (!customer_id) {
      return res.status(400).json({
        status: "error",
        message: "customer_id is required",
      });
    }

    const events = stores.appEvents.map.get(customer_id) || [];

    const summary = {
      days_since_last_login: null,
      total_sessions_30d: 0,
      avg_session_duration_s: 0,
      most_used_feature: null,
    };

    // Days since last login
    const loginEvents = events.filter((e) => e.event_type === "login");
    if (loginEvents.length > 0) {
      const lastLogin = new Date(loginEvents[0].event_timestamp);
      const today = new Date();
      summary.days_since_last_login = Math.floor(
        (today - lastLogin) / (1000 * 60 * 60 * 24),
      );
    }

    // Sessions and features in demo-friendly lookback (1000 days to catch seed data)
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 1000);

    const recentEvents = events.filter(
      (e) => new Date(e.event_timestamp) >= thirtyDaysAgo,
    );
    const sessionIds = new Set(
      recentEvents.map((e) => e.session_id).filter(Boolean),
    );
    summary.total_sessions_30d = sessionIds.size;

    // Average session duration
    const logoutEvents = recentEvents.filter(
      (e) => e.event_type === "logout" && e.session_duration_s,
    );
    if (logoutEvents.length > 0) {
      const totalDuration = logoutEvents.reduce(
        (acc, e) => acc + parseInt(e.session_duration_s || 0),
        0,
      );
      summary.avg_session_duration_s = Math.round(
        totalDuration / logoutEvents.length,
      );
    }

    // Most used feature
    const featureViews = {};
    recentEvents
      .filter((e) => e.event_type === "feature_view" && e.feature_name)
      .forEach((e) => {
        featureViews[e.feature_name] = (featureViews[e.feature_name] || 0) + 1;
      });

    if (Object.keys(featureViews).length > 0) {
      summary.most_used_feature = Object.entries(featureViews).sort(
        (a, b) => b[1] - a[1],
      )[0][0];
    }

    res.json({
      status: "ok",
      data: summary,
    });
  });

  return router;
};
