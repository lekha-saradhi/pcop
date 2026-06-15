// API client — all calls proxied through Next.js rewrites to avoid CORS
const API_URL = typeof window !== 'undefined' ? '' : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000');
const TOKEN_KEY = 'pcop_token';

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token: string): void { localStorage.setItem(TOKEN_KEY, token); }
export function clearToken(): void { localStorage.removeItem(TOKEN_KEY); }

async function fetchApi(endpoint: string, options: RequestInit = {}) {
  const url   = `${API_URL}${endpoint}`;
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const response = await fetch(url, { ...options, headers });
  if (response.status === 401) {
    clearToken();
    if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login'))
      window.location.href = '/login';
    throw new Error('Unauthorized');
  }
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.message || `API Error ${response.status}`);
  }
  return response.json();
}

export const api = {
  // ── Auth ────────────────────────────────────────────────────────────────────
  login: async (username: string, password: string) => {
    const r = await fetch(`${API_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    if (!r.ok) throw new Error('Invalid credentials');
    const data = await r.json();
    if (data.token) setToken(data.token);
    return data;
  },
  logout: () => clearToken(),

  // ── Portfolio ───────────────────────────────────────────────────────────────
  getPortfolioFull:      ()      => fetchApi('/api/portfolio/full'),
  getPortfolioSummary:   ()      => fetchApi('/api/portfolio/summary'),
  getTierDistribution:   ()      => fetchApi('/api/portfolio/tier-distribution'),
  getChurnTrend:         ()      => fetchApi('/api/portfolio/churn-trend'),
  getSignalBreakdown:    ()      => fetchApi('/api/portfolio/signal-breakdown'),
  getTopAtRisk:          (n=10)  => fetchApi(`/api/portfolio/top-at-risk?limit=${n}`),
  getModelHealth:        ()      => fetchApi('/api/portfolio/model-health'),
  getUpliftStats:        ()      => fetchApi('/api/portfolio/uplift'),
  getBanditState:        ()      => fetchApi('/api/portfolio/bandit'),

  // ── Customers ───────────────────────────────────────────────────────────────
  getCustomers: (params: Record<string, string | number | undefined> = {}) => {
    const sp = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') sp.set(k, String(v)); });
    return fetchApi(`/api/customers?${sp}`);
  },
  getCustomerById:       (id: string) => fetchApi(`/api/customers/${id}`),
  getCustomerSignals:    (id: string) => fetchApi(`/api/customers/${id}/signals`),
  getCustomerTransactions:(id: string) => fetchApi(`/api/customers/${id}/transactions`),
  getCustomerSurvival:   (id: string) => fetchApi(`/api/customers/${id}/survival`),
  getCustomerScore:      (id: string) => fetchApi(`/api/customers/${id}/score`),
  getCustomerPlan:       (id: string) => fetchApi(`/api/customers/${id}/plan`),
  getCustomerHerald:     (id: string) => fetchApi(`/api/customers/${id}/herald`),

  // ── V2 / CHRONOS ────────────────────────────────────────────────────────────
  getV2Scores:           ()           => fetchApi('/api/v2/scores'),
  getV2Score:            (id: string) => fetchApi(`/api/v2/scores/${id}`),
  getV2Signals:          ()           => fetchApi('/api/v2/signals'),
  getV2ActionPlans:      ()           => fetchApi('/api/v2/action-plans'),
  getV2ActionPlan:       (id: string) => fetchApi(`/api/v2/action-plans/${id}`),
  getV2Content:          ()           => fetchApi('/api/v2/content'),
  getV2ContentById:      (id: string) => fetchApi(`/api/v2/content/${id}`),
  getV2ModelHealth:      ()           => fetchApi('/api/v2/model-health'),
  getV2PortfolioSurvival:()           => fetchApi('/api/v2/portfolio-survival'),

  // ── Outreach ────────────────────────────────────────────────────────────────
  getCampaigns: () => fetchApi('/api/outreach/campaigns'),
  getOutreach: (params: Record<string, string | number | undefined> = {}) => {
    const sp = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') sp.set(k, String(v)); });
    return fetchApi(`/api/outreach?${sp}`);
  },
  getOutreachById:    (id: string) => fetchApi(`/api/outreach/${id}`),
  generateOutreach:   (customer_id: string) =>
    fetchApi('/api/outreach/generate', { method: 'POST', body: JSON.stringify({ customer_id }) }),

  // ── Analysis ────────────────────────────────────────────────────────────────
  analyzeCustomer:    (customer_id: string) =>
    fetchApi('/api/analysis/analyze', { method: 'POST', body: JSON.stringify({ customer_id }) }),

  // ── Reviews ─────────────────────────────────────────────────────────────────
  getReviews: (params: Record<string, string | number | undefined> = {}) => {
    const sp = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') sp.set(k, String(v)); });
    return fetchApi(`/api/reviews?${sp}`);
  },
  getReviewById:      (id: string) => fetchApi(`/api/reviews/${id}`),
  getReviewStats:     () => fetchApi('/api/reviews/stats'),
  getReviewOfficers:  () => fetchApi('/api/reviews/officers'),
  approveReview:      (id: string, notes?: string) =>
    fetchApi(`/api/reviews/${id}/approve`, { method: 'POST', body: JSON.stringify({ notes }) }),
  rejectReview:       (id: string, notes?: string) =>
    fetchApi(`/api/reviews/${id}/reject`, { method: 'POST', body: JSON.stringify({ notes }) }),
  takeReviewAction: (id: string, opts: { action: string; comment: string }) => {
    if (opts.action === 'approve')
      return fetchApi(`/api/reviews/${id}/approve`, { method: 'POST', body: JSON.stringify({ notes: opts.comment }) });
    if (opts.action === 'reject')
      return fetchApi(`/api/reviews/${id}/reject`, { method: 'POST', body: JSON.stringify({ notes: opts.comment }) });
    return fetchApi(`/api/reviews/${id}/action`, { method: 'POST', body: JSON.stringify(opts) });
  },

  // ── Customers (create) ───────────────────────────────────────────────────────
  createCustomer: (data: unknown) =>
    fetchApi('/api/customers', { method: 'POST', body: JSON.stringify(data) }),

  // ── Kafka ────────────────────────────────────────────────────────────────────
  getKafkaStatus:     () => fetchApi('/api/kafka/status'),
};
