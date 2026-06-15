const demoServerClient = require('./demoServerClient');

const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function runAnalysis(customerId) {
    // Fetch customer snapshot, which contains the pre-seeded correct result
    const snapshotData = await demoServerClient.getCustomerById(customerId);
    if (!snapshotData || !snapshotData.customer) {
        throw new Error(`Customer ${customerId} not found`);
    }

    const customer = snapshotData.customer;

    // Pipeline stages: simulate sequential Delays
    // 1. Fetching signals
    await delay(800);
    // 2. Running CUSUM & BOCPD detection
    await delay(1200);
    // 3. Scoring with XGBoost + Transformer
    await delay(1500);
    // 4. LangGraph orchestration
    await delay(1000);
    // 5. Generating action plan
    await delay(600);

    // Hardcode reason codes based on risk tier or signals for demo
    let reason_codes = [];
    if (customer.risk_tier === 'critical') {
        reason_codes = [
            'Significant drop in engagement over 30 days',
            'Recent high-stress lifecycle events detected',
            'Unresolved CRM complaints affecting sentiment'
        ];
    } else if (customer.risk_tier === 'high') {
        reason_codes = [
            'Salary drift detected',
            'Decrease in account balance velocity',
            'Recent competitor inquiry'
        ];
    } else {
        reason_codes = [
            'Normal transaction patterns',
            'Stable engagement',
            'No negative CRM sentiment'
        ];
    }

    // Pre-seeded recommended action
    let recommended_action = null;
    if (customer.recommended_action) {
        // Attempt to parse if string, or create a mock object
        recommended_action = {
            channel: customer.preferred_channel || 'email',
            offer_code: 'RET-24-SPECIAL',
            timing: 'next_24_hours',
            rationale: 'Customer prefers this channel and has high churn risk.'
        };
    } else {
        // Demo defaults for recommended_action
        recommended_action = {
            channel: customer.preferred_channel || 'email',
            offer_code: 'RM-CONSULT',
            timing: 'next_business_day',
            rationale: 'Proactive outreach to ensure satisfaction.'
        };
    }

    const result = {
        customer_id: customer.customer_id,
        churn_score: customer.churn_score,
        risk_tier: customer.risk_tier,
        active_signals: customer.active_signals || [],
        life_events: (customer.life_events || []).map(event => ({
            event_type: event,
            confidence: 0.95,
            evidence: ['Inferred from recent transaction patterns']
        })),
        recommended_action,
        reason_codes,
        analysis_duration_ms: 800 + 1200 + 1500 + 1000 + 600,
        model_version: 'xgb-v2.1 + transformer-v1.4',
        scored_at: new Date().toISOString()
    };

    return result;
}

module.exports = {
    runAnalysis
};
