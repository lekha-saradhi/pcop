/**
 * dataStore.js
 * Loads all static demo data from server/data/*.json at startup.
 * Every route reads from this singleton — no database required.
 */

const path = require('path');
const fs   = require('fs');

const DATA_DIR = path.join(__dirname, '..', 'data');

function load(filename) {
    const fp = path.join(DATA_DIR, filename);
    if (!fs.existsSync(fp)) {
        console.warn(`[dataStore] WARNING: ${filename} not found at ${fp}`);
        return null;
    }
    const raw = fs.readFileSync(fp, 'utf8').replace(/^\uFEFF/, '');
return JSON.parse(raw);
}

// ── Load all static data ──────────────────────────────────────────────────────
const CUSTOMERS    = load('customers.json')    || [];
const SCORES       = load('scores.json')       || [];
const SIGNALS      = load('signals.json')      || [];
const TRANSACTIONS = load('transactions.json') || [];
const SURVIVAL     = load('survival.json')     || [];
const ACTION_PLANS = load('action_plans.json') || [];
const HERALD       = load('herald.json')       || [];
const PORTFOLIO    = load('portfolio.json')    || {};

// ── Build lookup maps for O(1) access ────────────────────────────────────────
const byId = (arr, key = 'customer_id') =>
    arr.reduce((m, item) => { m[item[key]] = item; return m; }, {});

const CUSTOMERS_MAP    = byId(CUSTOMERS);
const SCORES_MAP       = byId(SCORES);
const SIGNALS_MAP      = byId(SIGNALS);
const TRANSACTIONS_MAP = byId(TRANSACTIONS);
const SURVIVAL_MAP     = byId(SURVIVAL);
const PLANS_MAP        = byId(ACTION_PLANS);
const HERALD_MAP       = byId(HERALD);

console.log(`[dataStore] Loaded ${CUSTOMERS.length} customers, ${HERALD.length} HERALD records`);

// ── Live state (mutated by Kafka simulation) ──────────────────────────────────
const liveScoreOverrides  = {};
const liveSignalOverrides = {};

// ── Accessors ─────────────────────────────────────────────────────────────────
function getCustomers(filters = {}) {
    let list = [...CUSTOMERS];
    if (filters.segment)   list = list.filter(c => c.segment   === filters.segment);
    if (filters.risk_tier) list = list.filter(c => c.risk_tier === filters.risk_tier);
    if (filters.city)      list = list.filter(c => c.city      === filters.city);
    if (filters.archetype) list = list.filter(c => c.archetype === filters.archetype);
    if (filters.search) {
        const q = filters.search.toLowerCase();
        list = list.filter(c =>
            c.full_name.toLowerCase().includes(q) ||
            c.customer_id.toLowerCase().includes(q) ||
            (c.employer || '').toLowerCase().includes(q) ||
            (c.city     || '').toLowerCase().includes(q));
    }
    // sort
    if (filters.sort === 'score_desc') list.sort((a,b) => b.churn_score - a.churn_score);
    if (filters.sort === 'score_asc')  list.sort((a,b) => a.churn_score - b.churn_score);
    if (filters.sort === 'name')       list.sort((a,b) => a.full_name.localeCompare(b.full_name));
    return list;
}

function getCustomerById(id) { return CUSTOMERS_MAP[id] || null; }

function getScore(id) {
    const base = SCORES_MAP[id];
    if (!base) return null;
    return { ...base, ...(liveScoreOverrides[id] || {}) };
}

function getScores() {
    return SCORES.map(s => ({ ...s, ...(liveScoreOverrides[s.customer_id] || {}) }));
}

function getSignals(id) {
    const base  = SIGNALS_MAP[id]?.signals || [];
    const extra = liveSignalOverrides[id]  || [];
    return [...base, ...extra];
}

function getAllSignals() {
    return SIGNALS.map(s => ({
        customer_id: s.customer_id,
        alarm_count: s.alarm_count,
        signals: [...s.signals, ...(liveSignalOverrides[s.customer_id] || [])],
    }));
}

function getTransactions(id, limit = 60) {
    const all = TRANSACTIONS_MAP[id]?.transactions || [];
    return all.slice(-limit);
}

function getSurvival(id) { return SURVIVAL_MAP[id] || null; }
function getActionPlan(id) { return PLANS_MAP[id] || null; }
function getActionPlans() { return ACTION_PLANS; }
function getHerald(id) { return HERALD_MAP[id] || null; }
function getHeraldAll() { return HERALD; }
function getPortfolio() { return PORTFOLIO; }
function getPortfolioSummary() { return PORTFOLIO.summary || {}; }

// ── Enriched customer snapshot (combines all data sources) ───────────────────
function getCustomerSnapshot(id) {
    const customer = getCustomerById(id);
    if (!customer) return null;
    const score     = getScore(id);
    const signals   = getSignals(id);
    const plan      = getActionPlan(id);
    const survival  = getSurvival(id);
    const herald    = getHerald(id);
    return { customer, score, signals, plan, survival, herald };
}

// ── Live state mutators ───────────────────────────────────────────────────────
function applyScoreOverride(customerId, delta) {
    liveScoreOverrides[customerId] = {
        ...(liveScoreOverrides[customerId] || {}),
        ...delta,
        _live_updated_at: new Date().toISOString(),
    };
}

function applySignalOverride(customerId, signal) {
    if (!liveSignalOverrides[customerId]) liveSignalOverrides[customerId] = [];
    const idx = liveSignalOverrides[customerId]
        .findIndex(s => s.signal_type === signal.signal_type);
    if (idx >= 0) liveSignalOverrides[customerId][idx] = signal;
    else liveSignalOverrides[customerId].push(signal);
}

module.exports = {
    CUSTOMERS, SCORES, SIGNALS, TRANSACTIONS, SURVIVAL,
    ACTION_PLANS, HERALD, PORTFOLIO,
    CUSTOMERS_MAP, SCORES_MAP, SIGNALS_MAP, PLANS_MAP, HERALD_MAP,
    getCustomers, getCustomerById, getCustomerSnapshot,
    getScore, getScores,
    getSignals, getAllSignals,
    getTransactions, getSurvival,
    getActionPlan, getActionPlans,
    getHerald, getHeraldAll,
    getPortfolio, getPortfolioSummary,
    applyScoreOverride, applySignalOverride,
};
