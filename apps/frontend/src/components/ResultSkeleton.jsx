export function ResultSkeleton({ featured = false }) {
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
