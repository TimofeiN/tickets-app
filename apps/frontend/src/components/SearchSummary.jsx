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
    <section className="panel">
      <div className="panel-title panel-title-row">
        <h2>Current search</h2>
        <button
          className="inline-link-button"
          type="button"
          onClick={onEditSearch}
        >
          Edit
        </button>
      </div>
      <div className="summary-grid">
        {summaryItems.map((item) => (
          <div className="summary-item" key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </div>
        ))}
      </div>
      <div className="summary-themes chips">
        {searchContext.themes.map((theme) => (
          <span className="chip chip-active" key={theme}>
            {formatThemeLabel(theme)}
          </span>
        ))}
      </div>
    </section>
  );
}
