import { useState } from "react";
import { fetchJson } from "../api/client";

export function useReactions({ onSignInRequired, onCountsUpdated }) {
  const [stateBySuggestionId, setStateBySuggestionId] = useState({});

  function reset() {
    setStateBySuggestionId({});
  }

  function getReactionProps(option) {
    const state = option.suggestion_id
      ? stateBySuggestionId[option.suggestion_id]
      : null;
    return {
      reactionValue: state?.reaction || "",
      reactionErrorText: state?.errorText || "",
      isReactionLoading: Boolean(state?.isLoading),
    };
  }

  async function react(token, suggestionId, reaction) {
    if (!token) {
      onSignInRequired();
      return;
    }
    if (!suggestionId) {
      return;
    }

    setStateBySuggestionId((current) => ({
      ...current,
      [suggestionId]: {
        ...current[suggestionId],
        isLoading: true,
        errorText: "",
      },
    }));

    try {
      const response = await fetchJson(
        `/search/suggestions/${suggestionId}/reaction`,
        {
          method: "POST",
          token,
          body: JSON.stringify({ reaction }),
        },
      );

      setStateBySuggestionId((current) => ({
        ...current,
        [suggestionId]: {
          reaction: response.reaction,
          isLoading: false,
          errorText: "",
        },
      }));
      onCountsUpdated(suggestionId, response);
    } catch (error) {
      setStateBySuggestionId((current) => ({
        ...current,
        [suggestionId]: {
          ...current[suggestionId],
          isLoading: false,
          errorText: error.message || "Failed to save reaction",
        },
      }));
    }
  }

  return { getReactionProps, react, reset };
}
