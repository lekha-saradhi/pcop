const router = require('express').Router();
const { verifyToken, requireRole } = require('../middleware/auth');
const ds = require('../services/dataStore');

// In-memory review queue — seeded with PRIORITY + ESCALATE customers
const reviewQueue = ds.CUSTOMERS
    .filter(c => ['PRIORITY','ESCALATE'].includes(c.risk_tier))
    .slice(0, 10)
    .map((c, i) => ({
        id:          `REV-${String(i+1).padStart(4,'0')}`,
        customer_id: c.customer_id,
        full_name:   c.full_name,
        risk_tier:   c.risk_tier,
        churn_score: c.churn_score,
        action:      ds.getActionPlan(c.customer_id)?.action || 'EMAIL',
        status:      'pending',
        created_at:  new Date(Date.now() - i * 3_600_000).toISOString(),
        reviewed_at: null,
        reviewer:    null,
        notes:       null,
        actionLog:   [],
    }));

// GET /api/reviews
router.get('/', verifyToken, (req, res) => {
    const { status } = req.query;
    const list = status ? reviewQueue.filter(r => r.status === status) : reviewQueue;
    // Strip internal actionLog
    const out = list.map(({ actionLog, ...r }) => r);
    res.json({ status: 'ok', reviews: out, total: out.length });
});

// GET /api/reviews/stats
router.get('/stats', verifyToken, (req, res) => {
    const pending   = reviewQueue.filter(r => r.status === 'pending').length;
    const approved  = reviewQueue.filter(r => r.status === 'approved').length;
    const rejected  = reviewQueue.filter(r => r.status === 'rejected').length;
    const in_review = reviewQueue.filter(r => r.status === 'in_review').length;
    res.json({
        status: 'ok',
        data: { pending, in_review, approved, rejected, total: reviewQueue.length },
    });
});

// GET /api/reviews/officers
router.get('/officers', verifyToken, (req, res) => {
    res.json({
        status: 'ok',
        data: [
            { id: 'manager', name: 'Portfolio Manager', role: 'manager' },
            { id: 'admin',   name: 'Administrator',     role: 'admin'   },
        ],
    });
});

// GET /api/reviews/:id
router.get('/:id', verifyToken, (req, res) => {
    const r = reviewQueue.find(x => x.id === req.params.id);
    if (!r) return res.status(404).json({ status: 'error', message: 'Not found' });
    const snap = ds.getCustomerSnapshot(r.customer_id);
    const { actionLog, ...review } = r;
    res.json({ status: 'ok', review, snapshot: snap });
});

// POST /api/reviews/:id/approve
router.post('/:id/approve', verifyToken, requireRole(['manager','admin']), (req, res) => {
    const r = reviewQueue.find(x => x.id === req.params.id);
    if (!r) return res.status(404).json({ status: 'error', message: 'Not found' });
    r.status      = 'approved';
    r.reviewed_at = new Date().toISOString();
    r.reviewer    = req.user.name;
    r.notes       = req.body.notes || null;
    const { actionLog, ...review } = r;
    res.json({ status: 'ok', review });
});

// POST /api/reviews/:id/reject
router.post('/:id/reject', verifyToken, requireRole(['manager','admin']), (req, res) => {
    const r = reviewQueue.find(x => x.id === req.params.id);
    if (!r) return res.status(404).json({ status: 'error', message: 'Not found' });
    r.status      = 'rejected';
    r.reviewed_at = new Date().toISOString();
    r.reviewer    = req.user.name;
    r.notes       = req.body.notes || null;
    const { actionLog, ...review } = r;
    res.json({ status: 'ok', review });
});

// POST /api/reviews/:id/action  (escalate, comment, start_review, assign)
router.post('/:id/action', verifyToken, (req, res) => {
    const r = reviewQueue.find(x => x.id === req.params.id);
    if (!r) return res.status(404).json({ status: 'error', message: 'Not found' });
    const { action, comment } = req.body;
    if (action === 'start_review') {
        r.status = 'in_review';
    } else if (action === 'escalate') {
        r.status = 'escalated';
    }
    r.actionLog.push({
        id:        `${r.id}-${Date.now()}`,
        action,
        comment:   comment || null,
        timestamp: new Date().toISOString(),
        actor:     req.user?.name || 'system',
    });
    const { actionLog, ...review } = r;
    res.json({ status: 'ok', review });
});

module.exports = router;
