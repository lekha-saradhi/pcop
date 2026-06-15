const dataStore = require("./dataStore");

let caseIdCounter = 1;
let actionIdCounter = 1;

const REVIEW_CASES = new Map();
const REVIEW_ACTIONS = new Map();

const OFFICERS = [
  { id: "O-001", name: "Arun Sharma", role: "manager" },
  { id: "O-002", name: "Priya Patel", role: "analyst" },
  { id: "O-003", name: "Ravi Deshmukh", role: "admin" },
];

function generateDemoCases() {
  const customers = dataStore.CUSTOMER_IDS.slice(0, 8);
  const score = dataStore.CHURN_SCORES;
  const now = Date.now();

  const types = ["score_alert", "compliance_flag", "outreach_approval", "manual"];
  const statuses = ["pending", "in_review", "approved", "rejected"];
  const priorities = ["critical", "high", "medium", "low"];

  const caseTemplates = [
    {
      customer_id: customers[0],
      type: "score_alert",
      priority: "critical",
      title: "Critical churn risk — score 0.87",
      description: "C-00000001 employer changed to Infosys and city shifted to Bangalore. Multiple risk signals active. Score exceeded critical threshold of 0.85. Requires immediate review and intervention plan.",
      status: "pending",
      createdBy: "system",
      assignedTo: null,
      createdAt: new Date(now - 2 * 3600000).toISOString(),
      context: { score: score[customers[0]] },
    },
    {
      customer_id: customers[1],
      type: "score_alert",
      priority: "high",
      title: "High churn risk — score 0.71",
      description: "C-00000002 showing declining transaction frequency and app engagement decay. Review and approve retention strategy.",
      status: "pending",
      createdBy: "system",
      assignedTo: "O-001",
      createdAt: new Date(now - 6 * 3600000).toISOString(),
      context: { score: score[customers[1]] },
    },
    {
      customer_id: customers[4],
      type: "compliance_flag",
      priority: "high",
      title: "AI-generated content flagged for review",
      description: "Herald content generation for C-00000006 triggered compliance check: bereavement-related content requires human approval before dispatch. Content references MCC 7261 (funeral services).",
      status: "pending",
      createdBy: "herald",
      assignedTo: null,
      createdAt: new Date(now - 4 * 3600000).toISOString(),
      context: { channel: "email", outreachId: null },
    },
    {
      customer_id: customers[5],
      type: "compliance_flag",
      priority: "medium",
      title: "Standard compliance check — content review",
      description: "C-00000012 outreach content triggered regulatory terms check. Standard review required before dispatch.",
      status: "in_review",
      createdBy: "herald",
      assignedTo: "O-002",
      createdAt: new Date(now - 12 * 3600000).toISOString(),
      context: { channel: "sms", outreachId: null },
    },
    {
      customer_id: customers[2],
      type: "outreach_approval",
      priority: "critical",
      title: "Outreach approval required — critical customer",
      description: "C-00000007 is high-risk (score 0.78). AI-generated retention outreach requires officer approval before dispatch per hard-gate policy.",
      status: "pending",
      createdBy: "system",
      assignedTo: null,
      createdAt: new Date(now - 1 * 3600000).toISOString(),
      context: { channel: "call", score: score[customers[2]] },
    },
    {
      customer_id: customers[6],
      type: "outreach_approval",
      priority: "high",
      title: "Outreach approval — high-risk customer",
      description: "C-00000016 has critical churn score (0.82). All engagement signals firing. Outreach prepared — needs officer sign-off.",
      status: "pending",
      createdBy: "system",
      assignedTo: "O-001",
      createdAt: new Date(now - 8 * 3600000).toISOString(),
      context: { channel: "email", score: score[customers[6]] },
    },
    {
      customer_id: customers[3],
      type: "manual",
      priority: "medium",
      title: "Manual review — account activity review",
      description: "C-00000009 flagged by Relationship Manager for unusual withdrawal pattern. Manual review of transaction history requested.",
      status: "approved",
      createdBy: "O-003",
      assignedTo: "O-003",
      createdAt: new Date(now - 24 * 3600000).toISOString(),
      context: {},
    },
    {
      customer_id: customers[7],
      type: "score_alert",
      priority: "medium",
      title: "Watchlist review — medium risk",
      description: "C-00000020 score trending upward (0.47). Wedding MCC pattern detected. Standard review recommended.",
      status: "rejected",
      createdBy: "system",
      assignedTo: "O-002",
      createdAt: new Date(now - 48 * 3600000).toISOString(),
      context: { score: score[customers[7]] },
    },
  ];

  for (const t of caseTemplates) {
    const caseId = `RC-${String(caseIdCounter++).padStart(5, "0")}`;
    REVIEW_CASES.set(caseId, { id: caseId, ...t });

    if (t.status === "approved") {
      const actionId = `RA-${String(actionIdCounter++).padStart(5, "0")}`;
      REVIEW_ACTIONS.set(actionId, {
        id: actionId,
        caseId,
        officerId: "O-003",
        officerName: "Ravi Deshmukh",
        action: "approve",
        comment: "Reviewed transactions. Pattern appears to be due to wedding season spending. No suspicious activity detected.",
        timestamp: new Date(now - 20 * 3600000).toISOString(),
        previousStatus: "in_review",
        newStatus: "approved",
      });
    }

    if (t.status === "rejected") {
      const actionId = `RA-${String(actionIdCounter++).padStart(5, "0")}`;
      REVIEW_ACTIONS.set(actionId, {
        id: actionId,
        caseId,
        officerId: "O-002",
        officerName: "Priya Patel",
        action: "reject",
        comment: "Score trend is within normal range for this segment. Wedding season activity explains the pattern. No intervention needed.",
        timestamp: new Date(now - 44 * 3600000).toISOString(),
        previousStatus: "pending",
        newStatus: "rejected",
      });
    }

    if (t.assignedTo) {
      const officer = OFFICERS.find((o) => o.id === t.assignedTo);
      if (t.status === "pending") {
        const actionId = `RA-${String(actionIdCounter++).padStart(5, "0")}`;
        REVIEW_ACTIONS.set(actionId, {
          id: actionId,
          caseId,
          officerId: null,
          officerName: "System",
          action: "assign",
          comment: `Assigned to ${officer.name}`,
          timestamp: new Date(Date.parse(t.createdAt) + 300000).toISOString(),
          previousStatus: "pending",
          newStatus: "pending",
        });
      }
    }
  }
}
generateDemoCases();

function listCases(filters = {}) {
  let list = Array.from(REVIEW_CASES.values());

  if (filters.status) list = list.filter((c) => c.status === filters.status);
  if (filters.type) list = list.filter((c) => c.type === filters.type);
  if (filters.priority) list = list.filter((c) => c.priority === filters.priority);
  if (filters.assignedTo) list = list.filter((c) => c.assignedTo === filters.assignedTo);

  list.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));

  const page = parseInt(filters.page) || 1;
  const limit = parseInt(filters.limit) || 20;
  const total = list.length;
  const paginated = list.slice((page - 1) * limit, page * limit);

  return {
    status: "ok",
    data: paginated,
    total,
    page,
    limit,
  };
}

function getCase(id) {
  const c = REVIEW_CASES.get(id);
  if (!c) return null;
  const actions = Array.from(REVIEW_ACTIONS.values())
    .filter((a) => a.caseId === id)
    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
  return { status: "ok", data: { ...c, actions } };
}

function createCase({ customer_id, type, priority, title, description, createdBy, context = {} }) {
  const caseId = `RC-${String(caseIdCounter++).padStart(5, "0")}`;
  const entry = {
    id: caseId,
    customer_id,
    type: type || "manual",
    priority: priority || "medium",
    title: title || "Review case",
    description: description || "",
    status: "pending",
    createdBy: createdBy || "system",
    createdAt: new Date().toISOString(),
    assignedTo: null,
    context,
  };
  REVIEW_CASES.set(caseId, entry);
  return { status: "ok", data: entry };
}

function takeAction({ caseId, officerId, officerName, action, comment }) {
  const c = REVIEW_CASES.get(caseId);
  if (!c) return null;

  const previousStatus = c.status;
  const allowedActions = {
    approve: { nextStatus: "approved" },
    reject: { nextStatus: "rejected" },
    escalate: { nextStatus: "escalated" },
    comment: { nextStatus: previousStatus },
    start_review: { nextStatus: "in_review" },
  };

  const transition = allowedActions[action];
  if (!transition) return null;

  const newStatus = transition.nextStatus;
  const actionId = `RA-${String(actionIdCounter++).padStart(5, "0")}`;

  const entry = {
    id: actionId,
    caseId,
    officerId: officerId || null,
    officerName: officerName || "Unknown",
    action,
    comment: comment || "",
    timestamp: new Date().toISOString(),
    previousStatus,
    newStatus,
  };

  REVIEW_ACTIONS.set(actionId, entry);
  c.status = newStatus;

  return {
    status: "ok",
    data: entry,
  };
}

function assignCase(caseId, officerId) {
  const c = REVIEW_CASES.get(caseId);
  if (!c) return null;

  const officer = OFFICERS.find((o) => o.id === officerId);
  const previousAssignee = c.assignedTo;
  c.assignedTo = officerId;

  const actionId = `RA-${String(actionIdCounter++).padStart(5, "0")}`;
  REVIEW_ACTIONS.set(actionId, {
    id: actionId,
    caseId,
    officerId: null,
    officerName: "System",
    action: "assign",
    comment: officer
      ? `Reassigned from ${previousAssignee || "unassigned"} to ${officer.name}`
      : `Assigned to officer ${officerId}`,
    timestamp: new Date().toISOString(),
    previousStatus: c.status,
    newStatus: c.status,
  });

  return { status: "ok", data: c };
}

function getStats() {
  const cases = Array.from(REVIEW_CASES.values());
  const byStatus = {};
  const byType = {};
  const byPriority = {};

  for (const c of cases) {
    byStatus[c.status] = (byStatus[c.status] || 0) + 1;
    byType[c.type] = (byType[c.type] || 0) + 1;
    byPriority[c.priority] = (byPriority[c.priority] || 0) + 1;
  }

  const now = Date.now();
  const allActions = Array.from(REVIEW_ACTIONS.values());
  const avgResolutionMs = allActions
    .filter((a) => a.action === "approve" || a.action === "reject")
    .map((a) => {
      const c = REVIEW_CASES.get(a.caseId);
      if (!c) return null;
      return new Date(a.timestamp) - new Date(c.createdAt);
    })
    .filter(Boolean);

  const avgResolutionH = avgResolutionMs.length
    ? Math.round(avgResolutionMs.reduce((a, b) => a + b, 0) / avgResolutionMs.length / 3600000)
    : 0;

  return {
    status: "ok",
    data: {
      total: cases.length,
      pending: byStatus.pending || 0,
      in_review: byStatus.in_review || 0,
      approved: byStatus.approved || 0,
      rejected: byStatus.rejected || 0,
      escalated: byStatus.escalated || 0,
      by_type: byType,
      by_priority: byPriority,
      avg_resolution_hours: avgResolutionH,
    },
  };
}

module.exports = {
  REVIEW_CASES,
  REVIEW_ACTIONS,
  OFFICERS,
  listCases,
  getCase,
  createCase,
  takeAction,
  assignCase,
  getStats,
};
