const axios = require('axios');

const CHRONOS_API = process.env.CHRONOS_API_URL || 'http://localhost:8001';

const client = axios.create({ baseURL: CHRONOS_API, timeout: 10000 });

async function getScores(params = {}) {
    const res = await client.get('/scores', { params });
    return res.data;
}

async function getScore(customerId) {
    const res = await client.get(`/scores/${encodeURIComponent(customerId)}`);
    return res.data;
}

async function getReasonCodes(customerId) {
    const res = await client.get(`/scores/${encodeURIComponent(customerId)}/reason-codes`);
    return res.data;
}

async function getModelHealth() {
    const res = await client.get('/model-health');
    return res.data;
}

async function getSchedulerStatus() {
    const res = await client.get('/model-health/scheduler');
    return res.data;
}

async function getTokenSequence(customerId, params = {}) {
    const res = await client.get(`/scores/${encodeURIComponent(customerId)}/token-sequence`, { params });
    return res.data;
}

async function analyzeScore(customerId) {
    const res = await client.post(`/scores/${encodeURIComponent(customerId)}/analyze`);
    return res.data;
}

module.exports = {
    getScores, getScore, getReasonCodes, getModelHealth, getSchedulerStatus, getTokenSequence, analyzeScore, client,
};
