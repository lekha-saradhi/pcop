const fs = require("fs");
const path = require("path");

module.exports = async function loadAccountEvents() {
  const filePath = path.join(__dirname, "../data/account_events.json");

  if (!fs.existsSync(filePath)) {
    throw new Error(`File not found: ${filePath}`);
  }

  const data = JSON.parse(fs.readFileSync(filePath, "utf8"));
  const byCustomer = new Map();
  const byId = new Map();

  data.forEach((event) => {
    byId.set(event.event_id, event);

    if (!byCustomer.has(event.customer_id)) {
      byCustomer.set(event.customer_id, []);
    }
    byCustomer.get(event.customer_id).push(event);
  });

  return {
    all: data,
    byCustomer,
    byId,
    count: data.length,
  };
};
