/**
 * Kafka stream status and control endpoints
 * GET  /api/kafka/status       — current mode, message counts, recent events
 * GET  /api/kafka/stream       — SSE stream of live events (real-time push)
 * POST /api/kafka/publish      — manually inject a test event
 */
const express = require('express');
const router = express.Router();
const { verifyToken: auth } = require('../middleware/auth');
const kafkaService = require('../services/kafkaService');

// ── Status snapshot ──────────────────────────────────────────────────────────

router.get('/status', auth, (req, res) => {
    res.json({ status: 'ok', data: kafkaService.getStatus() });
});

// ── SSE live event stream ────────────────────────────────────────────────────

router.get('/stream', auth, (req, res) => {
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.setHeader('Access-Control-Allow-Origin', '*');

    // Send current status immediately on connect
    res.write(`data: ${JSON.stringify({ type: 'status', ...kafkaService.getStatus() })}\n\n`);

    // Heartbeat every 15s to keep connection alive
    const heartbeat = setInterval(() => {
        res.write(`data: ${JSON.stringify({ type: 'heartbeat', ts: new Date().toISOString() })}\n\n`);
    }, 15000);

    // Forward each new banking event to this SSE client
    const onEvent = (evt) => {
        res.write(`data: ${JSON.stringify({ type: 'event', ...evt })}\n\n`);
    };
    kafkaService.getEventBus().on('event', onEvent);

    req.on('close', () => {
        clearInterval(heartbeat);
        kafkaService.getEventBus().off('event', onEvent);
    });
});

// ── Manual event injection (for demo/testing) ────────────────────────────────

router.post('/publish', auth, async (req, res) => {
    const { topic, key, value } = req.body;
    if (!topic || !value) {
        return res.status(400).json({ status: 'error', message: 'topic and value are required' });
    }
    try {
        await kafkaService.publish(topic, key || 'manual', value);
        res.json({ status: 'ok', message: 'Event published', topic, value });
    } catch (err) {
        res.status(500).json({ status: 'error', message: err.message });
    }
});

module.exports = router;
