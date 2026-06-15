const router = require('express').Router();
const { verifyToken } = require('../middleware/auth');
const ds = require('../services/dataStore');

// GET /api/customers  — list with optional filters
router.get('/', verifyToken, (req, res) => {
    const { segment, risk_tier, city, archetype, search, sort,
            page = 1, limit = 100 } = req.query;
    const list  = ds.getCustomers({ segment, risk_tier, city, archetype, search, sort });
    const total = list.length;
    const p = parseInt(page), l = Math.min(parseInt(limit), 200);
    const items = list.slice((p - 1) * l, p * l);
    res.json({ status: 'ok', total, page: p, limit: l, customers: items });
});

// GET /api/customers/:id  — full snapshot
router.get('/:id', verifyToken, (req, res) => {
    const snap = ds.getCustomerSnapshot(req.params.id);
    if (!snap) return res.status(404).json({ status: 'error', message: 'Customer not found' });
    res.json({ status: 'ok', ...snap });
});

// GET /api/customers/:id/signals
router.get('/:id/signals', verifyToken, (req, res) => {
    if (!ds.getCustomerById(req.params.id))
        return res.status(404).json({ status: 'error', message: 'Not found' });
    const signals = ds.getSignals(req.params.id);
    res.json({ status: 'ok', customer_id: req.params.id,
               signals, alarm_count: signals.length });
});

// GET /api/customers/:id/transactions
router.get('/:id/transactions', verifyToken, (req, res) => {
    if (!ds.getCustomerById(req.params.id))
        return res.status(404).json({ status: 'error', message: 'Not found' });
    const txns = ds.getTransactions(req.params.id, parseInt(req.query.limit) || 60);
    res.json({ status: 'ok', customer_id: req.params.id,
               transactions: txns, count: txns.length });
});

// GET /api/customers/:id/survival
router.get('/:id/survival', verifyToken, (req, res) => {
    const data = ds.getSurvival(req.params.id);
    if (!data) return res.status(404).json({ status: 'error', message: 'Not found' });
    res.json({ status: 'ok', ...data });
});

// GET /api/customers/:id/score
router.get('/:id/score', verifyToken, (req, res) => {
    const score = ds.getScore(req.params.id);
    if (!score) return res.status(404).json({ status: 'error', message: 'Not found' });
    res.json({ status: 'ok', ...score });
});

// GET /api/customers/:id/plan
router.get('/:id/plan', verifyToken, (req, res) => {
    const plan = ds.getActionPlan(req.params.id);
    if (!plan) return res.status(404).json({ status: 'error', message: 'Not found' });
    res.json({ status: 'ok', ...plan });
});

// GET /api/customers/:id/herald
router.get('/:id/herald', verifyToken, (req, res) => {
    const herald = ds.getHerald(req.params.id);
    if (!herald) return res.status(404).json({ status: 'error', message: 'No content generated' });
    res.json({ status: 'ok', ...herald });
});

// POST /api/customers  — create a new customer (stub: returns a synthetic record)
router.post('/', verifyToken, (req, res) => {
    const body = req.body || {};
    if (!body.full_name) return res.status(400).json({ status: 'error', message: 'full_name is required' });
    const now = Date.now();
    const customer_id = `CUST-NEW-${now.toString(36).toUpperCase()}`;
    const newCustomer = {
        customer_id,
        full_name:            body.full_name,
        first_name:           body.full_name.split(' ')[0],
        email:                body.email || '',
        phone:                body.phone_mobile || '',
        age:                  body.age || 30,
        income:               500000,
        tenure_months:        Math.round((body.tenure_years || 0) * 12),
        segment:              body.segment || 'Mass Market',
        archetype:            'healthy_active',
        city:                 body.city || 'Mumbai',
        city_tier:            2,
        product_count:        1,
        employer:             body.employer_name || '',
        relationship_manager: 'System',
        preferred_channel:    body.preferred_channel || 'email',
        email_opt_in:         body.email_opt_in ?? true,
        sms_opt_in:           body.sms_opt_in ?? true,
        txn_freq_90d:         0,
        avg_txn_amount:       0,
        inactivity_days:      0,
        digital_ratio:        0.5,
        complaint_count:      0,
        atm_withdrawals_90d:  0,
        app_logins_30d:       0,
        balance:              10000,
        salary_credit_count:  0,
        nps:                  7,
        risk_tier:            'MONITOR',
        churn_score:          0.15,
        life_event:           null,
        life_event_desc:      null,
    };
    res.status(201).json({ status: 'ok', data: newCustomer });
});

module.exports = router;
