import { useState } from "react";
import { fetchJson } from "../api/client";

export function useSavedSearches() {
  const [items, setItems] = useState([]);
  const [errorText, setErrorText] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  async function load(token) {
    if (!token) {
      setItems([]);
      setErrorText("");
      return;
    }

    setIsLoading(true);
    try {
      const data = await fetchJson("/searches", { token });
      setItems(data || []);
      setErrorText("");
    } catch (error) {
      setErrorText(error.message || "Failed to load saved searches");
    } finally {
      setIsLoading(false);
    }
  }

  async function open(token, savedSearchId) {
    setIsLoading(true);
    setErrorText("");
    try {
      return await fetchJson(`/searches/${savedSearchId}`, { token });
    } catch (error) {
      setErrorText(error.message || "Failed to load saved search");
      return null;
    } finally {
      setIsLoading(false);
    }
  }

  function reset() {
    setItems([]);
    setErrorText("");
  }

  return { items, errorText, isLoading, load, open, reset };
}
