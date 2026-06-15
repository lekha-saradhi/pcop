const fs = require("fs");
const path = require("path");
const { parse } = require("csv-parse/sync");

module.exports = async function loadTransactions() {
  const filePath = path.join(__dirname, "../data/transactions.csv");

  if (!fs.existsSync(filePath)) {
    throw new Error(`File not found: ${filePath}`);
  }

  const fileContent = fs.readFileSync(filePath, "utf8");
  const records = parse(fileContent, {
    columns: true,
    skip_empty_lines: true,
    cast: (value, context) => {
      if (context.column === "amount" || context.column === "balance_after") {
        return parseFloat(value);
      }
      if (context.column === "is_international") {
        return value === "1" || value === "true";
      }
      return value;
    },
  });

  const transactionsByCustomer = new Map();

  records.forEach((transaction) => {
    if (!transactionsByCustomer.has(transaction.customer_id)) {
      transactionsByCustomer.set(transaction.customer_id, []);
    }
    transactionsByCustomer.get(transaction.customer_id).push(transaction);
  });

  // Sort each customer's transactions by date descending
  transactionsByCustomer.forEach((txns) => {
    txns.sort((a, b) => new Date(b.txn_date) - new Date(a.txn_date));
  });

  return {
    map: transactionsByCustomer,
    count: records.length,
  };
};
