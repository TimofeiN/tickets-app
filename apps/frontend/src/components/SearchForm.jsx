import { useMemo } from "react";
import { THEMES } from "../config/constants";
import { getTripLengthLabel, parseDateInputValue } from "../utils/format";

export function SearchForm({
  shellRef,
  originCity,
  budgetUsd,
  startDate,
  endDate,
  themes,
  authUser,
  isLoading,
  onOriginCityChange,
  onBudgetChange,
  onStartDateChange,
  onEndDateChange,
  onToggleTheme,
  onSubmit,
}) {
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

  return (
    <section className="panel search-panel" ref={shellRef}>
      <h2 className="panel-title">Search</h2>

      <form onSubmit={onSubmit}>
        <div className="search-fields">
          <label className="field">
            <span>Origin city</span>
            <input
              value={originCity}
              onChange={(event) => onOriginCityChange(event.target.value)}
              placeholder="Belgrade"
            />
          </label>

          <label className="field">
            <span>Start date</span>
            <input
              type="date"
              value={startDate}
              onChange={(event) => onStartDateChange(event.target.value)}
            />
          </label>

          <label className="field">
            <span>End date</span>
            <input
              type="date"
              value={endDate}
              onChange={(event) => onEndDateChange(event.target.value)}
            />
          </label>

          <label className="field">
            <span>Total budget, USD</span>
            <input
              type="number"
              min="100"
              value={budgetUsd}
              onChange={(event) => onBudgetChange(event.target.value)}
            />
            <small>For 2 travelers</small>
          </label>
        </div>

        {!isDateRangeValid ? (
          <p className="inline-hint inline-hint-warning search-themes">
            End date must be after start date.
          </p>
        ) : null}

        <div className="search-themes">
          <div className="search-themes-head">
            <span>Themes</span>
            <span>{themes.length} of 5 selected</span>
          </div>

          <div className="chips">
            {THEMES.map((theme) => {
              const isActive = themes.includes(theme.value);
              return (
                <button
                  key={theme.value}
                  type="button"
                  className={isActive ? "chip chip-active" : "chip"}
                  aria-pressed={isActive}
                  onClick={() => onToggleTheme(theme.value)}
                >
                  {theme.label}
                </button>
              );
            })}
          </div>
        </div>

        <div className="search-actions">
          <div className="search-actions-copy">
            <strong>
              {getTripLengthLabel(startDate, endDate) || "Trip length pending"}
            </strong>
            <span>
              {authUser
                ? "The result is saved to your account."
                : "Sign in first to save the result."}
            </span>
          </div>
          <button
            className="cta-button"
            type="submit"
            disabled={!canSubmit || isLoading}
          >
            {isLoading ? "Searching..." : "Show recommendations →"}
          </button>
        </div>
      </form>
    </section>
  );
}
