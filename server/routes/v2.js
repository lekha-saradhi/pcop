/**
 * /api/v2  — Precision Risk Engine (CHRONOS) endpoints
 * Serves pre-computed ensemble scores, action plans, HERALD content, and model health.
 */
const router = require('express').Router();
const { verifyToken } = require('../middleware/auth');
const ds = require('../services/dataStore');

// GET /api/v2/scores          — all 50 ensemble scores
router.get('/scores', verifyToken, (req, res) => {
    res.json({ status: 'ok', data: ds.getScores(), count: ds.SCORES.length });
});

// GET /api/v2/scores/:id
router.get('/scores/:id', verifyToken, (req, res) => {
    const score = ds.getScore(req.params.id);
    if (!score) return res.status(404).json({ status: 'error', message: 'Not found' });
    res.json({ status: 'ok', data: score });
});

// GET /api/v2/signals         — all signals
router.get('/signals', verifyToken, (req, res) => {
    res.json({ status: 'ok', data: ds.getAllSignals() });
});

// GET /api/v2/signals/:id
router.get('/signals/:id', verifyToken, (req, res) => {
    const signals = ds.getSignals(req.params.id);
    res.json({ status: 'ok', customer_id: req.params.id,
               signals, alarm_count: signals.length });
});

// GET /api/v2/action-plans    — all COMPASS decisions
router.get('/action-plans', verifyToken, (req, res) => {
    res.json({ status: 'ok', data: ds.getActionPlans(), count: ds.ACTION_PLANS.length });
});

// GET /api/v2/action-plans/:id
router.get('/action-plans/:id', verifyToken, (req, res) => {
    const plan = ds.getActionPlan(req.params.id);
    if (!plan) return res.status(404).json({ status: 'error', message: 'Not found' });
    res.json({ status: 'ok', data: plan });
});

// GET /api/v2/content         — all HERALD content
router.get('/content', verifyToken, (req, res) => {
    res.json({ status: 'ok', data: ds.getHeraldAll(), count: ds.HERALD.length });
});

// GET /api/v2/content/:id
router.get('/content/:id', verifyToken, (req, res) => {
    const herald = ds.getHerald(req.params.id);
    if (!herald) return res.status(404).json({ status: 'error', message: 'No content' });
    res.json({ status: 'ok', data: herald });
});

// GET /api/v2/model-health
router.get('/model-health', verifyToken, (req, res) => {
    const port = ds.getPortfolio();
    res.json({ status: 'ok', data: port.model_health || {} });
});

// GET /api/v2/portfolio-survival  — portfolio-level survival summary
router.get('/portfolio-survival', verifyToken, (req, res) => {
    const scores = ds.getScores();
    const summary = {
        avg_p7:  +(scores.reduce((s,c) => s + c.p7,  0) / scores.length).toFixed(4),
        avg_p30: +(scores.reduce((s,c) => s + c.p30, 0) / scores.length).toFixed(4),
        avg_p90: +(scores.reduce((s,c) => s + c.p90, 0) / scores.length).toFixed(4),
        urgent_7d:  scores.filter(c => c.p7  > 0.40).length,
        urgent_30d: scores.filter(c => c.p30 > 0.40).length,
        urgent_90d: scores.filter(c => c.p90 > 0.40).length,
    };
    res.json({ status: 'ok', data: summary });
});

module.exports = router;
