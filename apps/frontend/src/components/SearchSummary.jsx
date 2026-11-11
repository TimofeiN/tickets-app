import {
  formatCurrency,
  formatDateLabel,
  formatThemeLabel,
  getTripLengthLabel,
} from "../utils/format";

export function SearchSummary({ searchContext, onEditSearch }) {
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
