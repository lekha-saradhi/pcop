// Utility functions for filtering data

function parseDate(dateStr) {
  if (!dateStr) return null;
  // Expect YYYY-MM-DD format
  const date = new Date(dateStr + "T00:00:00Z");
  if (isNaN(date.getTime())) return null;
  return date;
}

function filterByDateRange(array, dateField, fromDate, toDate) {
  if (!fromDate && !toDate) return array;

  const from = fromDate ? parseDate(fromDate) : null;
  const to = toDate ? parseDate(toDate) : null;

  return array.filter((item) => {
    const itemDate = parseDate(item[dateField]);
    if (!itemDate) return false;

    if (from && itemDate < from) return false;
    if (to && itemDate > to) return false;

    return true;
  });
}

function filterByCategory(array, category) {
  if (!category) return array;
  return array.filter((item) => item.category === category);
}

function filterByNoteType(array, noteType) {
  if (!noteType) return array;
  return array.filter((item) => item.note_type === noteType);
}

function filterByResolved(array, resolved) {
  if (resolved === undefined || resolved === null) return array;
  const boolValue = resolved === "true" || resolved === true;
  return array.filter((item) => item.resolved === boolValue);
}

function filterByEventType(array, eventType) {
  if (!eventType) return array;
  return array.filter((item) => item.event_type === eventType);
}

function filterByCustomerId(array, customerId) {
  if (!customerId) return array;
  return array.filter((item) => item.customer_id === customerId);
}

function filterByMcc(array, mccCode) {
  if (!mccCode) return array;
  return array.filter((item) => item.mcc_code === mccCode);
}

function filterByChannel(array, channel) {
  if (!channel) return array;
  return array.filter((item) => item.channel === channel);
}

function sliceArray(array, limit) {
  if (!limit) return array;
  const maxLimit = 1000;
  const parsedLimit = Math.min(parseInt(limit), maxLimit);
  return array.slice(0, Math.max(1, parsedLimit));
}

function validateDateFormat(dateStr) {
  if (!dateStr) return true; // Optional parameter
  const regex = /^\d{4}-\d{2}-\d{2}$/;
  if (!regex.test(dateStr)) return false;
  const date = parseDate(dateStr);
  return date !== null;
}

module.exports = {
  parseDate,
  filterByDateRange,
  filterByCategory,
  filterByNoteType,
  filterByResolved,
  filterByEventType,
  filterByCustomerId,
  filterByMcc,
  filterByChannel,
  sliceArray,
  validateDateFormat,
};
