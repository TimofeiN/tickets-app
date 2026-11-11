export const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL || "http://localhost:8100";
export const AUTH_TOKEN_STORAGE_KEY = "tickets_app_access_token";
export const DAY_IN_MS = 24 * 60 * 60 * 1000;
export const THEMES = [
  { value: "beach", label: "Beach" },
  { value: "history", label: "History" },
  { value: "active_summer", label: "Active summer" },
  { value: "active_winter", label: "Active winter" },
  { value: "gastronomy", label: "Gastronomy" },
  { value: "family", label: "Family" },
  { value: "nightlife", label: "Nightlife" },
];
export const THEME_LABELS = Object.fromEntries(
  THEMES.map((theme) => [theme.value, theme.label]),
);
export const FRIENDLY_SOURCE = {
  live: "Live fares",
  fallback: "Backup fares",
};
export const FRIENDLY_RANKING = {
  llm: "AI-ranked",
  deterministic: "Rule-based ranking",
};
export const FRIENDLY_ENRICHMENT = {
  llm: "Trip notes included",
  unavailable: "Basic details only",
};
export const FRIENDLY_FALLBACK_REASON = {
  provider_unavailable: "Using backup fare data for this search.",
  ranking_unavailable:
    "Showing rule-based ranking because AI ranking was unavailable.",
  enrichment_unavailable: "Trip notes are limited for this search.",
  city_names_unavailable:
    "Some destination labels may be less polished than usual.",
  constraints_relaxed:
    "Some options may stretch the original search constraints.",
};
export const AI_LOADING_STEPS = [
  "Analyzing destinations...",
  "Ranking options...",
  "Building itinerary...",
];
