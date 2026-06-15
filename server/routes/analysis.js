const router  = require('express').Router();
const https   = require('https');
const { verifyToken } = require('../middleware/auth');
const ds = require('../services/dataStore');

const NVIDIA_ENDPOINT = process.env.NVIDIA_ENDPOINT ||
    'https://integrate.api.nvidia.com/v1/chat/completions';
const NVIDIA_KEY   = process.env.NVIDIA_API_KEY  || '';
const NVIDIA_MODEL = process.env.NVIDIA_MODEL    || 'deepseek-ai/deepseek-v4-pro';

function callNvidia(messages) {
    return new Promise((resolve, reject) => {
        const body = JSON.stringify({ model: NVIDIA_MODEL, messages, max_tokens: 400, temperature: 0.4 });
        const url  = new URL(NVIDIA_ENDPOINT);
        const opts = {
            hostname: url.hostname,
            path:     url.pathname + url.search,
            method:   'POST',
            headers:  { 'Content-Type': 'application/json', 'Authorization': `Bearer ${NVIDIA_KEY}`,
                        'Content-Length': Buffer.byteLength(body) },
        };
        const req = https.request(opts, (r) => {
            let data = '';
            r.on('data', d => { data += d; });
            r.on('end', () => { try { resolve(JSON.parse(data)); } catch(e){ reject(e); } });
        });
        req.on('error', reject);
        req.write(body); req.end();
    });
}

// POST /api/analysis/analyze
router.post('/analyze', verifyToken, async (req, res) => {
    const { customer_id } = req.body;
    if (!customer_id)
        return res.status(400).json({ status: 'error', message: 'customer_id required' });

    const snap = ds.getCustomerSnapshot(customer_id);
    if (!snap) return res.status(404).json({ status: 'error', message: 'Not found' });

    const { customer, score, signals } = snap;
    const sysPrompt = (
        'You are a senior bank risk analyst. Write a concise (max 180 words) ' +
        'risk assessment. Cover: (1) key churn drivers, (2) recommended intervention, ' +
        '(3) urgency. Be specific and cite the signals provided.'
    );
    const userPrompt =
        `Customer: ${customer.full_name} | ${customer.segment} | ${customer.tenure_months}mo tenure\n` +
        `Churn score: ${score.final_score} (${score.risk_tier}) | P(churn<30d): ${score.p30}\n` +
        `Signals: ${signals.map(s=>s.signal_type).join(', ')||'none'}\n` +
        `Life event: ${customer.life_event||'none'} | Balance: ₹${customer.balance?.toLocaleString('en-IN')}\n` +
        `Inactivity: ${customer.inactivity_days}d | Complaints: ${customer.complaint_count}`;

    if (!NVIDIA_KEY) {
        return res.json({
            status: 'ok', source: 'mock',
            analysis:
                `**Risk Assessment — ${customer.full_name}**\n\n` +
                `Score: ${score.final_score} (${score.risk_tier}). ` +
                `Primary drivers: ${signals.slice(0,3).map(s=>s.signal_type.replace(/_/g,' ')).join(', ')||'inactivity streak'}. ` +
                `${customer.life_event ? `Life event detected: ${customer.life_event}. ` : ''}` +
                `Recommend ${score.risk_tier==='PRIORITY'?'immediate RM call':'targeted email within 24h'}.`,
        });
    }

    try {
        const resp = await callNvidia([
            { role: 'system', content: sysPrompt },
            { role: 'user',   content: userPrompt },
        ]);
        const text = resp?.choices?.[0]?.message?.content || 'Analysis unavailable.';
        res.json({ status: 'ok', analysis: text, source: 'nvidia' });
    } catch (err) {
        res.status(500).json({ status: 'error', message: err.message });
    }
});

module.exports = router;
