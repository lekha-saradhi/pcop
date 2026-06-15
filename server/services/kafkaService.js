/**
 * PCOP · Kafka Integration Service
 *
 * Connects to a Kafka broker and consumes banking event streams.
 * If the broker is unavailable, falls back to a deterministic simulation
 * that generates realistic banking events at regular intervals — so the
 * data pipeline stays demonstrable without a running Kafka cluster.
 *
 * Topics consumed:
 *   cbs.transactions       — Core Banking System payment events
 *   cbs.account_updates    — Balance / account status changes
 *   crm.customer_events    — CRM complaints, resolutions, notes
 *   risk.signal_detections — ARGUS-generated risk signals
 *   risk.score_updates     — ML score refreshes from FusionXV pipeline
 *   engagement.activity    — Digital channel engagement events
 */

const { Kafka, logLevel } = require('kafkajs');
const { EventEmitter } = require('events');
const dataStore = require('./dataStore');

// ── Configuration ────────────────────────────────────────────────────────────

const KAFKA_BROKERS = (process.env.KAFKA_BROKERS || 'localhost:9092').split(',');
const KAFKA_CLIENT_ID = process.env.KAFKA_CLIENT_ID || 'pcop-intelligence-server';
const KAFKA_GROUP_ID  = process.env.KAFKA_GROUP_ID  || 'pcop-consumers';

const TOPICS = {
    TRANSACTIONS:  'cbs.transactions',
    ACCOUNTS:      'cbs.account_updates',
    CRM:           'crm.customer_events',
    SIGNALS:       'risk.signal_detections',
    SCORES:        'risk.score_updates',
    ENGAGEMENT:    'engagement.activity',
};

// ── Event bus (for SSE push to frontend) ─────────────────────────────────────

const eventBus = new EventEmitter();
eventBus.setMaxListeners(100);

// ── Mutable live state (overlays the static dataStore) ───────────────────────

const liveState = {
    connected: false,
    mode: 'initialising',   // 'kafka' | 'simulation' | 'initialising'
    brokers: KAFKA_BROKERS,
    topicsConsumed: Object.values(TOPICS),
    messagesProcessed: 0,
    lastEventAt: null,
    recentEvents: [],        // ring buffer, last 50 events
    scoreOverrides: {},      // customerId → { churn_score, risk_tier, updated_at }
    signalOverrides: {},     // customerId → [signals]
    crmOverrides: {},        // customerId → [notes]
    transactionBuffer: {},   // customerId → [recent txns]
    accountOverrides: {},    // customerId → { balance_delta, updated_at }
};

function pushEvent(topic, customerId, payload, description) {
    const evt = {
        id: ++liveState.messagesProcessed,
        topic,
        customerId,
        description,
        payload,
        ts: new Date().toISOString(),
    };
    liveState.lastEventAt = evt.ts;
    liveState.recentEvents.unshift(evt);
    if (liveState.recentEvents.length > 50) liveState.recentEvents.pop();
    eventBus.emit('event', evt);
}

// ── Event handlers ────────────────────────────────────────────────────────────

function handleScoreUpdate({ customer_id, churn_score, risk_tier, model_version, reason }) {
    if (!customer_id) return;
    liveState.scoreOverrides[customer_id] = { churn_score, risk_tier, model_version, updated_at: new Date().toISOString() };
    dataStore.applyScoreOverride(customer_id, { final_score: churn_score, risk_tier });
    pushEvent(TOPICS.SCORES, customer_id,
        { churn_score, risk_tier, model_version },
        `Retention Risk Index updated → ${Math.round(churn_score * 100)}% (${risk_tier})`
    );
}

function handleSignalDetection({ customer_id, signal_type, confidence, cusum_value, alarm_threshold, method, evidence }) {
    if (!customer_id) return;
    const sig = { signal_type, confidence, cusum_value, alarm_threshold, method, detected: true, days_active: 1 };
    dataStore.applySignalOverride(customer_id, sig);
    if (!liveState.signalOverrides[customer_id]) liveState.signalOverrides[customer_id] = [];
    liveState.signalOverrides[customer_id].push(sig);
    pushEvent(TOPICS.SIGNALS, customer_id,
        { signal_type, confidence, cusum_value },
        `Signal detected: ${signal_type.replace(/_/g,' ')} · ${method} · conf ${Math.round(confidence*100)}%`
    );
}

function handleTransaction({ customer_id, amount, direction, category, channel, merchant_name }) {
    if (!customer_id) return;
    if (!liveState.transactionBuffer[customer_id]) liveState.transactionBuffer[customer_id] = [];
    const txn = { txn_date: new Date().toISOString().split('T')[0], amount, direction, category, channel, merchant_name, payment_ref: `TXN${Date.now()}` };
    liveState.transactionBuffer[customer_id].unshift(txn);
    if (liveState.transactionBuffer[customer_id].length > 30) liveState.transactionBuffer[customer_id].pop();
    pushEvent(TOPICS.TRANSACTIONS, customer_id,
        txn,
        `${direction === 'credit' ? '↑ Credit' : '↓ Debit'} ₹${amount.toLocaleString('en-IN')} · ${category} via ${channel}`
    );
}

function handleCrmEvent({ customer_id, note_type, note_text, channel, resolved }) {
    if (!customer_id) return;
    if (!liveState.crmOverrides[customer_id]) liveState.crmOverrides[customer_id] = [];
    const note = { customer_id, note_type, note_text, channel, resolved, created_at: new Date().toISOString() };
    liveState.crmOverrides[customer_id].unshift(note);
    pushEvent(TOPICS.CRM, customer_id, note,
        `CRM ${note_type}: "${note_text.slice(0, 60)}${note_text.length > 60 ? '…' : ''}"`
    );
}

function handleAccountUpdate({ customer_id, account_type, balance_delta, status }) {
    if (!customer_id) return;
    liveState.accountOverrides[customer_id] = { account_type, balance_delta, status, updated_at: new Date().toISOString() };
    pushEvent(TOPICS.ACCOUNTS, customer_id,
        { account_type, balance_delta, status },
        `Account update · ${account_type} · balance Δ ₹${balance_delta >= 0 ? '+' : ''}${balance_delta.toLocaleString('en-IN')}`
    );
}

// ── Message router ────────────────────────────────────────────────────────────

function routeMessage(topic, value) {
    try {
        const payload = JSON.parse(value.toString());
        switch (topic) {
            case TOPICS.SCORES:      return handleScoreUpdate(payload);
            case TOPICS.SIGNALS:     return handleSignalDetection(payload);
            case TOPICS.TRANSACTIONS:return handleTransaction(payload);
            case TOPICS.CRM:         return handleCrmEvent(payload);
            case TOPICS.ACCOUNTS:    return handleAccountUpdate(payload);
            case TOPICS.ENGAGEMENT:  return pushEvent(topic, payload.customer_id, payload, `Engagement update: ${payload.event_type || 'activity'}`);
        }
    } catch (err) {
        // Malformed event — ignore silently
    }
}

// ── Simulation mode ──────────────────────────────────────────────────────────

const SIM_CUSTOMERS = dataStore.CUSTOMERS.map(c => c.customer_id);
const SIM_SIGNAL_TYPES = ['transaction_frequency','salary_amount','digital_engagement','complaint_sentiment','stress_overdraft','location_city','lifecycle_mcc'];
const SIM_CATEGORIES   = ['grocery','utility','food','fuel','emi','shopping','travel'];
const SIM_CHANNELS     = ['upi','netbanking','pos','nach','atm'];
const SIM_MERCHANTS    = ['BigBasket','Swiggy','Zomato','BPCL','IRCTC','Flipkart','Amazon','PhonePe'];

let simInterval = null;
let simTick = 0;

function getRandomItem(arr) { return arr[Math.floor(Math.random() * arr.length)]; }
function pickCustomer() { return getRandomItem(SIM_CUSTOMERS); }

function runSimulationTick() {
    simTick++;
    const id    = pickCustomer();
    const score = dataStore.getScore(id);
    const cust  = dataStore.getCustomerById(id);
    if (!score || !cust) return;

    const roll = simTick % 6;

    if (roll === 0) {
        // Score refresh — small drift
        const delta    = (Math.random() - 0.5) * 0.03;
        const newScore = Math.max(0.05, Math.min(0.98, score.final_score + delta));
        let tier = 'NONE';
        if (newScore >= 0.80) tier = 'PRIORITY';
        else if (newScore >= 0.60) tier = 'ESCALATE';
        else if (newScore >= 0.40) tier = 'STANDARD';
        else if (newScore >= 0.20) tier = 'MONITOR';
        dataStore.applyScoreOverride(id, { final_score: +newScore.toFixed(4), risk_tier: tier });
        handleScoreUpdate({ customer_id: id, churn_score: +newScore.toFixed(4), risk_tier: tier, model_version: 'FusionXV2-sim', reason: null });

    } else if (roll === 1) {
        // Transaction event
        const isCredit = Math.random() < 0.25;
        const salary   = Math.round(cust.income / 12);
        const amount   = isCredit ? salary : Math.round(500 + Math.random() * 8000);
        handleTransaction({ customer_id: id, amount, direction: isCredit ? 'credit' : 'debit', category: isCredit ? 'salary' : getRandomItem(SIM_CATEGORIES), channel: getRandomItem(SIM_CHANNELS), merchant_name: getRandomItem(SIM_MERCHANTS) });

    } else if (roll === 2 && score.final_score > 0.55) {
        // Signal detection for high-risk customers
        const sigType = getRandomItem(SIM_SIGNAL_TYPES);
        const threshold = sigType === 'stress_overdraft' ? 2.5 : sigType === 'location_city' ? 3.5 : 3.0;
        const cusumValue = threshold + Math.random() * 2;
        handleSignalDetection({ customer_id: id, signal_type: sigType, confidence: +(0.65 + Math.random() * 0.3).toFixed(2), cusum_value: +cusumValue.toFixed(2), alarm_threshold: threshold, method: getRandomItem(['CUSUM','BOCPD','SPRT']), evidence: `Simulated drift detected in ${sigType.replace(/_/g,' ')}` });

    } else if (roll === 3) {
        // Account balance update
        const delta = Math.round((Math.random() - 0.4) * 15000);
        handleAccountUpdate({ customer_id: id, account_type: getRandomItem(['savings','current','fd']), balance_delta: delta, status: 'active' });

    } else if (roll === 4 && score.final_score > 0.60) {
        // CRM complaint for high-risk
        const complaints = [
            'Customer called about unexpected fee deduction on savings account.',
            'Delay in NEFT transfer processing — customer escalated.',
            'Net banking login issues persisted for 3 days.',
            'Request for interest rate review on personal loan.',
            'Customer reported missing transaction in statement.',
        ];
        handleCrmEvent({ customer_id: id, note_type: 'complaint', note_text: getRandomItem(complaints), channel: getRandomItem(['call','email','branch']), resolved: false });
    }
    // roll === 5: no event (quiet period)
}

function startSimulation() {
    liveState.mode = 'simulation';
    liveState.connected = false;
    console.log('[Kafka] Simulation mode active — generating banking events every 8s');
    simInterval = setInterval(runSimulationTick, 8000);
    // Fire an immediate tick so the feed isn't empty on startup
    setTimeout(runSimulationTick, 1500);
    setTimeout(runSimulationTick, 3000);
    setTimeout(runSimulationTick, 4500);
}

// ── Kafka consumer ────────────────────────────────────────────────────────────

let kafkaConsumer = null;
let kafkaProducer = null;

async function startKafka() {
    const kafka = new Kafka({
        clientId: KAFKA_CLIENT_ID,
        brokers: KAFKA_BROKERS,
        logLevel: logLevel.ERROR,
        retry: { retries: 3, initialRetryTime: 300 },
        connectionTimeout: 3000,
        requestTimeout: 5000,
    });

    kafkaConsumer = kafka.consumer({ groupId: KAFKA_GROUP_ID });
    kafkaProducer = kafka.producer();

    await kafkaConsumer.connect();
    await kafkaProducer.connect();

    // Subscribe to all topics
    for (const topic of Object.values(TOPICS)) {
        await kafkaConsumer.subscribe({ topic, fromBeginning: false });
    }

    await kafkaConsumer.run({
        eachMessage: async ({ topic, partition, message }) => {
            routeMessage(topic, message.value);
        },
    });

    liveState.connected = true;
    liveState.mode = 'kafka';
    console.log(`[Kafka] Connected to ${KAFKA_BROKERS.join(', ')} — consuming ${Object.values(TOPICS).length} topics`);
}

// ── Public API ───────────────────────────────────────────────────────────────

async function init() {
    try {
        await startKafka();
    } catch (err) {
        console.log(`[Kafka] Broker unreachable (${KAFKA_BROKERS.join(',')}) — switching to simulation mode`);
        startSimulation();
    }
}

async function publish(topic, key, value) {
    if (!kafkaProducer || liveState.mode !== 'kafka') {
        // In simulation mode, route directly
        routeMessage(topic, Buffer.from(JSON.stringify(value)));
        return;
    }
    await kafkaProducer.send({ topic, messages: [{ key, value: JSON.stringify(value) }] });
}

async function shutdown() {
    if (simInterval) clearInterval(simInterval);
    try { await kafkaConsumer?.disconnect(); } catch (_) {}
    try { await kafkaProducer?.disconnect(); } catch (_) {}
}

function getStatus() {
    return {
        mode: liveState.mode,
        connected: liveState.connected,
        brokers: liveState.brokers,
        topicsConsumed: liveState.topicsConsumed,
        messagesProcessed: liveState.messagesProcessed,
        lastEventAt: liveState.lastEventAt,
        recentEvents: liveState.recentEvents.slice(0, 20),
        liveOverrides: {
            scores:       Object.keys(liveState.scoreOverrides).length,
            signals:      Object.keys(liveState.signalOverrides).length,
            transactions: Object.keys(liveState.transactionBuffer).length,
            crm:          Object.keys(liveState.crmOverrides).length,
        },
    };
}

function getLiveState() { return liveState; }
function getEventBus()  { return eventBus; }

module.exports = { init, publish, shutdown, getStatus, getLiveState, getEventBus, TOPICS };
