const fs = require("fs");
const path = require("path");

module.exports = async function loadCustomers() {
  const filePath = path.join(__dirname, "../data/customers.json");

  if (!fs.existsSync(filePath)) {
    throw new Error(`File not found: ${filePath}`);
  }

  const data = JSON.parse(fs.readFileSync(filePath, "utf8"));
  const customerMap = new Map();

  data.forEach((customer) => {
    customerMap.set(customer.customer_id, customer);
  });

  return {
    map: customerMap,
    count: customerMap.size,
  };
};
