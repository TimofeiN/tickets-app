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
      <div className="results-bar">
        <strong>{resultsTitle}</strong>
      </div>

      <ResultMeta meta={meta} />
      <GuidancePanel guidance={guidance} />

      {isLoading ? (
        <section className="panel">
          <ResultSkeleton />
          <ResultSkeleton />
          <ResultSkeleton />
        </section>
      ) : null}

      {!isLoading && !searchContext ? (
        <section className="panel empty-state">
          <h3>Start with a trip brief</h3>
          <p>
            Choose dates, a budget, and a few themes to get a compact set of
            ranked destination ideas.
          </p>
        </section>
      ) : null}

      {!isLoading && searchContext && options.length === 0 ? (
        <section className="panel empty-state">
          <h3>No options matched this search</h3>
          <p>
            Try widening the dates, increasing the budget, or simplifying the
            selected themes.
          </p>
        </section>
      ) : null}

      {!isLoading && options.length > 0 ? (
        <section className="panel">
          {options.map((option, optionIndex) => (
            <OptionCard
              key={option.option_id}
              option={option}
              index={optionIndex}
              options={options}
              featured={optionIndex === 0}
              canReact={Boolean(authUser)}
              {...getReactionProps(option)}
              onReact={onReact}
            />
          ))}
        </section>
      ) : null}
    </div>
  );
}
