import { useMemo } from "react";
import { THEMES } from "../config/constants";
import {
  formatThemeLabel,
  getTripLengthLabel,
  parseDateInputValue,
} from "../utils/format";

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

  const selectedThemeLabels = themes.map((theme) => formatThemeLabel(theme));

  return (
    <section className="search-shell" ref={shellRef}>
      <div className="search-shell-header">
        <div>
          <p className="section-kicker">Search setup</p>
          <h2>Build the trip brief</h2>
        </div>
        <p className="form-note">Budget is shown as total for 2 travelers.</p>
      </div>

      <form className="search-form" onSubmit={onSubmit}>
        <div className="field-grid field-grid-main">
          <label className="field">
            <span>Origin city</span>
            <input
              value={originCity}
              onChange={(event) => onOriginCityChange(event.target.value)}
              placeholder="Belgrade"
            />
          </label>

          <label className="field">
            <span>Total budget</span>
            <input
              type="number"
              min="100"
              value={budgetUsd}
              onChange={(event) => onBudgetChange(event.target.value)}
            />
            <small>Shown and ranked as a total budget for two travelers.</small>
          </label>
        </div>

        <div className="field-grid">
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
                  onClick={() => onToggleTheme(theme.value)}
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
              {getTripLengthLabel(startDate, endDate) || "Trip length pending"}
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
  );
}
