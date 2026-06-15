const fs = require("fs");
const path = require("path");

module.exports = async function loadAccounts() {
  const filePath = path.join(__dirname, "../data/accounts.json");

  if (!fs.existsSync(filePath)) {
    throw new Error(`File not found: ${filePath}`);
  }

  const data = JSON.parse(fs.readFileSync(filePath, "utf8"));
  const accountsByCustomer = new Map();
  const accountMap = new Map();

  data.forEach((account) => {
    accountMap.set(account.account_id, account);

    if (!accountsByCustomer.has(account.customer_id)) {
      accountsByCustomer.set(account.customer_id, []);
    }
    accountsByCustomer.get(account.customer_id).push(account);
  });

  return {
    byCustomer: accountsByCustomer,
    byId: accountMap,
    count: data.length,
  };
};
