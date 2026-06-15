// ─── Core types matching server/data/*.json ───────────────────────────────────

export type RiskTier = 'PRIORITY' | 'ESCALATE' | 'STANDARD' | 'MONITOR' | 'NONE';
export type Segment  = 'HNW' | 'Mass Affluent' | 'Mass Market' | 'SME' | 'Digital Native';
export type Channel  = 'email' | 'sms' | 'push' | 'phone' | 'branch' | 'app' | 'call' | 'rm_visit';
export type Archetype = 'vip_loyal' | 'healthy_active' | 'drifting' | 'high_risk' | 'critical';

export interface Customer {
  customer_id:          string;
  full_name:            string;
  first_name:           string;
  email:                string;
  phone:                string;
  age:                  number;
  income:               number;
  tenure_months:        number;
  segment:              Segment;
  archetype:            Archetype;
  city:                 string;
  city_tier:            number;
  product_count:        number;
  employer:             string;
  relationship_manager: string;
  preferred_channel:    Channel;
  email_opt_in:         boolean;
  sms_opt_in:           boolean;
  txn_freq_90d:         number;
  avg_txn_amount:       number;
  inactivity_days:      number;
  digital_ratio:        number;
  complaint_count:      number;
  atm_withdrawals_90d:  number;
  app_logins_30d:       number;
  balance:              number;
  salary_credit_count:  number;
  nps:                  number;
  risk_tier:            RiskTier;
  churn_score:          number;
  life_event:           string | null;
  life_event_desc:      string | null;
}

export interface ModelScore {
  customer_id:            string;
  final_score:            number;
  risk_tier:              RiskTier;
  genesis_score:          number;
  habitat_score:          number;
  tare_score:             number;
  graph_score:            number;
  ci_lower:               number;
  ci_upper:               number;
  p7:                     number;
  p30:                    number;
  p90:                    number;
  urgency_horizon:        '7d' | '30d' | '90d';
  ensemble_disagreement:  number;
}

export interface Signal {
  signal_type:      string;
  detected:         boolean;
  confidence:       number;
  cusum_value:      number;
  alarm_threshold:  number;
  method:           string;
  days_active:      number;
}

export interface Transaction {
  date:     string;
  amount:   number;
  channel:  string;
  type:     string;
  category: string;
}

export interface SurvivalData {
  customer_id:  string;
  time_points:  number[];
  survival:     number[];
  p7:           number;
  p30:          number;
  p90:          number;
}

export interface ActionPlan {
  customer_id:      string;
  action:           string;
  channel:          string;
  urgency:          string;
  offer_code:       string;
  offer_display:    string;
  content_strategy: string;
  rationale:        string;
  life_event:       string | null;
  suppressed:       boolean;
  tone_modifiers:   string[];
  priority_rank:    number;
}

export interface HeraldContent {
  customer_id: string;
  risk_tier:   RiskTier;
  email?: {
    subject:            string;
    body:               string;
    compliance_status:  string;
    variant:            string;
    word_count:         number;
  };
  sms?: {
    body:               string;
    compliance_status:  string;
    char_count:         number;
  };
  push?: {
    title:              string;
    body:               string;
    compliance_status:  string;
  };
}

export interface CustomerSnapshot {
  customer:   Customer;
  score:      ModelScore;
  signals:    Signal[];
  plan:       ActionPlan;
  survival:   SurvivalData;
  herald:     HeraldContent | null;
}

// ─── Portfolio ────────────────────────────────────────────────────────────────

export interface PortfolioSummary {
  total_customers:      number;
  avg_churn_score:      number;
  priority_count:       number;
  escalate_count:       number;
  standard_count:       number;
  monitor_count:        number;
  safe_count:           number;
  active_signals:       number;
  life_events_detected: number;
  outreach_dispatched:  number;
  suppression_rate:     number;
}

export interface TierDistribution {
  tier:  RiskTier;
  count: number;
  pct:   number;
}

export interface ChurnTrendPoint {
  week:             number;
  label:            string;
  avg_score:        number;
  critical_count:   number;
  high_count:       number;
}

export interface ModelHealth {
  ensemble_weights:  Record<string, number>;
  model_aucs:        Record<string, number>;
  fusion_ece:        number;
  fusion_auc:        number;
  last_retrained:    string;
  n_customers_scored:number;
  calibration_points: { bin: number; predicted: number; actual: number }[];
  feature_importance: { feature: string; importance: number }[];
}

export interface UpliftStats {
  ate_doubly_robust:  number;
  ate_ci_lower:       number;
  ate_ci_upper:       number;
  qini_coefficient:   number;
  treated_visit_rate: number;
  control_visit_rate: number;
  n_treated:          number;
  n_control:          number;
  qini_curve:         { pct: number; uplift: number }[];
}

export interface BanditState {
  arms:               string[];
  true_rates:         number[];
  expected_reward:    number[];
  selection_counts:   number[];
  total_steps:        number;
  regret_reduction_pct: number;
  best_arm:           string;
  posteriors:         { arm: string; alpha: number; beta: number; mean: number }[];
}

export interface Portfolio {
  summary:           PortfolioSummary;
  tier_distribution: TierDistribution[];
  churn_trend:       ChurnTrendPoint[];
  signal_breakdown:  { type: string; count: number }[];
  model_health:      ModelHealth;
  uplift_stats:      UpliftStats;
  bandit_state:      BanditState;
  top_at_risk:       { customer_id: string; full_name: string; segment: string; churn_score: number; risk_tier: RiskTier; city: string; alarm_count: number }[];
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export interface AuthUser {
  username: string;
  role:     'analyst' | 'manager' | 'admin';
  name:     string;
}

// ─── Outreach ─────────────────────────────────────────────────────────────────

export interface OutreachRecord {
  id:              string;
  customer_id:     string;
  channel:         string;
  risk_tier:       RiskTier;
  status:          'sent' | 'delivered' | 'opened' | 'clicked' | 'failed';
  offer_code:      string;
  dispatched_at:   string;
  content_preview: string;
}

export interface Campaign {
  id:          string;
  name:        string;
  status:      'active' | 'completed' | 'paused';
  channel:     string;
  customers:   number;
  opens:       number;
  conversions: number;
}

// ─── Reviews ─────────────────────────────────────────────────────────────────

export type ReviewActionType = 'approve' | 'reject' | 'escalate' | 'comment' | 'assign' | 'start_review';
export type ReviewStatus     = 'pending' | 'in_review' | 'approved' | 'rejected' | 'escalated';
export type ReviewType       = 'score_alert' | 'compliance_flag' | 'outreach_approval' | 'manual';
export type ReviewPriority   = 'low' | 'medium' | 'high' | 'critical';

export interface ReviewActionEntry {
  id:             string;
  action:         ReviewActionType;
  comment?:       string;
  timestamp:      string;
  officerName:    string;
  previousStatus: ReviewStatus;
  newStatus:      ReviewStatus;
}

export interface ReviewItem {
  id:          string;
  customer_id: string;
  full_name:   string;
  risk_tier:   RiskTier;
  churn_score: number;
  action:      string;
  status:      'pending' | 'approved' | 'rejected';
  created_at:  string;
  reviewed_at: string | null;
  reviewer:    string | null;
  notes:       string | null;
}

export interface ReviewCase {
  id:          string;
  customer_id: string;
  full_name:   string;
  risk_tier:   RiskTier;
  churn_score: number;
  action:      string;
  status:      ReviewStatus;
  created_at:  string;
  reviewed_at: string | null;
  reviewer:    string | null;
  notes:       string | null;
  type:        ReviewType;
  title:       string;
  description: string;
  priority:    ReviewPriority;
  createdAt:   string;
  createdBy:   string;
  context:     Record<string, unknown>;
  actions:     ReviewActionEntry[];
}

export interface ReviewStats {
  pending:    number;
  in_review:  number;
  approved:   number;
  rejected:   number;
  total:      number;
}

export interface ReviewOfficer {
  id:   string;
  name: string;
  role: string;
}

// ─── Kafka ────────────────────────────────────────────────────────────────────

export interface KafkaEvent {
  id:          number;
  topic:       string;
  customerId:  string;
  description: string;
  ts:          string;
}

export interface KafkaStatus {
  mode:              'kafka' | 'simulation' | 'initialising';
  connected:         boolean;
  messagesProcessed: number;
  lastEventAt:       string | null;
  recentEvents:      KafkaEvent[];
}

export interface CreateCustomerInput {
  full_name:           string;
  age?:                number;
  city?:               string;
  email?:              string;
  phone_mobile?:       string;
  employer_name?:      string;
  employment_type?:    string;
  annual_income_band?: string;
  tenure_years?:       number;
  segment?:            Segment;
  preferred_channel?:  Channel;
  email_opt_in?:       boolean;
  sms_opt_in?:         boolean;
  push_opt_in?:        boolean;
  call_opt_in?:        boolean;
  [key: string]:       unknown;
}
