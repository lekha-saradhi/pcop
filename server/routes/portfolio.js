const router = require('express').Router();
const { verifyToken } = require('../middleware/auth');
const ds = require('../services/dataStore');

// GET /api/portfolio/summary
router.get('/summary', verifyToken, (req, res) => {
    res.json({ status: 'ok', data: ds.getPortfolioSummary() });
});

// GET /api/portfolio/tier-distribution
router.get('/tier-distribution', verifyToken, (req, res) => {
    const port = ds.getPortfolio();
    res.json({ status: 'ok', data: port.tier_distribution || [] });
});

// GET /api/portfolio/churn-trend
router.get('/churn-trend', verifyToken, (req, res) => {
    const port = ds.getPortfolio();
    res.json({ status: 'ok', data: port.churn_trend || [] });
});

// GET /api/portfolio/signal-breakdown
router.get('/signal-breakdown', verifyToken, (req, res) => {
    const port = ds.getPortfolio();
    res.json({ status: 'ok', data: port.signal_breakdown || [] });
});

// GET /api/portfolio/top-at-risk
router.get('/top-at-risk', verifyToken, (req, res) => {
    const port = ds.getPortfolio();
    const limit = parseInt(req.query.limit) || 10;
    res.json({ status: 'ok', data: (port.top_at_risk || []).slice(0, limit) });
});

// GET /api/portfolio/model-health
router.get('/model-health', verifyToken, (req, res) => {
    const port = ds.getPortfolio();
    res.json({ status: 'ok', data: port.model_health || {} });
});

// GET /api/portfolio/uplift
router.get('/uplift', verifyToken, (req, res) => {
    const port = ds.getPortfolio();
    res.json({ status: 'ok', data: port.uplift_stats || {} });
});

// GET /api/portfolio/bandit
router.get('/bandit', verifyToken, (req, res) => {
    const port = ds.getPortfolio();
    res.json({ status: 'ok', data: port.bandit_state || {} });
});

// GET /api/portfolio/full  — everything in one call (used by dashboard)
router.get('/full', verifyToken, (req, res) => {
    res.json({ status: 'ok', data: ds.getPortfolio() });
});

module.exports = router;
