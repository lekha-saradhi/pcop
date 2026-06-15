const fs = require("fs");
const path = require("path");

module.exports = async function loadKycUpdates() {
  const filePath = path.join(__dirname, "../data/kyc_updates.json");

  if (!fs.existsSync(filePath)) {
    throw new Error(`File not found: ${filePath}`);
  }

  const data = JSON.parse(fs.readFileSync(filePath, "utf8"));
  const byCustomer = new Map();
  const byId = new Map();

  data.forEach((update) => {
    byId.set(update.update_id, update);

    if (!byCustomer.has(update.customer_id)) {
      byCustomer.set(update.customer_id, []);
    }
    byCustomer.get(update.customer_id).push(update);
  });

  return {
    all: data,
    byCustomer,
    byId,
    count: data.length,
  };
};
