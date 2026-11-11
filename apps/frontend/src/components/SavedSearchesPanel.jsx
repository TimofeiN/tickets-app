import {
  formatCurrency,
  formatDateLabel,
  formatDateTimeLabel,
  formatThemeLabel,
} from "../utils/format";

export function SavedSearchesPanel({
  activeSavedSearchId,
  authUser,
  isLoading,
  items,
  errorText,
  onSelect,
}) {
  return (
    <section className="panel">
      <div className="panel-title panel-title-row">
        <h2>Saved searches</h2>
        {authUser ? <span>{items.length}</span> : null}
      </div>
      <div className="panel-body">
        {!authUser ? (
          <p className="note">
            Sign in to keep searches and reopen them later without running a new
            query.
          </p>
        ) : null}

        {authUser && errorText ? (
          <p className="inline-hint inline-hint-error">{errorText}</p>
        ) : null}

        {authUser && isLoading ? (
          <p className="note">Loading saved searches...</p>
        ) : null}

        {authUser && !isLoading && items.length === 0 ? (
          <p className="note">
            No saved searches yet. Run a search while signed in and it will
            appear here.
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
                    <strong>
                      {item.summary_destination || "Saved search"}
                    </strong>
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
      </div>
    </section>
  );
}
