export function normalizeResultPayload(data, savedSearchId = null) {
  return {
    options: data?.options || [],
    guidance: data?.guidance || {
      improvement_hint: "",
      counterfactual: "",
    },
    meta: data?.meta || null,
    savedSearchId: data?.saved_search_id || savedSearchId,
  };
}

export function buildSearchContextFromPayload(payload) {
  return {
    originCity: payload.origin_city,
    startDate: payload.strict_dates?.start_date || "",
    endDate: payload.strict_dates?.end_date || "",
    budgetUsd: payload.budget_usd,
    themes: payload.themes || [],
  };
}
