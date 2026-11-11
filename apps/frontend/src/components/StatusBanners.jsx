import { AI_LOADING_STEPS } from "../config/constants";

export function StatusBanners({
  errorText,
  resultStatusText,
  isLoading,
  loadingStepIndex,
}) {
  return (
    <>
      {errorText ? (
        <p className="status-banner status-banner-error">
          Search failed. {errorText}
        </p>
      ) : null}

      {resultStatusText ? (
        <p className="status-banner status-banner-info">{resultStatusText}</p>
      ) : null}

      {isLoading ? (
        <div className="status-banner status-banner-info ai-loading-banner">
          {AI_LOADING_STEPS.map((step, index) => (
            <p
              className={
                index === loadingStepIndex
                  ? "ai-loading-step ai-loading-step-active"
                  : "ai-loading-step"
              }
              key={step}
            >
              {step}
            </p>
          ))}
        </div>
      ) : null}
    </>
  );
}
