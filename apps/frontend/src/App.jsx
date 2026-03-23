import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8100";
const AUTH_TOKEN_STORAGE_KEY = "tickets_app_access_token";
const DAY_IN_MS = 24 * 60 * 60 * 1000;
const THEMES = [
  { value: "beach", label: "Beach" },
  { value: "history", label: "History" },
  { value: "active_summer", label: "Active summer" },
  { value: "active_winter", label: "Active winter" },
  { value: "gastronomy", label: "Gastronomy" },
  { value: "family", label: "Family" },
  { value: "nightlife", label: "Nightlife" },
];
const THEME_LABELS = Object.fromEntries(
  THEMES.map((theme) => [theme.value, theme.label]),
);
const FRIENDLY_SOURCE = {
  live: "Live fares",
  fallback: "Backup fares",
};
const FRIENDLY_RANKING = {
  llm: "AI-ranked",
  deterministic: "Rule-based ranking",
};
const FRIENDLY_ENRICHMENT = {
  llm: "Trip notes included",
  unavailable: "Basic details only",
};
const FRIENDLY_FALLBACK_REASON = {
  provider_unavailable: "Using backup fare data for this search.",
  ranking_unavailable:
    "Showing rule-based ranking because AI ranking was unavailable.",
  enrichment_unavailable: "Trip notes are limited for this search.",
  city_names_unavailable:
    "Some destination labels may be less polished than usual.",
  constraints_relaxed:
    "Some options may stretch the original search constraints.",
};
const AI_LOADING_STEPS = [
  "Analyzing destinations...",
  "Ranking options...",
  "Building itinerary...",
];

function toDateInputValue(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function parseDateInputValue(value) {
  return new Date(`${value}T00:00:00`);
}

function formatDateLabel(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
  }).format(parseDateInputValue(value));
}

function formatDateTimeLabel(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatThemeLabel(theme) {
  return THEME_LABELS[theme] || theme;
}

function formatCurrency(value) {
  if (typeof value !== "number") return "";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatMatchScore(score) {
  return `${Math.round(score * 100)}% match`;
}

function getTripLengthLabel(startDate, endDate) {
  if (!startDate || !endDate) return "";
  const diffDays = Math.round(
    (parseDateInputValue(endDate) - parseDateInputValue(startDate)) / DAY_IN_MS,
  );
  if (diffDays <= 0) return "";
  return `${diffDays} ${diffDays === 1 ? "night" : "nights"}`;
}

function getOptionBadges(option, index, options) {
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

function getTripPlanPreview(tripPlan) {
  const lines = tripPlan
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  if (!lines.length) return "";

  const dayLine =
    lines.find((line) => /^[-*]?\s*day\s+\d+/i.test(line)) || lines[0];
  return dayLine.replace(/^[-*]\s*/, "");
}

function getStoredAuthToken() {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY) || "";
}

function storeAuthToken(token) {
  if (typeof window === "undefined") return;
  if (token) {
    window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
    return;
  }
  window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
}

function extractErrorMessage(errorBody, fallbackMessage) {
  const validationError = errorBody?.detail?.[0];
  if (validationError?.msg) {
    const fieldName = validationError.loc?.[validationError.loc.length - 1];
    if (typeof fieldName === "string") {
      const normalizedFieldName = fieldName.replaceAll("_", " ");
      const label =
        normalizedFieldName.charAt(0).toUpperCase() +
        normalizedFieldName.slice(1);
      const normalizedMessage = validationError.msg.replace(/^String /, "");
      return `${label}: ${normalizedMessage}`;
    }
    return validationError.msg;
  }

  return errorBody?.error?.message || errorBody?.detail || fallbackMessage;
}

async function fetchJson(path, { token = "", ...options } = {}) {
  const headers = {
    ...(options.body ? { "Content-Type": "application/json" } : {}),
    ...(options.headers || {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
  const response = await fetch(`${BACKEND_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorMessage = "Request failed";
    try {
      const errorBody = await response.json();
      errorMessage = extractErrorMessage(errorBody, errorMessage);
    } catch {
      // keep default message when response body is not JSON
    }
    throw new Error(errorMessage);
  }

  if (response.status === 204) {
    return null;
  }
  return response.json();
}

function normalizeResultPayload(data, savedSearchId = null) {
  return {
    options: data?.options || [],
    guidance: data?.guidance || {
      improvement_hint: "",
      counterfactual: "",
    },
    meta: data?.meta || null,
    savedSearchId: data?.saved_search_id || savedSearchId,
  };
}

function buildSearchContextFromPayload(payload) {
  return {
    originCity: payload.origin_city,
    startDate: payload.strict_dates?.start_date || "",
    endDate: payload.strict_dates?.end_date || "",
    budgetUsd: payload.budget_usd,
    themes: payload.themes || [],
  };
}

const DEFAULT_START_DATE = toDateInputValue(new Date());
const DEFAULT_END_DATE = toDateInputValue(new Date(Date.now() + 3 * DAY_IN_MS));

function ResultMeta({ meta }) {
  if (!meta) return null;

  const pills = [
    FRIENDLY_SOURCE[meta.data_source],
    FRIENDLY_RANKING[meta.ranking_mode],
    FRIENDLY_ENRICHMENT[meta.enrichment_mode],
  ].filter(Boolean);

  const notices = (meta.fallback_reasons || [])
    .map((reason) => FRIENDLY_FALLBACK_REASON[reason])
    .filter(Boolean);

  return (
    <>
      {pills.length ? (
        <div className="meta-panel">
          {pills.map((pill) => (
            <span className="meta-pill" key={pill}>
              {pill}
            </span>
          ))}
        </div>
      ) : null}
      {notices.length ? (
        <div className="notice-stack">
          {notices.map((notice) => (
            <p className="notice" key={notice}>
              {notice}
            </p>
          ))}
        </div>
      ) : null}
    </>
  );
}

function SearchSummary({ searchContext, onEditSearch }) {
  if (!searchContext) return null;

  const summaryItems = [
    {
      label: "From",
      value: searchContext.originCity,
    },
    {
      label: "Dates",
      value: `${formatDateLabel(searchContext.startDate)} - ${formatDateLabel(searchContext.endDate)}`,
    },
    {
      label: "Trip length",
      value: getTripLengthLabel(searchContext.startDate, searchContext.endDate),
    },
    {
      label: "Budget",
      value: `${formatCurrency(searchContext.budgetUsd)} total for 2`,
    },
  ].filter((item) => item.value);

  return (
    <aside className="summary-card">
      <div className="summary-header">
        <div className="summary-header-row">
          <p className="section-kicker">Current brief</p>
          <button
            className="inline-link-button"
            type="button"
            onClick={onEditSearch}
          >
            Edit search
          </button>
        </div>
        <h3>What this search optimizes for</h3>
      </div>
      <div className="summary-grid">
        {summaryItems.map((item) => (
          <div className="summary-item" key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </div>
        ))}
      </div>
      <div className="summary-themes">
        {searchContext.themes.map((theme) => (
          <span className="summary-theme" key={theme}>
            {formatThemeLabel(theme)}
          </span>
        ))}
      </div>
    </aside>
  );
}

function GuidancePanel({ guidance }) {
  if (!guidance?.improvement_hint && !guidance?.counterfactual) return null;

  return (
    <div className="guidance-grid">
      {guidance.improvement_hint ? (
        <article className="guidance-card">
          <p className="section-kicker">Refine search</p>
          <h3>How to improve results</h3>
          <p>{guidance.improvement_hint}</p>
        </article>
      ) : null}
      {guidance.counterfactual ? (
        <article className="guidance-card">
          <p className="section-kicker">Tradeoff view</p>
          <h3>If priorities change</h3>
          <p>{guidance.counterfactual}</p>
        </article>
      ) : null}
    </div>
  );
}

function OptionCard({ option, index, options, featured = false }) {
  const badges = getOptionBadges(option, index, options);
  const cardClassName = featured ? "card card-featured" : "card";
  const hasStyleDetails = option.trip_style || option.vibe;
  const tripPlan = option.trip_plan?.trim() || "";
  const isTripPlanCollapsible =
    tripPlan.length > 320 || tripPlan.split("\n").filter(Boolean).length > 5;
  const [isTripPlanExpanded, setIsTripPlanExpanded] = useState(false);

  return (
    <article className={cardClassName}>
      <div className="card-topline">
        <div className="badge-row">
          {badges.map((badge) => (
            <span
              className={`result-badge result-badge-${badge.tone}`}
              key={badge.label}
            >
              {badge.label}
            </span>
          ))}
        </div>
        <span className="score-pill">{formatMatchScore(option.score)}</span>
      </div>

      <div className="card-header">
        <div>
          <h3>{option.destination_city}</h3>
          <p className="route">
            {option.origin_airport} to {option.destination_airport}
          </p>
        </div>
        <div className="price-block">
          <strong>{formatCurrency(option.price_usd)}</strong>
          <span>Total for 2 travelers</span>
        </div>
      </div>

      <section className="card-section">
        <p className="section-kicker">Why this works</p>
        <p className="lead">{option.reason}</p>
      </section>

      {hasStyleDetails ? (
        <div className="detail-grid">
          {option.trip_style ? (
            <section className="detail-card">
              <span>Trip style</span>
              <strong>{option.trip_style}</strong>
            </section>
          ) : null}
          {option.vibe ? (
            <section className="detail-card">
              <span>Mood</span>
              <strong>{option.vibe}</strong>
            </section>
          ) : null}
        </div>
      ) : null}

      {option.theme_explanation ? (
        <section className="card-section">
          <p className="section-kicker">Theme fit</p>
          <p>{option.theme_explanation}</p>
        </section>
      ) : null}

      {option.highlights?.length ? (
        <section className="card-section">
          <p className="section-kicker">Highlights</p>
          <ul className="plain-list">
            {option.highlights.map((highlight) => (
              <li key={highlight}>{highlight}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {tripPlan ? (
        <section className="card-section trip-plan-section">
          <p className="section-kicker">Trip note</p>
          {isTripPlanCollapsible && !isTripPlanExpanded ? (
            <p className="itinerary-preview">{getTripPlanPreview(tripPlan)}</p>
          ) : (
            <div className="markdown-body">
              <ReactMarkdown>{tripPlan}</ReactMarkdown>
            </div>
          )}
          {isTripPlanCollapsible ? (
            <button
              className="inline-link-button itinerary-toggle"
              type="button"
              onClick={() => setIsTripPlanExpanded((value) => !value)}
            >
              {isTripPlanExpanded ? "Collapse itinerary" : "Expand itinerary"}
            </button>
          ) : null}
        </section>
      ) : null}

      {(option.tradeoff || option.caveat) && !featured ? (
        <div className="detail-grid">
          {option.tradeoff ? (
            <section className="detail-card">
              <span>Tradeoff</span>
              <strong>{option.tradeoff}</strong>
            </section>
          ) : null}
          {option.caveat ? (
            <section className="detail-card">
              <span>Watch for</span>
              <strong>{option.caveat}</strong>
            </section>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}

function ResultSkeleton({ featured = false }) {
  const cardClassName = featured
    ? "card card-featured skeleton-card"
    : "card skeleton-card";

  return (
    <article className={cardClassName}>
      <div className="skeleton skeleton-badge-row" />
      <div className="skeleton skeleton-title" />
      <div className="skeleton skeleton-text" />
      <div className="skeleton skeleton-text skeleton-text-short" />
      <div className="detail-grid">
        <div className="detail-card">
          <div className="skeleton skeleton-detail" />
        </div>
        <div className="detail-card">
          <div className="skeleton skeleton-detail" />
        </div>
      </div>
      <div className="skeleton skeleton-block" />
    </article>
  );
}

function AccountPanel({
  authMode,
  authEmail,
  authPassword,
  authUser,
  authErrorText,
  isAuthLoading,
  onAuthEmailChange,
  onAuthModeChange,
  onAuthPasswordChange,
  onAuthSubmit,
  onLogout,
}) {
  const submitLabel = authMode === "login" ? "Sign in" : "Create account";

  return (
    <aside className="hero-panel account-panel">
      <div className="account-header">
        <p className="section-kicker">Account</p>
        <h2>
          {authUser ? "Search history is active" : "Sign in to save searches"}
        </h2>
      </div>

      {authUser ? (
        <div className="account-summary">
          <div className="account-summary-card">
            <span>Signed in as</span>
            <strong>{authUser.email}</strong>
          </div>
          <p className="account-note">
            Every new search is saved automatically and can be reopened below.
          </p>
          <button className="secondary-button" type="button" onClick={onLogout}>
            Sign out
          </button>
        </div>
      ) : (
        <>
          <p className="account-note">
            Search still works without an account, but results will not be
            saved.
          </p>

          <div className="auth-toggle">
            <button
              className={
                authMode === "login"
                  ? "secondary-button secondary-button-active"
                  : "secondary-button"
              }
              type="button"
              onClick={() => onAuthModeChange("login")}
            >
              Sign in
            </button>
            <button
              className={
                authMode === "register"
                  ? "secondary-button secondary-button-active"
                  : "secondary-button"
              }
              type="button"
              onClick={() => onAuthModeChange("register")}
            >
              Create account
            </button>
          </div>

          <form className="account-form" onSubmit={onAuthSubmit}>
            <label className="field">
              <span>Email</span>
              <input
                type="email"
                value={authEmail}
                onChange={(event) => onAuthEmailChange(event.target.value)}
                placeholder="you@example.com"
              />
            </label>

            <label className="field">
              <span>Password</span>
              <input
                type="password"
                value={authPassword}
                onChange={(event) => onAuthPasswordChange(event.target.value)}
                placeholder="At least 8 characters"
              />
            </label>

            {authErrorText ? (
              <p className="inline-hint inline-hint-error">{authErrorText}</p>
            ) : null}

            <button
              className="cta-button account-submit"
              type="submit"
              disabled={isAuthLoading}
            >
              {isAuthLoading ? "Working..." : submitLabel}
            </button>
          </form>
        </>
      )}
    </aside>
  );
}

function SavedSearchesPanel({
  activeSavedSearchId,
  authUser,
  isLoading,
  items,
  errorText,
  onSelect,
}) {
  return (
    <section className="saved-searches-panel">
      <div className="saved-searches-header">
        <div>
          <p className="section-kicker">Saved searches</p>
          <h3>Recent history</h3>
        </div>
        {authUser ? (
          <span className="saved-count">{items.length} saved</span>
        ) : null}
      </div>

      {!authUser ? (
        <p className="account-note">
          Sign in to keep searches and reopen them later without running a new
          query.
        </p>
      ) : null}

      {authUser && errorText ? (
        <p className="inline-hint inline-hint-error">{errorText}</p>
      ) : null}

      {authUser && isLoading ? (
        <p className="account-note">Loading saved searches...</p>
      ) : null}

      {authUser && !isLoading && items.length === 0 ? (
        <p className="account-note">
          No saved searches yet. Run a search while signed in and it will appear
          here.
        </p>
      ) : null}

      {authUser && items.length > 0 ? (
        <div className="history-list">
          {items.map((item) => {
            const itemClassName =
              item.id === activeSavedSearchId
                ? "history-item history-item-active"
                : "history-item";

            return (
              <button
                className={itemClassName}
                key={item.id}
                type="button"
                onClick={() => onSelect(item.id)}
              >
                <div className="history-item-topline">
                  <strong>{item.summary_destination || "Saved search"}</strong>
                  {typeof item.summary_price_usd === "number" ? (
                    <span>{formatCurrency(item.summary_price_usd)}</span>
                  ) : null}
                </div>
                <span className="history-item-meta">
                  {item.origin_city} · {formatDateLabel(item.start_date)} -{" "}
                  {formatDateLabel(item.end_date)}
                </span>
                <span className="history-item-meta">
                  {item.themes
                    .map((theme) => formatThemeLabel(theme))
                    .join(", ")}
                </span>
                <span className="history-item-meta">
                  {formatDateTimeLabel(item.created_at)}
                </span>
              </button>
            );
          })}
        </div>
      ) : null}
    </section>
  );
}

export default function App() {
  const [originCity, setOriginCity] = useState("Belgrade");
  const [startDate, setStartDate] = useState(DEFAULT_START_DATE);
  const [endDate, setEndDate] = useState(DEFAULT_END_DATE);
  const [budgetUsd, setBudgetUsd] = useState("2000");
  const [themes, setThemes] = useState(["beach", "history"]);
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorText, setErrorText] = useState("");
  const [resultStatusText, setResultStatusText] = useState("");
  const [searchContext, setSearchContext] = useState(null);
  const [authMode, setAuthMode] = useState("login");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authToken, setAuthToken] = useState(getStoredAuthToken);
  const [authUser, setAuthUser] = useState(null);
  const [authErrorText, setAuthErrorText] = useState("");
  const [isAuthLoading, setIsAuthLoading] = useState(false);
  const [savedSearches, setSavedSearches] = useState([]);
  const [savedSearchesError, setSavedSearchesError] = useState("");
  const [isSavedSearchesLoading, setIsSavedSearchesLoading] = useState(false);
  const [activeSavedSearchId, setActiveSavedSearchId] = useState(null);
  const [loadingStepIndex, setLoadingStepIndex] = useState(0);
  const searchShellRef = useRef(null);

  const isBudgetValid = Number(budgetUsd) >= 100;
  const isDateRangeValid =
    Boolean(startDate && endDate) &&
    parseDateInputValue(endDate) > parseDateInputValue(startDate);

  const canSubmit = useMemo(() => {
    if (!originCity.trim()) return false;
    if (!isBudgetValid) return false;
    if (themes.length === 0) return false;
    return isDateRangeValid;
  }, [isBudgetValid, isDateRangeValid, originCity, themes]);

  useEffect(() => {
    if (!authToken) return;

    async function bootstrapSession() {
      setIsAuthLoading(true);
      try {
        const user = await fetchJson("/auth/me", { token: authToken });
        setAuthUser(user);
        setAuthErrorText("");
        await loadSavedSearches(authToken);
      } catch {
        storeAuthToken("");
        setAuthToken("");
        setAuthUser(null);
        setSavedSearches([]);
      } finally {
        setIsAuthLoading(false);
      }
    }

    void bootstrapSession();
  }, []);

  useEffect(() => {
    if (!isLoading) {
      setLoadingStepIndex(0);
      return;
    }

    setLoadingStepIndex(0);
    const intervalId = window.setInterval(() => {
      setLoadingStepIndex((index) =>
        Math.min(index + 1, AI_LOADING_STEPS.length - 1),
      );
    }, 1200);

    return () => window.clearInterval(intervalId);
  }, [isLoading]);

  async function loadSavedSearches(tokenOverride = authToken) {
    if (!tokenOverride) {
      setSavedSearches([]);
      setSavedSearchesError("");
      return;
    }

    setIsSavedSearchesLoading(true);
    try {
      const items = await fetchJson("/searches", { token: tokenOverride });
      setSavedSearches(items || []);
      setSavedSearchesError("");
    } catch (error) {
      setSavedSearchesError(error.message || "Failed to load saved searches");
    } finally {
      setIsSavedSearchesLoading(false);
    }
  }

  function toggleTheme(theme) {
    setThemes((current) => {
      if (current.includes(theme)) {
        return current.filter((item) => item !== theme);
      }
      if (current.length >= 5) {
        return current;
      }
      return [...current, theme];
    });
  }

  function applySearchContext(searchPayload) {
    const context = buildSearchContextFromPayload(searchPayload);
    setOriginCity(context.originCity);
    setStartDate(context.startDate);
    setEndDate(context.endDate);
    setBudgetUsd(String(context.budgetUsd));
    setThemes(context.themes);
    setSearchContext(context);
  }

  async function handleAuthSubmit(event) {
    event.preventDefault();
    setIsAuthLoading(true);
    setAuthErrorText("");

    try {
      const data = await fetchJson(`/auth/${authMode}`, {
        method: "POST",
        body: JSON.stringify({
          email: authEmail,
          password: authPassword,
        }),
      });
      const nextToken = data.access_token || "";
      setAuthToken(nextToken);
      setAuthUser(data.user || null);
      setAuthPassword("");
      storeAuthToken(nextToken);
      await loadSavedSearches(nextToken);
      setResultStatusText("Future searches will now be saved to your account.");
    } catch (error) {
      setAuthErrorText(error.message || "Authentication failed");
    } finally {
      setIsAuthLoading(false);
    }
  }

  async function handleLogout() {
    try {
      if (authToken) {
        await fetchJson("/auth/logout", {
          method: "POST",
          token: authToken,
        });
      }
    } catch {
      // clear local session even if logout request fails
    } finally {
      storeAuthToken("");
      setAuthToken("");
      setAuthUser(null);
      setSavedSearches([]);
      setSavedSearchesError("");
      setActiveSavedSearchId(null);
      setResultStatusText("Signed out. New searches will not be saved.");
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const payload = {
      origin_city: originCity.trim(),
      dates_mode: "strict",
      themes,
      budget_usd: Number(budgetUsd),
      travelers_count: 2,
      strict_dates: {
        start_date: startDate,
        end_date: endDate,
      },
    };

    setIsLoading(true);
    setErrorText("");
    setResultStatusText("");
    setResult(null);
    setActiveSavedSearchId(null);
    applySearchContext(payload);

    try {
      const data = await fetchJson("/search", {
        method: "POST",
        token: authToken,
        body: JSON.stringify(payload),
      });

      setResult(normalizeResultPayload(data));

      if (data?.saved_search_id) {
        setResultStatusText("Saved to your account.");
        setActiveSavedSearchId(data.saved_search_id);
        await loadSavedSearches(authToken);
      } else if (!authUser) {
        setResultStatusText("Search complete. Sign in to save future results.");
      }
    } catch (error) {
      setResult(null);
      setErrorText(error.message || "Unexpected error");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleLoadSavedSearch(savedSearchId) {
    if (!authToken) return;

    setIsSavedSearchesLoading(true);
    setSavedSearchesError("");
    setErrorText("");
    setResultStatusText("");
    try {
      const data = await fetchJson(`/searches/${savedSearchId}`, {
        token: authToken,
      });
      applySearchContext(data.request_payload);
      setResult(normalizeResultPayload(data.response_payload, savedSearchId));
      setActiveSavedSearchId(savedSearchId);
      setResultStatusText("Loaded from saved searches.");
    } catch (error) {
      setSavedSearchesError(error.message || "Failed to load saved search");
    } finally {
      setIsSavedSearchesLoading(false);
    }
  }

  function handleEditSearch() {
    searchShellRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }

  const options = result?.options || [];
  const featuredOption = options[0] || null;
  const alternativeOptions = options.slice(1);
  const guidance = result?.guidance || {
    improvement_hint: "",
    counterfactual: "",
  };
  const meta = result?.meta;
  const selectedThemeLabels = themes.map((theme) => formatThemeLabel(theme));
  let resultsTitle = "Search to see ranked destination ideas";

  if (isLoading) {
    resultsTitle = "Finding your best-fit trip";
  } else if (searchContext && options.length > 0) {
    resultsTitle = `${options.length} ranked option${options.length === 1 ? "" : "s"}`;
  } else if (searchContext) {
    resultsTitle = "No matching options yet";
  }

  return (
    <main className="page">
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Flight shortlist</p>
          <h1>
            Find a trip that fits the brief,
            <br className="hero-title-break" />
            not just the route map.
          </h1>
          <p className="hero-text">
            Compare a small set of destination ideas ranked against your budget
            and travel themes, then keep every useful result in your account.
          </p>

          <div className="hero-points">
            <div className="hero-point">
              <strong>Up to 3 ranked options</strong>
              <span>One lead recommendation, then alternatives.</span>
            </div>
            <div className="hero-point">
              <strong>Searches can persist</strong>
              <span>Sign in once and each query is saved automatically.</span>
            </div>
            <div className="hero-point">
              <strong>Trip notes when available</strong>
              <span>
                Extra context appears directly inside the result cards.
              </span>
            </div>
          </div>
        </div>

        <AccountPanel
          authMode={authMode}
          authEmail={authEmail}
          authPassword={authPassword}
          authUser={authUser}
          authErrorText={authErrorText}
          isAuthLoading={isAuthLoading}
          onAuthEmailChange={setAuthEmail}
          onAuthModeChange={setAuthMode}
          onAuthPasswordChange={setAuthPassword}
          onAuthSubmit={handleAuthSubmit}
          onLogout={handleLogout}
        />
      </section>

      <section className="search-shell" ref={searchShellRef}>
        <div className="search-shell-header">
          <div>
            <p className="section-kicker">Search setup</p>
            <h2>Build the trip brief</h2>
          </div>
          <p className="form-note">Budget is shown as total for 2 travelers.</p>
        </div>

        <form className="search-form" onSubmit={handleSubmit}>
          <div className="field-grid field-grid-main">
            <label className="field">
              <span>Origin city</span>
              <input
                value={originCity}
                onChange={(event) => setOriginCity(event.target.value)}
                placeholder="Belgrade"
              />
            </label>

            <label className="field">
              <span>Total budget</span>
              <input
                type="number"
                min="100"
                value={budgetUsd}
                onChange={(event) => setBudgetUsd(event.target.value)}
              />
              <small>
                Shown and ranked as a total budget for two travelers.
              </small>
            </label>
          </div>

          <div className="field-grid">
            <label className="field">
              <span>Start date</span>
              <input
                type="date"
                value={startDate}
                onChange={(event) => setStartDate(event.target.value)}
              />
            </label>

            <label className="field">
              <span>End date</span>
              <input
                type="date"
                value={endDate}
                onChange={(event) => setEndDate(event.target.value)}
              />
            </label>
          </div>

          {!isDateRangeValid ? (
            <p className="inline-hint inline-hint-warning">
              End date must be after start date.
            </p>
          ) : null}

          <div className="theme-panel">
            <div className="theme-panel-header">
              <div>
                <p className="section-kicker">Themes</p>
                <h3>{themes.length} of 5 selected</h3>
              </div>
              <p className="form-note">
                Pick the travel styles that should drive the ranking.
              </p>
            </div>

            <div className="chips">
              {THEMES.map((theme) => {
                const isActive = themes.includes(theme.value);
                return (
                  <button
                    key={theme.value}
                    type="button"
                    className={isActive ? "chip chip-active" : "chip"}
                    onClick={() => toggleTheme(theme.value)}
                  >
                    {theme.label}
                  </button>
                );
              })}
            </div>

            <p className="inline-hint">
              Selected: {selectedThemeLabels.join(", ")}
            </p>
          </div>

          <div className="search-actions">
            <div className="search-actions-copy">
              <strong>
                {getTripLengthLabel(startDate, endDate) ||
                  "Trip length pending"}
              </strong>
              <span>
                {authUser
                  ? "Run the search and save the snapshot automatically."
                  : "Run the search now, or sign in first to save the result."}
              </span>
            </div>
            <button
              className="cta-button"
              type="submit"
              disabled={!canSubmit || isLoading}
            >
              {isLoading ? "Searching..." : "Show recommendations"}
            </button>
          </div>
        </form>
      </section>

      {errorText ? (
        <p className="status-banner status-banner-error">
          Search failed. {errorText}
        </p>
      ) : null}

      {resultStatusText ? (
        <p className="status-banner status-banner-info">{resultStatusText}</p>
      ) : null}

      {isLoading ? (
        <div className="status-banner status-banner-info ai-loading-banner">
          {AI_LOADING_STEPS.map((step, index) => (
            <p
              className={
                index === loadingStepIndex
                  ? "ai-loading-step ai-loading-step-active"
                  : "ai-loading-step"
              }
              key={step}
            >
              {step}
            </p>
          ))}
        </div>
      ) : null}

      <section className="results-section">
        <div className="results-layout">
          <div className="results-main">
            <div className="results-heading">
              <p className="section-kicker">Recommendations</p>
              <h2>{resultsTitle}</h2>
              <p className="hero-text">
                {searchContext
                  ? "Results are organized as one main recommendation plus any remaining alternatives."
                  : "Set the brief above to compare a focused shortlist instead of scanning a long list."}
              </p>
            </div>

            <ResultMeta meta={meta} />
            <GuidancePanel guidance={guidance} />

            {isLoading ? (
              <div className="results-stack">
                <ResultSkeleton featured />
                <div className="alternative-grid">
                  <ResultSkeleton />
                  <ResultSkeleton />
                </div>
              </div>
            ) : null}

            {!isLoading && !searchContext ? (
              <div className="empty-state">
                <h3>Start with a trip brief</h3>
                <p>
                  Choose dates, a budget, and a few themes to get a compact set
                  of ranked destination ideas.
                </p>
              </div>
            ) : null}

            {!isLoading && searchContext && options.length === 0 ? (
              <div className="empty-state">
                <h3>No options matched this search</h3>
                <p>
                  Try widening the dates, increasing the budget, or simplifying
                  the selected themes.
                </p>
              </div>
            ) : null}

            {!isLoading && featuredOption ? (
              <div className="results-stack">
                <OptionCard
                  option={featuredOption}
                  index={0}
                  options={options}
                  featured
                />

                {alternativeOptions.length ? (
                  <section className="alternatives-section">
                    <div className="alternatives-header">
                      <p className="section-kicker">Alternatives</p>
                      <h3>Other options worth considering</h3>
                    </div>
                    <div className="alternative-grid">
                      {alternativeOptions.map((option, optionIndex) => (
                        <OptionCard
                          key={option.option_id}
                          option={option}
                          index={optionIndex + 1}
                          options={options}
                        />
                      ))}
                    </div>
                  </section>
                ) : null}
              </div>
            ) : null}
          </div>

          <div className="results-sidebar">
            <SearchSummary
              onEditSearch={handleEditSearch}
              searchContext={searchContext}
            />
            <SavedSearchesPanel
              activeSavedSearchId={activeSavedSearchId}
              authUser={authUser}
              isLoading={isSavedSearchesLoading}
              items={savedSearches}
              errorText={savedSearchesError}
              onSelect={handleLoadSavedSearch}
            />
          </div>
        </div>
      </section>
    </main>
  );
}
