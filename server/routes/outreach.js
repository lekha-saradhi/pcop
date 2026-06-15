/**
 * /api/outreach  — HERALD content generation + campaign and outreach record endpoints
 * POST /api/outreach/generate calls NVIDIA DeepSeek V4 Pro live to produce email/SMS/push content.
 */
const router = require('express').Router();
const https  = require('https');
const { verifyToken } = require('../middleware/auth');
const ds = require('../services/dataStore');

// ── NVIDIA DeepSeek helper ─────────────────────────────────────────────────────
const NVIDIA_ENDPOINT = process.env.NVIDIA_ENDPOINT ||
    'https://integrate.api.nvidia.com/v1/chat/completions';
const NVIDIA_KEY   = process.env.NVIDIA_API_KEY || '';
const NVIDIA_MODEL = process.env.NVIDIA_MODEL   || 'deepseek-ai/deepseek-v4-pro';

function callNvidia(messages, maxTokens = 600) {
    return new Promise((resolve, reject) => {
        const body = JSON.stringify({ model: NVIDIA_MODEL, messages, max_tokens: maxTokens, temperature: 0.7 });
        const url  = new URL(NVIDIA_ENDPOINT);
        const opts = {
            hostname: url.hostname,
            path:     url.pathname + url.search,
            method:   'POST',
            headers:  {
                'Content-Type':   'application/json',
                'Authorization':  `Bearer ${NVIDIA_KEY}`,
                'Content-Length': Buffer.byteLength(body),
            },
        };
        const req = https.request(opts, (r) => {
            let data = '';
            r.on('data', d => { data += d; });
            r.on('end', () => {
                try { resolve(JSON.parse(data)); }
                catch(e) { reject(new Error(`JSON parse error: ${data.slice(0,200)}`)); }
            });
        });
        req.on('error', reject);
        req.write(body);
        req.end();
    });
}

// ── In-memory outreach log (seeded from herald data) ─────────────────────────
const outreachLog = ds.HERALD.map((h, i) => ({
    id:              `OR-${String(i+1).padStart(4,'0')}`,
    customer_id:     h.customer_id,
    channel:         h.risk_tier === 'PRIORITY' ? 'phone' :
                     h.risk_tier === 'ESCALATE' ? 'email' : 'sms',
    risk_tier:       h.risk_tier,
    status:          ['sent','delivered','opened','clicked'][Math.floor(Math.random()*4)],
    offer_code:      ds.PLANS_MAP[h.customer_id]?.offer_code || 'NONE',
    dispatched_at:   new Date(Date.now() - Math.random()*7*86400_000).toISOString(),
    content_preview: h.email?.body?.slice(0, 120) + '...',
}));

// ── 3 static campaigns ───────────────────────────────────────────────────────
const CAMPAIGNS = [
    { id: 'C001', name: 'Q1 Retention Drive',   status: 'active',    channel: 'email', customers: 18, opens: 11, conversions: 4 },
    { id: 'C002', name: 'High-Risk SMS Blitz',   status: 'active',    channel: 'sms',   customers: 10, opens: 7,  conversions: 2 },
    { id: 'C003', name: 'VIP Loyalty Programme', status: 'completed', channel: 'phone', customers: 8,  opens: 8,  conversions: 6 },
];

// ── Routes ────────────────────────────────────────────────────────────────────

// GET /api/outreach/campaigns
router.get('/campaigns', verifyToken, (req, res) => {
    res.json({ status: 'ok', campaigns: CAMPAIGNS });
});

// GET /api/outreach
router.get('/', verifyToken, (req, res) => {
    const { customer_id, status, channel, page = 1, limit = 20 } = req.query;
    let list = [...outreachLog];
    if (customer_id) list = list.filter(o => o.customer_id === customer_id);
    if (status)      list = list.filter(o => o.status      === status);
    if (channel)     list = list.filter(o => o.channel     === channel);
    const p = parseInt(page), l = parseInt(limit);
    res.json({ status: 'ok', total: list.length, page: p, limit: l, records: list.slice((p-1)*l, p*l) });
});

// GET /api/outreach/:id
router.get('/:id', verifyToken, (req, res) => {
    const record = outreachLog.find(o => o.id === req.params.id);
    if (!record) return res.status(404).json({ status: 'error', message: 'Not found' });
    res.json({ status: 'ok', data: { ...record, full_content: ds.getHerald(record.customer_id) } });
});

// POST /api/outreach/generate  — HERALD: live NVIDIA DeepSeek V4 Pro content generation
router.post('/generate', verifyToken, async (req, res) => {
    const { customer_id } = req.body;
    if (!customer_id)
        return res.status(400).json({ status: 'error', message: 'customer_id required' });

    const snap = ds.getCustomerSnapshot(customer_id);
    if (!snap)
        return res.status(404).json({ status: 'error', message: 'Customer not found' });

    const { customer: c, score, signals, plan } = snap;

    // If no NVIDIA key, fall back to pre-generated static HERALD content
    if (!NVIDIA_KEY) {
        const cached = ds.getHerald(customer_id);
        if (cached) return res.json({ status: 'ok', source: 'cached', herald: cached });
        return res.status(404).json({ status: 'error', message: 'No HERALD content and NVIDIA API key not configured' });
    }

    const firstName  = c.first_name || c.full_name.split(' ')[0];
    const tier       = score?.risk_tier || c.risk_tier;
    const offerText  = plan?.offer_display || plan?.offer_code?.replace(/_/g,' ') || 'a personalised banking offer';
    const channel    = plan?.channel || 'email';

    // Rich signal descriptions — give the LLM context not just labels
    const signalDetails = signals.length > 0
        ? signals.map(s => {
            const desc = {
                balance_decline:      'account balance has been steadily declining over the past weeks',
                inactivity:           `no transactions for ${c.inactivity_days} days — account appears dormant`,
                login_drop:           `app logins dropped to ${c.app_logins_30d} in the last 30 days`,
                salary_miss:          `salary credits have stopped — only ${c.salary_credit_count} credits in last 3 months`,
                complaint_spike:      `${c.complaint_count} service complaint(s) filed recently`,
                digital_ratio_drop:   `digital channel usage has dropped to ${Math.round(c.digital_ratio*100)}%`,
                competitor_transfer:  'large outward transfers detected to competitor bank accounts',
                txn_frequency_drop:   `transaction frequency dropped to ${c.txn_freq_90d} in last 90 days`,
                atm_spike:            `unusual ATM withdrawal activity — ${c.atm_withdrawals_90d} withdrawals in 90 days`,
            }[s.signal_type] || s.signal_type.replace(/_/g,' ');
            return `  • ${s.signal_type.replace(/_/g,' ')} (${s.method}, confidence ${Math.round(s.confidence*100)}%, active ${s.days_active} days): ${desc}`;
          }).join('\n')
        : '  • No active behavioural signals detected';

    const lifeEventContext = c.life_event
        ? `LIFE EVENT DETECTED: ${c.life_event.replace(/_/g,' ')} — ${c.life_event_desc || 'significant life transition detected'}. Acknowledge this sensitively in your message without being intrusive.`
        : '';

    const urgencyInstruction = tier === 'PRIORITY'
        ? 'URGENCY: HIGH. This customer shows multiple strong distress signals. Write with genuine warmth and urgency. Make them feel valued and heard. The relationship manager wants to personally reconnect.'
        : tier === 'ESCALATE'
        ? 'URGENCY: MEDIUM. Customer engagement is declining. Write a reconnection message that reminds them of the value PCOP provides and presents the offer as a reward for their loyalty.'
        : 'URGENCY: LOW. Customer is stable but engagement could improve. Write an appreciative, value-adding message.';

    const systemPrompt = `You are HERALD, the AI personalisation engine for PCOP's customer retention platform.
Your job is to write hyper-personalised, empathetic, compliance-safe outreach content for at-risk customers.

STRICT RULES:
1. NEVER use the words: churn, risk, score, monitored, flagged, alert, detected, warning, attrition
2. NEVER make specific interest rate or return promises
3. NEVER sound like a generic marketing email — every sentence must feel written specifically for this person
4. Address customer by their first name throughout
5. Reference their specific situation (tenure, city, life event, behaviour patterns) naturally
6. The tone should feel like a caring relationship manager reaching out personally, not a corporate blast
7. All content must be complete — no ellipsis (...) as placeholder, no truncation
8. Sign off warmly as PCOP`;

    const userPrompt = `Write personalised retention outreach for the following PCOP customer.
Return ONLY a valid raw JSON object. No markdown fences, no explanation, no extra text.

═══════════════════════════════════════════
CUSTOMER INTELLIGENCE BRIEF
═══════════════════════════════════════════

IDENTITY:
- Full name: ${c.full_name} | First name: ${firstName}
- Customer ID: ${c.customer_id}
- Age: ${c.age} | City: ${c.city} | Segment: ${c.segment}
- Employer: ${c.employer}
- Relationship Manager: ${c.relationship_manager}

BANKING RELATIONSHIP:
- Tenure: ${c.tenure_months} months with PCOP
- Account balance: ₹${c.balance?.toLocaleString('en-IN')}
- Annual income: ₹${c.income?.toLocaleString('en-IN')}
- Products held: ${c.product_count} (cross-sell opportunity if low)
- NPS score: ${c.nps}/10 ${c.nps < 4 ? '(very dissatisfied — handle with care)' : c.nps < 7 ? '(neutral)' : '(satisfied)'}

RECENT BEHAVIOUR (last 30-90 days):
- Days since last transaction: ${c.inactivity_days}
- App logins last 30 days: ${c.app_logins_30d}
- Transaction frequency (90d): ${c.txn_freq_90d}
- Digital channel usage: ${Math.round(c.digital_ratio*100)}%
- Salary credits (last 3 months): ${c.salary_credit_count}
- Complaints filed: ${c.complaint_count}

ACTIVE BEHAVIOURAL SIGNALS FROM ARGUS:
${signalDetails}

${lifeEventContext ? lifeEventContext + '\n' : ''}
RECOMMENDED ACTION: ${plan?.action || channel.toUpperCase()} via ${channel}
OFFER TO PRESENT: ${offerText}
CONTENT STRATEGY: ${plan?.content_strategy || 'empathy_lead'}
TONE MODIFIERS: ${plan?.tone_modifiers?.join(', ') || 'professional, warm, empathetic'}

${urgencyInstruction}

═══════════════════════════════════════════
WRITING INSTRUCTIONS
═══════════════════════════════════════════

EMAIL (150-200 words):
- Subject: Compelling, personal, 8-12 words — make ${firstName} want to open it
- Body:
  Paragraph 1 (2-3 sentences): Warm personal opening. Reference their ${c.tenure_months}-month relationship. Make them feel valued.
  Paragraph 2 (2-3 sentences): Gently acknowledge their situation using the behavioural context WITHOUT mentioning any monitoring. Frame it as "we noticed we haven't connected recently" or similar.
  ${lifeEventContext ? 'Paragraph 3 (1-2 sentences): Sensitively acknowledge the life event and how PCOP can support them through it.' : ''}
  Paragraph ${lifeEventContext ? '4' : '3'} (2-3 sentences): Introduce the offer (${offerText}) as a reward/exclusive benefit for loyal customers like them.
  Paragraph ${lifeEventContext ? '5' : '4'} (1-2 sentences): Clear, friendly call to action — invite them to call, visit the branch in ${c.city}, or reply to this email.
  Sign off: Warm, from their RM ${c.relationship_manager} / PCOP team.

SMS (under 155 characters total including opt-out):
- Personal, conversational, creates curiosity or urgency without being pushy
- Must end with: Reply STOP to opt out

PUSH NOTIFICATION:
- Title: 5-8 words, personal to ${firstName}, creates curiosity
- Body: 1-2 short punchy sentences, under 90 characters, makes them want to tap

═══════════════════════════════════════════

Return this exact JSON structure with all fields filled with real written content:
{"email":{"subject":"<write subject here>","body":"<write full email body here>","compliance_status":"APPROVED","word_count":0},"sms":{"body":"<write sms here>","compliance_status":"APPROVED","char_count":0},"push":{"title":"<write push title here>","body":"<write push body here>","compliance_status":"APPROVED"}}

Fill word_count and char_count with actual counts. Return only the JSON, nothing else.`;

    try {
        console.log(`[HERALD] Generating live content for ${customer_id} via NVIDIA DeepSeek V4 Pro`);
        const resp = await callNvidia([
            { role: 'system', content: systemPrompt },
            { role: 'user',   content: userPrompt },
        ], 1200);

        const raw = resp?.choices?.[0]?.message?.content || '';

        let generated;
        try {
            // Strip any accidental markdown fences
            const cleaned = raw.replace(/```json\n?/g,'').replace(/```\n?/g,'').trim();
            generated = JSON.parse(cleaned);
        } catch {
            console.error('[HERALD] JSON parse failed, raw:', raw.slice(0, 300));
            const cached = ds.getHerald(customer_id);
            if (cached) return res.json({ status: 'ok', source: 'cached_fallback', herald: cached, plan });
            return res.status(500).json({ status: 'error', message: 'DeepSeek returned malformed JSON and no cached content exists.' });
        }

        // Recompute counts from actual content (model often returns 0)
        if (generated.email?.body) {
            generated.email.word_count = generated.email.body.trim().split(/\s+/).length;
        }
        if (generated.sms?.body) {
            generated.sms.char_count = generated.sms.body.length;
        }

        const herald = {
            customer_id,
            risk_tier: tier,
            generated_at: new Date().toISOString(),
            source: 'nvidia_deepseek_v4_pro',
            ...generated,
        };

        res.json({ status: 'ok', source: 'nvidia', herald, plan });

    } catch (err) {
        console.error('[HERALD] NVIDIA call failed:', err.message);
        // Graceful fallback to cached static content
        const cached = ds.getHerald(customer_id);
        if (cached) {
            return res.json({ status: 'ok', source: 'cached_fallback', herald: cached, plan });
        }
        res.status(500).json({ status: 'error', message: err.message });
    }
});

module.exports = router;
