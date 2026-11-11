import { DAY_IN_MS, THEME_LABELS } from "../config/constants";

export function toDateInputValue(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function parseDateInputValue(value) {
  return new Date(`${value}T00:00:00`);
}

export function formatDateLabel(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
  }).format(parseDateInputValue(value));
}

export function formatDateTimeLabel(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

export function formatThemeLabel(theme) {
  return THEME_LABELS[theme] || theme;
}

export function formatCurrency(value) {
  if (typeof value !== "number") return "";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatMatchScore(score) {
  return `${Math.round(score * 100)}% match`;
}

export function getTripLengthLabel(startDate, endDate) {
  if (!startDate || !endDate) return "";
  const diffDays = Math.round(
    (parseDateInputValue(endDate) - parseDateInputValue(startDate)) / DAY_IN_MS,
  );
  if (diffDays <= 0) return "";
  return `${diffDays} ${diffDays === 1 ? "night" : "nights"}`;
}

export function getOptionBadges(option, index, options) {
  if (!options.length) return [];
  const lowestPrice = Math.min(...options.map((item) => item.price_usd));
  const badges = [];

  if (index === 0) {
    badges.push({ label: "Best match", tone: "primary" });
  } else if (option.price_usd === lowestPrice) {
    badges.push({ label: "Lowest price", tone: "success" });
  } else {
    badges.push({ label: "Alternative", tone: "neutral" });
  }

  if (index === 0 && option.price_usd === lowestPrice) {
    badges.push({ label: "Lowest price", tone: "success" });
  }

  return badges;
}

export function getTripPlanPreview(tripPlan) {
  const lines = tripPlan
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  if (!lines.length) return "";

  const dayLine =
    lines.find((line) => /^[-*]?\s*day\s+\d+/i.test(line)) || lines[0];
  return dayLine.replace(/^[-*]\s*/, "");
}
