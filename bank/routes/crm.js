const express = require("express");
const {
  filterByDateRange,
  filterByNoteType,
  filterByResolved,
  sliceArray,
  validateDateFormat,
} = require("../utils/filters");

module.exports = function createCrmRouter(stores) {
  const router = express.Router();

  // GET /api/crm/notes - CRM notes with filters
  router.get("/notes", (req, res) => {
    const { customer_id, from, to, note_type, resolved, limit } = req.query;

    if (!customer_id) {
      return res.status(400).json({
        status: "error",
        message: "customer_id is required",
      });
    }

    if (
      (from && !validateDateFormat(from)) ||
      (to && !validateDateFormat(to))
    ) {
      return res.status(400).json({
        status: "error",
        message: "Invalid date format. Use YYYY-MM-DD",
      });
    }

    let notes = stores.crmNotes.byCustomer.get(customer_id) || [];

    notes = filterByDateRange(notes, "created_at", from, to);
    if (note_type) {
      notes = filterByNoteType(notes, note_type);
    }
    if (resolved !== undefined) {
      notes = filterByResolved(notes, resolved);
    }

    notes = sliceArray(notes, limit || 20);

    res.json({
      status: "ok",
      count: notes.length,
      data: notes,
    });
  });

  // GET /api/crm/notes/:note_id - Single note by ID
  router.get("/notes/:note_id", (req, res) => {
    const note = stores.crmNotes.byId.get(req.params.note_id);

    if (!note) {
      return res.status(404).json({
        status: "error",
        message: `Note ${req.params.note_id} not found`,
      });
    }

    res.json({
      status: "ok",
      data: note,
    });
  });

  // GET /api/crm/complaints/summary - Complaint statistics
  router.get("/complaints/summary", (req, res) => {
    const { customer_id } = req.query;

    if (!customer_id) {
      return res.status(400).json({
        status: "error",
        message: "customer_id is required",
      });
    }

    let notes = stores.crmNotes.byCustomer.get(customer_id) || [];
    const complaints = notes.filter((n) => n.note_type === "complaint");

    const summary = {
      total_complaints: complaints.length,
      unresolved_count: 0,
      avg_resolution_days: 0,
      last_complaint_at: null,
    };

    let totalResolutionDays = 0;
    let resolvedCount = 0;

    complaints.forEach((complaint) => {
      if (!complaint.resolved) {
        summary.unresolved_count++;
      } else {
        if (complaint.resolution_days) {
          totalResolutionDays += complaint.resolution_days;
          resolvedCount++;
        }
      }
    });

    if (complaints.length > 0) {
      summary.last_complaint_at = complaints[0].created_at;
    }

    if (resolvedCount > 0) {
      summary.avg_resolution_days = totalResolutionDays / resolvedCount;
    }

    res.json({
      status: "ok",
      data: summary,
    });
  });

  // GET /api/crm/sentiment/history - Sentiment history for CUSUM
  router.get("/sentiment/history", (req, res) => {
    const { customer_id, from, to } = req.query;

    if (!customer_id) {
      return res.status(400).json({
        status: "error",
        message: "customer_id is required",
      });
    }

    if (
      (from && !validateDateFormat(from)) ||
      (to && !validateDateFormat(to))
    ) {
      return res.status(400).json({
        status: "error",
        message: "Invalid date format. Use YYYY-MM-DD",
      });
    }

    let notes = stores.crmNotes.byCustomer.get(customer_id) || [];
    notes = filterByDateRange(notes, "created_at", from, to);

    const history = notes.map((note) => ({
      created_at: note.created_at,
      sentiment_score: note.sentiment_score,
    }));

    res.json({
      status: "ok",
      count: history.length,
      data: history,
    });
  });

  return router;
};
