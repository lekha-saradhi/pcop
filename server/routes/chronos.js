/**
 * /api/chronos  — Proxy to CHRONOS FastAPI (optional service on port 8001).
 * Falls back to the pre-computed JSON data from dataStore if CHRONOS is not running.
 */
const router = require('express').Router();
const { verifyToken } = require('../middleware/auth');
const ds = require('../services/dataStore');

// GET /api/chronos/scores  — same shape as v2/scores
router.get('/scores', verifyToken, (req, res) => {
    res.json({ status: 'ok', data: ds.getScores() });
});

// GET /api/chronos/scores/:id
router.get('/scores/:id', verifyToken, (req, res) => {
    const score = ds.getScore(req.params.id);
    if (!score) return res.status(404).json({ status: 'error', message: 'Not found' });
    res.json({ status: 'ok', data: score });
});

// GET /api/chronos/health
router.get('/health', verifyToken, (req, res) => {
    const mh = ds.getPortfolio().model_health || {};
    res.json({ status: 'ok', source: 'precomputed', model_health: mh });
});

module.exports = router;
