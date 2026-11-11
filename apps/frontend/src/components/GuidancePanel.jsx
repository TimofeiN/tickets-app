export function GuidancePanel({ guidance }) {
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
