import { createElement, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8100";
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

function toDateInputValue(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

const DEFAULT_START_DATE = toDateInputValue(new Date());
const DEFAULT_END_DATE = toDateInputValue(new Date(Date.now() + 3 * DAY_IN_MS));

export default function App() {
  const [originCity, setOriginCity] = useState("Belgrade");
  const [startDate, setStartDate] = useState(DEFAULT_START_DATE);
  const [endDate, setEndDate] = useState(DEFAULT_END_DATE);
  const [budgetUsd, setBudgetUsd] = useState("2000");
  const [themes, setThemes] = useState(["beach", "history"]);
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorText, setErrorText] = useState("");

  const canSubmit = useMemo(() => {
    if (!originCity.trim()) return false;
    if (!budgetUsd) return false;
    if (themes.length === 0) return false;
    return Boolean(startDate && endDate);
  }, [budgetUsd, endDate, originCity, startDate, themes]);

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

  async function handleSubmit(event) {
    event.preventDefault();
    setIsLoading(true);
    setErrorText("");

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

    try {
      const response = await fetch(`${BACKEND_URL}/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        let errorMessage = "Search request failed";
        try {
          const errorBody = await response.json();
          errorMessage =
            errorBody?.error?.message ||
            errorBody?.detail?.[0]?.msg ||
            errorBody?.detail ||
            errorMessage;
        } catch {
          // keep default message when response body is not JSON
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();
      setResult({
        options: data.options || [],
        guidance: data.guidance || {
          improvement_hint: "",
          counterfactual: "",
        },
        meta: data.meta || null,
        trip_plan: data.trip_plan || "",
      });
    } catch (error) {
      setResult(null);
      setErrorText(error.message || "Unexpected error");
    } finally {
      setIsLoading(false);
    }
  }

  const options = result?.options || [];
  const guidance = result?.guidance || {
    improvement_hint: "",
    counterfactual: "",
  };
  const meta = result?.meta;

  return (
    <main className="page">
      <h1>tickets_app search</h1>

      <form className="search-form" onSubmit={handleSubmit}>
        <label>
          Origin city
          <input
            value={originCity}
            onChange={(event) => setOriginCity(event.target.value)}
          />
        </label>

        <div className="grid2">
          <label>
            Start date
            <input
              type="date"
              value={startDate}
              onChange={(event) => setStartDate(event.target.value)}
            />
          </label>
          <label>
            End date
            <input
              type="date"
              value={endDate}
              onChange={(event) => setEndDate(event.target.value)}
            />
          </label>
        </div>

        <label>
          Budget USD (total for 2)
          <input
            type="number"
            min="100"
            value={budgetUsd}
            onChange={(event) => setBudgetUsd(event.target.value)}
          />
        </label>

        <div>
          <div className="label">Themes (max 5)</div>
          <div className="chips">
            {THEMES.map((theme) => (
              <button
                key={theme.value}
                type="button"
                className={
                  themes.includes(theme.value) ? "chip chip-active" : "chip"
                }
                onClick={() => toggleTheme(theme.value)}
              >
                {theme.label}
              </button>
            ))}
          </div>
        </div>

        <button type="submit" disabled={!canSubmit || isLoading}>
          {isLoading ? "Searching..." : "Search"}
        </button>
      </form>

      {errorText ? <p className="error">{errorText}</p> : null}

      <section>
        <h2>Top options</h2>
        {meta ? (
          <div className="meta-panel">
            <span className="meta-pill">Source: {meta.data_source}</span>
            <span className="meta-pill">Ranking: {meta.ranking_mode}</span>
            <span className="meta-pill">
              Enrichment: {meta.enrichment_mode}
            </span>
            <span className="meta-pill">
              Constraints relaxed: {meta.constraints_relaxed ? "yes" : "no"}
            </span>
          </div>
        ) : null}
        {guidance.improvement_hint || guidance.counterfactual ? (
          <div className="guidance-grid">
            {guidance.improvement_hint ? (
              <article className="guidance-card">
                <h3>How to improve results</h3>
                <p>{guidance.improvement_hint}</p>
              </article>
            ) : null}
            {guidance.counterfactual ? (
              <article className="guidance-card">
                <h3>Counterfactual</h3>
                <p>{guidance.counterfactual}</p>
              </article>
            ) : null}
          </div>
        ) : null}
        {options.length === 0 ? <p>No results yet.</p> : null}
        <div className="results">
          {options.map((option) => (
            <article className="card" key={option.option_id}>
              <div className="card-header">
                <div>
                  <h3>{option.destination_city}</h3>
                  <p className="route">
                    {option.origin_airport} → {option.destination_airport}
                  </p>
                </div>
                <div className="price-block">
                  <strong>${option.price_usd}</strong>
                  <span>Score {option.score}</span>
                </div>
              </div>

              <p className="lead">{option.reason}</p>

              {option.trip_plan ? (
                <section className="card-section">
                  <h4>Trip plan</h4>
                  <div className="markdown-body">
                    {createElement(ReactMarkdown, null, option.trip_plan)}
                  </div>
                </section>
              ) : null}

              {option.theme_explanation ? (
                <section className="card-section">
                  <h4>Theme fit</h4>
                  <p>{option.theme_explanation}</p>
                </section>
              ) : null}

              {option.highlights?.length ? (
                <section className="card-section">
                  <h4>Highlights</h4>
                  <ul className="plain-list">
                    {option.highlights.map((highlight) => (
                      <li key={highlight}>{highlight}</li>
                    ))}
                  </ul>
                </section>
              ) : null}

              <div className="detail-grid">
                {option.trip_style ? (
                  <section className="card-section detail-card">
                    <h4>Trip style</h4>
                    <p>{option.trip_style}</p>
                  </section>
                ) : null}
                {option.vibe ? (
                  <section className="card-section detail-card">
                    <h4>Vibe</h4>
                    <p>{option.vibe}</p>
                  </section>
                ) : null}
              </div>

              <div className="detail-grid">
                {option.tradeoff ? (
                  <section className="card-section detail-card">
                    <h4>Tradeoff</h4>
                    <p>{option.tradeoff}</p>
                  </section>
                ) : null}
                {option.caveat ? (
                  <section className="card-section detail-card">
                    <h4>Caveat</h4>
                    <p>{option.caveat}</p>
                  </section>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
