export function ResultSkeleton() {
  return (
    <article className="option-row" aria-hidden="true">
      <div className="option-code">
        <div className="skeleton skeleton-code" />
      </div>
      <div className="option-body">
        <div className="skeleton skeleton-title" />
        <div className="skeleton skeleton-text" />
        <div className="skeleton skeleton-text skeleton-text-short" />
      </div>
      <div className="option-side">
        <div className="skeleton skeleton-price" />
      </div>
    </article>
  );
}
