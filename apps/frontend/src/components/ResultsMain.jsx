import { GuidancePanel } from "./GuidancePanel";
import { OptionCard } from "./OptionCard";
import { ResultMeta } from "./ResultMeta";
import { ResultSkeleton } from "./ResultSkeleton";

export function ResultsMain({
  isLoading,
  searchContext,
  result,
  authUser,
  getReactionProps,
  onReact,
}) {
  const options = result?.options || [];
  const featuredOption = options[0] || null;
  const alternativeOptions = options.slice(1);
  const guidance = result?.guidance || {
    improvement_hint: "",
    counterfactual: "",
  };
  const meta = result?.meta;
  let resultsTitle = "Search to see ranked destination ideas";

  if (isLoading) {
    resultsTitle = "Finding your best-fit trip";
  } else if (searchContext && options.length > 0) {
    resultsTitle = `${options.length} ranked option${options.length === 1 ? "" : "s"}`;
  } else if (searchContext) {
    resultsTitle = "No matching options yet";
  }

  return (
    <div className="results-main">
      <div className="results-heading">
        <p className="section-kicker">Recommendations</p>
        <h2>{resultsTitle}</h2>
        <p className="hero-text">
          {searchContext
            ? "Results are organized as one main recommendation plus any remaining alternatives."
            : "Set the brief above to compare a focused shortlist instead of scanning a long list."}
        </p>
      </div>

      <ResultMeta meta={meta} />
      <GuidancePanel guidance={guidance} />

      {isLoading ? (
        <div className="results-stack">
          <ResultSkeleton featured />
          <div className="alternative-grid">
            <ResultSkeleton />
            <ResultSkeleton />
          </div>
        </div>
      ) : null}

      {!isLoading && !searchContext ? (
        <div className="empty-state">
          <h3>Start with a trip brief</h3>
          <p>
            Choose dates, a budget, and a few themes to get a compact set of
            ranked destination ideas.
          </p>
        </div>
      ) : null}

      {!isLoading && searchContext && options.length === 0 ? (
        <div className="empty-state">
          <h3>No options matched this search</h3>
          <p>
            Try widening the dates, increasing the budget, or simplifying the
            selected themes.
          </p>
        </div>
      ) : null}

      {!isLoading && featuredOption ? (
        <div className="results-stack">
          <OptionCard
            option={featuredOption}
            index={0}
            options={options}
            featured
            canReact={Boolean(authUser)}
            {...getReactionProps(featuredOption)}
            onReact={onReact}
          />

          {alternativeOptions.length ? (
            <section className="alternatives-section">
              <div className="alternatives-header">
                <p className="section-kicker">Alternatives</p>
                <h3>Other options worth considering</h3>
              </div>
              <div className="alternative-grid">
                {alternativeOptions.map((option, optionIndex) => (
                  <OptionCard
                    key={option.option_id}
                    option={option}
                    index={optionIndex + 1}
                    options={options}
                    canReact={Boolean(authUser)}
                    {...getReactionProps(option)}
                    onReact={onReact}
                  />
                ))}
              </div>
            </section>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
