import { useMemo, useState } from "react";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";
const THEMES = [
  { value: "beach", label: "Beach" },
  { value: "history", label: "History" },
  { value: "active_summer", label: "Active summer" },
  { value: "active_winter", label: "Active winter" },
  { value: "gastronomy", label: "Gastronomy" },
  { value: "family", label: "Family" },
  { value: "nightlife", label: "Nightlife" }
];

export default function App() {
  const [originCity, setOriginCity] = useState("Belgrade");
  const [datesMode, setDatesMode] = useState("strict");
  const [startDate, setStartDate] = useState("2026-06-10");
  const [endDate, setEndDate] = useState("2026-06-17");
  const [flexYear, setFlexYear] = useState("2026");
  const [flexMonth, setFlexMonth] = useState("6");
  const [tripLengthDays, setTripLengthDays] = useState("7");
  const [budgetUsd, setBudgetUsd] = useState("2000");
  const [themes, setThemes] = useState(["beach", "history"]);
  const [options, setOptions] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorText, setErrorText] = useState("");

  const canSubmit = useMemo(() => {
    if (!originCity.trim()) return false;
    if (!budgetUsd) return false;
    if (themes.length === 0) return false;
    if (datesMode === "strict") return Boolean(startDate && endDate);
    return Boolean(flexYear && flexMonth && tripLengthDays);
  }, [budgetUsd, datesMode, endDate, flexMonth, flexYear, originCity, startDate, themes, tripLengthDays]);

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
      dates_mode: datesMode,
      themes,
      budget_usd: Number(budgetUsd),
      travelers_count: 2
    };

    if (datesMode === "strict") {
      payload.strict_dates = {
        start_date: startDate,
        end_date: endDate
      };
    } else {
      payload.flexible_dates = {
        year: Number(flexYear),
        month: Number(flexMonth),
        trip_length_days: Number(tripLengthDays)
      };
    }

    try {
      const response = await fetch(`${BACKEND_URL}/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errorBody = await response.json();
        throw new Error(errorBody?.detail?.[0]?.msg || "Search request failed");
      }

      const data = await response.json();
      setOptions(data.options || []);
    } catch (error) {
      setOptions([]);
      setErrorText(error.message || "Unexpected error");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="page">
      <h1>tickets_app search</h1>

      <form className="search-form" onSubmit={handleSubmit}>
        <label>
          Origin city
          <input value={originCity} onChange={(event) => setOriginCity(event.target.value)} />
        </label>

        <label>
          Dates mode
          <select value={datesMode} onChange={(event) => setDatesMode(event.target.value)}>
            <option value="strict">Strict</option>
            <option value="flexible">Flexible</option>
          </select>
        </label>

        {datesMode === "strict" ? (
          <div className="grid2">
            <label>
              Start date
              <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
            </label>
            <label>
              End date
              <input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} />
            </label>
          </div>
        ) : (
          <div className="grid3">
            <label>
              Year
              <input value={flexYear} onChange={(event) => setFlexYear(event.target.value)} />
            </label>
            <label>
              Month
              <input value={flexMonth} onChange={(event) => setFlexMonth(event.target.value)} />
            </label>
            <label>
              Trip length days
              <input value={tripLengthDays} onChange={(event) => setTripLengthDays(event.target.value)} />
            </label>
          </div>
        )}

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
                className={themes.includes(theme.value) ? "chip chip-active" : "chip"}
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
        {options.length === 0 ? <p>No results yet.</p> : null}
        <div className="results">
          {options.map((option) => (
            <article className="card" key={option.option_id}>
              <h3>{option.destination_city}</h3>
              <p>
                {option.origin_airport} → {option.destination_airport}
              </p>
              <p>Price: ${option.price_usd}</p>
              <p>Score: {option.score}</p>
              <p>{option.reason}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
