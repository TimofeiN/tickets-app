export function GuidancePanel({ guidance }) {
  if (!guidance?.improvement_hint && !guidance?.counterfactual) return null;

  return (
    <section className="panel">
      {guidance.improvement_hint ? (
        <article className="guidance-block">
          <h3>How to improve results</h3>
          <p>{guidance.improvement_hint}</p>
        </article>
      ) : null}
      {guidance.counterfactual ? (
        <article className="guidance-block">
          <h3>If priorities change</h3>
          <p>{guidance.counterfactual}</p>
        </article>
      ) : null}
    </section>
  );
}
