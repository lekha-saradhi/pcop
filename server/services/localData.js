/**
 * Local data service — reads directly from bank/data JSON files.
 * Replaces demoServerClient calls that require localhost:3001.
 */
const path = require('path');
const CHRONOS_API = process.env.CHRONOS_API_URL || 'http://localhost:8001';
const fs = require('fs');
const http = require('http');
const dataStore = require('./dataStore');

const DATA_DIR = path.join(__dirname, '..', '..', 'bank', 'data');
const CHRONOS_DATA_DIR = path.join(__dirname, '..', '..', 'chronos', 'data');

function readJson(file) {
    try {
        return JSON.parse(fs.readFileSync(path.join(DATA_DIR, file), 'utf8'));
    } catch { return []; }
}

function readChronosJson(file) {
    try {
        return JSON.parse(fs.readFileSync(path.join(CHRONOS_DATA_DIR, file), 'utf8'));
    } catch { return null; }
}

// lazy-loaded caches
let _customers = null;
let _accounts  = null;
let _events    = null;
let _crm       = null;
let _enrichment= null;
let _chronosScores = null;

function customers()  { return _customers  || (_customers  = readJson('customers.json')); }
function accounts()   { return _accounts   || (_accounts   = readJson('accounts.json')); }
function events()     { return _events     || (_events     = readJson('account_events.json')); }
function crmNotes()   { return _crm        || (_crm        = readJson('crm_notes.json')); }
function enrichment() { return _enrichment || (_enrichment = readJson('enrichment.json') || {}); }
// ── Chronos score cache ────────────────────────────────────────────────────
let _chronosScoreCache = {};
let _chronosCacheUpdating = false;

function refreshChronosCache() {
    if (_chronosCacheUpdating) return;
    _chronosCacheUpdating = true;
    // Fallback: load from scores_v2.json
    const fallback = readChronosJson('scores_v2.json');
    if (fallback) {
        for (const s of fallback) {
            if (!_chronosScoreCache[s.customer_id]) {
                _chronosScoreCache[s.customer_id] = s;
            }
        }
    }
    // Try the live Chronos API (non-blocking)
    http.get(`${CHRONOS_API}/scores?page_size=100`, (res) => {
        let body = '';
        res.on('data', (chunk) => body += chunk);
        res.on('end', () => {
            try {
                const data = JSON.parse(body);
                const list = data?.customers ?? data?.data ?? data;
                if (Array.isArray(list)) {
                    for (const s of list) {
                        if (!s.customer_id) continue;
                        const existing = _chronosScoreCache[s.customer_id];
                        if (!existing || (s.scored_at && s.scored_at > existing.scored_at)) {
                            _chronosScoreCache[s.customer_id] = s;
                        }
                    }
                }
            } catch {}
            _chronosCacheUpdating = false;
        });
    }).on('error', () => { _chronosCacheUpdating = false; });
}
refreshChronosCache();
setInterval(refreshChronosCache, 60000);

function enrichCustomer(c) {
    const hardcoded = dataStore.CHURN_SCORES[c.customer_id];
    const chronos = _chronosScoreCache[c.customer_id];
    const signals = dataStore.SIGNALS
        .filter(s => s.customer_id === c.customer_id && s.detected)
        .map(s => s.signal_type);
    const lifeEvts = dataStore.LIFE_EVENTS
        .filter(e => e.customer_id === c.customer_id)
        .map(e => e.event_type);

    const churn_score  = chronos?.final_score ?? hardcoded?.churn_score ?? 0.5;
    const risk_tier    = chronos?.risk_tier ?? hardcoded?.risk_tier ?? 'medium';
    const reason_codes = hardcoded?.reason_codes ?? [];

    return {
        ...c,
        churn_score,
        risk_tier,
        reason_codes,
        active_signals: signals,
        life_events: lifeEvts,
        recommended_action: reason_codes[0] ?? 'Monitor Account',
    };
}

function getCustomers(filters = {}) {
    let list = customers().map(enrichCustomer);
    if (filters.segment)   list = list.filter(c => c.segment === filters.segment);
    if (filters.risk_tier) list = list.filter(c => c.risk_tier === filters.risk_tier);
    if (filters.city)      list = list.filter(c => c.city === filters.city);
    return { status: 'ok', data: list };
}

function getCustomerById(id) {
    const c = customers().find(c => c.customer_id === id);
    if (!c) return null;
    const ec = enrichCustomer(c);
    const accs = accounts().filter(a => a.customer_id === id);
    const evts = events().filter(e => e.customer_id === id);
    const crm  = crmNotes().filter(n => n.customer_id === id);
    const enr  = enrichment()[id];
    const complaints = crm.filter(n => n.note_type === 'complaint');

    // Build engagement from enrichment data (enrichment.json is keyed by customer_id)
    const engagementDefaults = { days_since_last_login: 14, total_sessions_30d: 8, avg_session_duration_s: 210, most_used_feature: 'balance_check' };
    const engagement = enr?.engagement_summary || engagementDefaults;

    // MCC categories derived from actual account events
    const mccCategories = { salary: 'Salary Credit', grocery: 'Grocery / Supermarket', utility: 'Utility Bill', emi: 'Loan EMI', travel: 'Travel', fuel: 'Fuel', insurance: 'Insurance Premium', entertainment: 'Entertainment' };
    const top_mccs = evts.slice(0, 5).map(e => ({
        mcc_code: e.product_code || 'MISC',
        mcc_description: mccCategories[e.event_type] || e.metadata?.product_name || e.event_type,
        count: 1
    }));

    return {
        status: 'ok',
        data: {
            customer: ec,
            accounts: accs,
            score_history: dataStore.getScoreHistory(id, 90),
            active_signal_details: dataStore.SIGNALS.filter(s => s.customer_id === id && s.detected),
            life_event_details: dataStore.LIFE_EVENTS.filter(e => e.customer_id === id),
            engagement,
            // resolved is boolean in crm_notes.json — use resolved === false for unresolved
            crm_summary: {
                total_complaints: complaints.length,
                unresolved_count: complaints.filter(n => n.resolved === false).length,
                avg_resolution_days: complaints.filter(n => n.resolution_days != null).reduce((s, n) => s + n.resolution_days, 0) / (complaints.filter(n => n.resolution_days != null).length || 1),
                last_complaint_at: complaints.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))[0]?.created_at || null,
            },
            top_mccs,
            enrichment: enr ? { linkedin_employer: enr.linkedin_employer, linkedin_title: enr.linkedin_title, credit_score: enr.credit_score, credit_score_band: enr.credit_score_band, competitor_proximity: enr.competitor_proximity, news_risk_flag: enr.news_risk_flag, news_summary: enr.news_summary } : null,
        },
    };
}

function getPortfolioStats() {
    const list = customers().map(enrichCustomer);
    const counts = { critical: 0, high: 0, medium: 0, watch: 0, low: 0 };
    let scoreSum = 0;
    list.forEach(c => {
        if (counts[c.risk_tier] !== undefined) counts[c.risk_tier]++;
        scoreSum += c.churn_score;
    });
    return {
        status: 'ok',
        data: {
            total_customers: list.length,
            critical_count: counts.critical,
            high_count: counts.high,
            medium_count: counts.medium,
            watch_count: counts.watch,
            low_count: counts.low,
            avg_churn_score: list.length ? scoreSum / list.length : 0,
            outreach_sent_this_week: dataStore.outreachRecords.filter(r => {
                const d = new Date(r.dispatched_at);
                const week = Date.now() - 7 * 24 * 60 * 60 * 1000;
                return d.getTime() > week;
            }).length,
        },
    };
}

function getMarketSignals() {
    return {
        status: 'ok',
        data: [
            { signal_id: 'MS-001', signal_type: 'competitor_rate', description: 'HDFC Bank raised savings rate to 7.25%', severity: 'high', detected_at: new Date(Date.now() - 2 * 3600000).toISOString() },
            { signal_id: 'MS-002', signal_type: 'rbi_policy',      description: 'RBI repo rate unchanged at 6.50%', severity: 'info', detected_at: new Date(Date.now() - 24 * 3600000).toISOString() },
            { signal_id: 'MS-003', signal_type: 'fintech_promo',   description: 'Paytm Payments Bank running zero-fee promo', severity: 'medium', detected_at: new Date(Date.now() - 48 * 3600000).toISOString() },
        ],
    };
}

// ── Customer generation (manual add) ─────────────────────────────────────────

const SIGNAL_TEMPLATES_BY_SEGMENT = {
    'HNW': [
        { signal_type: 'location_city', confidence: 0.92, evidence: ['Recent location change detected'], cusum_value: 4.2, alarm_threshold: 3.5, method_used: 'CUSUM' },
        { signal_type: 'transaction_frequency', confidence: 0.85, evidence: ['Transaction frequency anomaly'], cusum_value: 3.8, alarm_threshold: 3.0, method_used: 'CUSUM' },
        { signal_type: 'salary_amount', confidence: 0.88, evidence: ['Salary credit pattern change'], cusum_value: 4.0, alarm_threshold: 3.0, method_used: 'CUSUM' },
    ],
    'Mass Affluent': [
        { signal_type: 'transaction_frequency', confidence: 0.78, evidence: ['Mild transaction frequency decline'], cusum_value: 3.2, alarm_threshold: 3.0, method_used: 'CUSUM' },
        { signal_type: 'digital_engagement', confidence: 0.74, evidence: ['App engagement down 30%'], cusum_value: 3.1, alarm_threshold: 3.0, method_used: 'CUSUM' },
    ],
    'Mass Market': [
        { signal_type: 'digital_engagement', confidence: 0.81, evidence: ['Feature views declining'], cusum_value: 3.5, alarm_threshold: 3.0, method_used: 'CUSUM' },
        { signal_type: 'complaint_sentiment', confidence: 0.72, evidence: ['Unresolved service feedback'], cusum_value: 2.8, alarm_threshold: 2.5, method_used: 'CUSUM' },
    ],
    'Digital Native': [
        { signal_type: 'digital_engagement', confidence: 0.79, evidence: ['Session frequency decreasing'], cusum_value: 3.3, alarm_threshold: 3.0, method_used: 'CUSUM' },
        { signal_type: 'transaction_frequency', confidence: 0.68, evidence: ['Transaction volume dropping'], cusum_value: 2.5, alarm_threshold: 2.5, method_used: 'CUSUM' },
    ],
};

const LIFE_EVENT_TEMPLATES_BY_SEGMENT = {
    'HNW': { event_type: 'job_change', confidence: 0.80, evidence: ['Employment change detected through transaction analysis'], source: 'rule_ml', risk_adjustment: 0.12 },
    'Mass Affluent': { event_type: 'relocation', confidence: 0.75, evidence: ['Location-based spending pattern shift'], source: 'rule_ml', risk_adjustment: 0.08 },
    'Mass Market': { event_type: 'salary_change', confidence: 0.70, evidence: ['Salary credit amount variation detected'], source: 'rule_ml', risk_adjustment: 0.06 },
    'Digital Native': { event_type: 'marriage', confidence: 0.72, evidence: ['Joint spending pattern detected'], source: 'rule_ml', risk_adjustment: -0.05 },
};

function generateCustomerProfile(data) {
    // Generate next customer ID
    const maxNum = customers()
        .map(c => parseInt(c.customer_id?.split('-')[1] || '0', 10))
        .reduce((a, b) => Math.max(a, b), 0);
    const customerId = `C-${String(maxNum + 1).padStart(8, '0')}`;

    // Build customer
    const customer = {
        customer_id: customerId,
        full_name: data.full_name,
        age: data.age || 30,
        city: data.city || 'Mumbai',
        segment: data.segment || 'Mass Market',
        tenure_years: data.tenure_years ?? 0,
        preferred_channel: data.preferred_channel || 'email',
        email: data.email,
        phone_mobile: data.phone_mobile || '',
        employer_name: data.employer_name || '',
        employment_type: data.employment_type || 'salaried',
        annual_income_band: data.annual_income_band || '5L_10L',
        email_opt_in: data.email_opt_in ?? true,
        sms_opt_in: data.sms_opt_in ?? true,
        push_opt_in: data.push_opt_in ?? true,
        call_opt_in: data.call_opt_in ?? false,
        kyc_status: 'pending',
        relationship_manager_id: null,
    };
    _customers.push(customer);
    _writeJson('customers.json', _customers);

    // Create default savings account
    accounts(); // ensure lazy-load
    const account = {
        account_id: `ACC-${customerId}-001`,
        customer_id: customerId,
        account_type: 'savings',
        balance: Math.round(Math.random() * 500000 + 50000),
        status: 'active',
        opened_date: new Date().toISOString().split('T')[0],
    };
    _accounts.push(account);
    _writeJson('accounts.json', _accounts);

    // Create enrichment entry
    enrichment(); // ensure lazy-load
    const creditBands = { 'above_25L': 800, '10L_25L': 750, '5L_10L': 700, 'below_5L': 650 };
    _enrichment[customerId] = {
        linkedin_employer: data.employer_name || '',
        linkedin_title: '',
        credit_score: creditBands[customer.annual_income_band] || 700,
        credit_score_band: customer.annual_income_band === 'above_25L' ? 'excellent' : customer.annual_income_band === '10L_25L' ? 'good' : customer.annual_income_band === '5L_10L' ? 'fair' : 'poor',
        competitor_proximity: Math.floor(Math.random() * 3),
        news_risk_flag: false,
        news_summary: 'No recent market news',
        captured_at: new Date().toISOString().split('T')[0],
        engagement_summary: {
            days_since_last_login: Math.floor(Math.random() * 7) + 1,
            total_sessions_30d: Math.floor(Math.random() * 15) + 5,
            avg_session_duration_s: Math.floor(Math.random() * 180) + 60,
            most_used_feature: 'balance_check',
        },
    };
    _writeJson('enrichment.json', _enrichment);

    // Generate CRM notes
    const notes = [
        {
            note_id: `CRM-${customerId}-001`,
            customer_id: customerId,
            note_type: 'onboarding',
            note_text: `Welcome ${customer.full_name}! Account opened successfully.`,
            sentiment_score: 0.85,
            issue_category: 'onboarding',
            resolved: true,
            channel: 'branch',
            resolution_days: 0,
            created_at: new Date().toISOString(),
        },
        {
            note_id: `CRM-${customerId}-002`,
            customer_id: customerId,
            note_type: 'check_in',
            note_text: `Initial check-in completed. Customer seems satisfied with onboarding.`,
            sentiment_score: 0.70,
            issue_category: 'general',
            resolved: true,
            channel: 'call',
            resolution_days: 1,
            created_at: new Date(Date.now() - 86400000).toISOString(),
        },
    ];
    crmNotes(); // ensure lazy-load
    _crm.push(...notes);
    _writeJson('crm_notes.json', _crm);

    // Generate account events
    const now = new Date();
    const accountEvents = [
        {
            event_id: `AE-${customerId}-001`,
            customer_id: customerId,
            event_type: 'account_opened',
            product_code: 'SAV001',
            event_date: now.toISOString().split('T')[0],
            metadata: { account_type: 'savings', product_name: 'Smart Savings Account' },
        },
    ];
    events(); // ensure lazy-load
    _events.push(...accountEvents);
    _writeJson('account_events.json', _events);

    // Generate signals
    const signalTmpls = SIGNAL_TEMPLATES_BY_SEGMENT[customer.segment] || SIGNAL_TEMPLATES_BY_SEGMENT['Mass Market'];
    const newSignals = signalTmpls.map((t, i) => ({
        customer_id: customerId,
        signal_type: t.signal_type,
        detected: true,
        confidence: t.confidence + (Math.random() * 0.1 - 0.05),
        evidence: t.evidence,
        cusum_value: t.cusum_value + (Math.random() * 0.5 - 0.25),
        alarm_threshold: t.alarm_threshold,
        method_used: t.method_used,
    }));
    dataStore.SIGNALS.push(...newSignals);

    // Generate life events
    const evtTmpl = LIFE_EVENT_TEMPLATES_BY_SEGMENT[customer.segment] || LIFE_EVENT_TEMPLATES_BY_SEGMENT['Mass Market'];
    dataStore.LIFE_EVENTS.push({
        customer_id: customerId,
        event_type: evtTmpl.event_type,
        confidence: evtTmpl.confidence,
        evidence: evtTmpl.evidence,
        source: evtTmpl.source,
        risk_adjustment: evtTmpl.risk_adjustment,
        detected_at: new Date().toISOString(),
    });

    // Set churn score
    dataStore.CHURN_SCORES[customerId] = {
        churn_score: 0.5,
        risk_tier: 'watch',
        reason_codes: ['New customer — monitoring initial behaviour'],
    };

    // Add to customer IDs
    dataStore.CUSTOMER_IDS.push(customerId);

    return enrichCustomer(customer);
}

function _writeJson(file, data) {
    try {
        fs.writeFileSync(path.join(DATA_DIR, file), JSON.stringify(data, null, 2), 'utf8');
    } catch (e) {
        console.error(`[localData] Failed to write ${file}:`, e.message);
    }
}

module.exports = { getCustomers, getCustomerById, getPortfolioStats, getMarketSignals, generateCustomerProfile };
