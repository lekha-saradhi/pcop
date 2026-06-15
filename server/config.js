require('dotenv').config();

module.exports = {
  port: process.env.PORT || 8000,
  bankApiBaseUrl: process.env.BANK_API_BASE_URL || 'http://localhost:3001',
  jwtSecret: process.env.JWT_SECRET || 'change-this-in-production',
  jwtExpiresIn: process.env.JWT_EXPIRES_IN || '8h',
  anthropicApiKey: process.env.ANTHROPIC_API_KEY || '',
  claudeModel: process.env.CLAUDE_MODEL || 'claude-3-sonnet-20240229',
  useClaudeFallback: process.env.USE_CLAUDE_FALLBACK === 'true' || !process.env.ANTHROPIC_API_KEY
};
