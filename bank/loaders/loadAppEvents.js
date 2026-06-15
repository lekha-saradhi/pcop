const fs = require("fs");
const path = require("path");
const { parse } = require("csv-parse/sync");

module.exports = async function loadAppEvents() {
  const filePath = path.join(__dirname, "../data/app_events.csv");

  if (!fs.existsSync(filePath)) {
    throw new Error(`File not found: ${filePath}`);
  }

  const fileContent = fs.readFileSync(filePath, "utf8");
  const records = parse(fileContent, {
    columns: true,
    skip_empty_lines: true,
    cast: (value, context) => {
      if (context.column === "session_duration_s") {
        return value ? parseInt(value) : null;
      }
      return value;
    },
  });

  const eventsByCustomer = new Map();

  records.forEach((event) => {
    if (!eventsByCustomer.has(event.customer_id)) {
      eventsByCustomer.set(event.customer_id, []);
    }
    eventsByCustomer.get(event.customer_id).push(event);
  });

  // Sort each customer's events by timestamp descending
  eventsByCustomer.forEach((events) => {
    events.sort(
      (a, b) => new Date(b.event_timestamp) - new Date(a.event_timestamp),
    );
  });

  return {
    map: eventsByCustomer,
    count: records.length,
  };
};
