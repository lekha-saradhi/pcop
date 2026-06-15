const Anthropic = require('@anthropic-ai/sdk');
const config = require('../config');

// Constants for fallback mode
const FALLBACK_MESSAGES = {
    critical: "Dear Customer,\n\nWe noticed some recent changes in your account activity. We value our relationship with you and would like to offer a complimentary review of your portfolio to ensure we are meeting all your financial needs. Please let us know a good time to connect.\n\nWarm regards,\nYour Bank Team",
    high: "Hi there,\nIt looks like your needs might be evolving. Let's schedule a quick call to ensure you're getting the best rates on your accounts.\nBest,\nYour Bank",
    default: "Hello,\nWe hope you're enjoying your experience with us. Discover our latest offers on the app!\nThanks,\nYour Bank"
};

const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function streamFallback(message, res) {
    const chars = message.split('');

    for (let i = 0; i < chars.length; i++) {
        // Send one event per chunk to simulate token streaming
        res.write(`data: ${JSON.stringify({ type: 'token', content: chars[i] })}\n\n`);
        await delay(15);
    }

    res.write(`data: ${JSON.stringify({ type: 'done', full_content: message })}\n\n`);
    res.end();
}

async function generateOutreach(customerData, analysisResult, channel, res) {
    const tier = analysisResult.risk_tier || 'medium';

    if (config.useClaudeFallback) {
        console.log('[ClaudeService] Using fallback mode for outreach generation');
        const fallbackMsg = FALLBACK_MESSAGES[tier] || FALLBACK_MESSAGES['default'];
        await streamFallback(fallbackMsg, res);
        return;
    }

    try {
        const client = new Anthropic({
            apiKey: config.anthropicApiKey,
        });

        const systemPrompt = `You are a retention specialist at a retail bank. Write personalised, empathetic outreach messages. Never mention churn or risk scores. Never make promises about rates. Keep tone professional but warm.`;

        const userPrompt = `
      Create a personalized retention message for:
      Name: ${customerData.customer.full_name}
      Segment: ${customerData.customer.segment}
      City: ${customerData.customer.city}
      Life Events: ${analysisResult.life_events.map(le => le.event_type).join(', ') || 'None'}
      Active Signals: ${analysisResult.active_signals.join(', ') || 'None'}
      Recommended Channel: ${channel}
      
      Format rules:
      - If channel is 'sms': keep under 160 characters.
      - If channel is 'email': include a subject line and body.
      - If channel is 'in_app': keep it brief, friendly, as an app notification.
    `;

        const stream = await client.messages.create({
            model: config.claudeModel,
            max_tokens: 1024,
            system: systemPrompt,
            messages: [{ role: 'user', content: userPrompt }],
            stream: true,
        });

        let fullContent = '';

        for await (const chunk of stream) {
            if (chunk.type === 'content_block_delta' && chunk.delta && chunk.delta.text) {
                fullContent += chunk.delta.text;
                res.write(`data: ${JSON.stringify({ type: 'token', content: chunk.delta.text })}\n\n`);
            }
        }

        res.write(`data: ${JSON.stringify({ type: 'done', full_content: fullContent })}\n\n`);
        res.end();

    } catch (error) {
        console.error('[ClaudeService] Error calling Anthropic API:', error);
        res.write(`data: ${JSON.stringify({ type: 'error', message: 'Failed to generate outreach via Claude API' })}\n\n`);
        res.end();
    }
}

module.exports = {
    generateOutreach
};
