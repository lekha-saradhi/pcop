const fs = require("fs");
const path = require("path");

module.exports = async function loadEnrichment() {
  const filePath = path.join(__dirname, "../data/enrichment.json");

  console.log("[loadEnrichment] Loading enrichment data from:", filePath);

  if (!fs.existsSync(filePath)) {
    console.error("[loadEnrichment] File not found:", filePath);
    throw new Error(`File not found: ${filePath}`);
  }

  const data = JSON.parse(fs.readFileSync(filePath, "utf8"));
  console.log("[loadEnrichment] Loaded data:", data);

  const enrichmentMap = new Map();
  Object.entries(data).forEach(([customerId, enrichmentData]) => {
    enrichmentMap.set(customerId, enrichmentData);
  });

  console.log("[loadEnrichment] Enrichment map size:", enrichmentMap.size);
  return {
    map: enrichmentMap,
    count: enrichmentMap.size,
  };
};
