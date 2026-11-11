import { useEffect, useState } from "react";

const STEP_INTERVAL_MS = 1200;

export function useLoadingStep(isLoading, stepCount) {
  const [stepIndex, setStepIndex] = useState(0);

  useEffect(() => {
    setStepIndex(0);
    if (!isLoading) return undefined;

    const intervalId = window.setInterval(() => {
      setStepIndex((index) => Math.min(index + 1, stepCount - 1));
    }, STEP_INTERVAL_MS);

    return () => window.clearInterval(intervalId);
  }, [isLoading, stepCount]);

  return stepIndex;
}
