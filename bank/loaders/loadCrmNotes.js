const fs = require("fs");
const path = require("path");

module.exports = async function loadCrmNotes() {
  const filePath = path.join(__dirname, "../data/crm_notes.json");

  if (!fs.existsSync(filePath)) {
    throw new Error(`File not found: ${filePath}`);
  }

  const data = JSON.parse(fs.readFileSync(filePath, "utf8"));
  const notesByCustomer = new Map();
  const noteMap = new Map();

  data.forEach((note) => {
    noteMap.set(note.note_id, note);

    if (!notesByCustomer.has(note.customer_id)) {
      notesByCustomer.set(note.customer_id, []);
    }
    notesByCustomer.get(note.customer_id).push(note);
  });

  // Sort each customer's notes by created_at descending
  notesByCustomer.forEach((notes) => {
    notes.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  });

  return {
    byCustomer: notesByCustomer,
    byId: noteMap,
    count: data.length,
  };
};
