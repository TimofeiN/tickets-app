export function HeroCopy() {
  return (
    <div className="hero-copy">
      <p className="eyebrow">Flight shortlist</p>
      <h1>
        Find a trip that fits the brief,
        <br className="hero-title-break" />
        not just the route map.
      </h1>
      <p className="hero-text">
        Compare a small set of destination ideas ranked against your budget and
        travel themes, then keep every useful result in your account.
      </p>

      <div className="hero-points">
        <div className="hero-point">
          <strong>Up to 3 ranked options</strong>
          <span>One lead recommendation, then alternatives.</span>
        </div>
        <div className="hero-point">
          <strong>Searches can persist</strong>
          <span>Sign in once and each query is saved automatically.</span>
        </div>
        <div className="hero-point">
          <strong>Trip notes when available</strong>
          <span>Extra context appears directly inside the result cards.</span>
        </div>
      </div>
    </div>
  );
}
