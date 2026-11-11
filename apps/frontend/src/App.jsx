import { useRef, useState } from "react";
import { fetchJson } from "./api/client";
import { AccountPanel } from "./components/AccountPanel";
import { HeroCopy } from "./components/HeroCopy";
import { ResultsMain } from "./components/ResultsMain";
import { SavedSearchesPanel } from "./components/SavedSearchesPanel";
import { SearchForm } from "./components/SearchForm";
import { SearchSummary } from "./components/SearchSummary";
import { StatusBanners } from "./components/StatusBanners";
import { AI_LOADING_STEPS, DAY_IN_MS } from "./config/constants";
import { useAuth } from "./hooks/useAuth";
import { useLoadingStep } from "./hooks/useLoadingStep";
import { useReactions } from "./hooks/useReactions";
import { useSavedSearches } from "./hooks/useSavedSearches";
import { toDateInputValue } from "./utils/format";
import {
  buildSearchContextFromPayload,
  normalizeResultPayload,
} from "./utils/searchPayload";

const DEFAULT_START_DATE = toDateInputValue(new Date());
const DEFAULT_END_DATE = toDateInputValue(new Date(Date.now() + 3 * DAY_IN_MS));
const MAX_THEMES = 5;

export default function App() {
  const [originCity, setOriginCity] = useState("Belgrade");
  const [startDate, setStartDate] = useState(DEFAULT_START_DATE);
  const [endDate, setEndDate] = useState(DEFAULT_END_DATE);
  const [budgetUsd, setBudgetUsd] = useState("2000");
  const [themes, setThemes] = useState(["beach", "history"]);
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorText, setErrorText] = useState("");
  const [resultStatusText, setResultStatusText] = useState("");
  const [searchContext, setSearchContext] = useState(null);
  const [activeSavedSearchId, setActiveSavedSearchId] = useState(null);
  const searchShellRef = useRef(null);

  const savedSearches = useSavedSearches();
  const reactions = useReactions({
    onSignInRequired: () => {
      setResultStatusText("Sign in to rate recommendations.");
    },
    onCountsUpdated: (suggestionId, response) => {
      setResult((current) => {
        if (!current) {
          return current;
        }
        return {
          ...current,
          options: (current.options || []).map((option) =>
            option.suggestion_id === suggestionId
              ? {
                  ...option,
                  likes: response.likes,
                  dislikes: response.dislikes,
                }
              : option,
          ),
        };
      });
    },
  });
  const auth = useAuth({
    onSessionRestored: (token) => savedSearches.load(token),
    onSessionExpired: () => savedSearches.reset(),
    onSignedIn: async (token) => {
      await savedSearches.load(token);
      setResultStatusText("Future searches will now be saved to your account.");
    },
    onSignedOut: () => {
      savedSearches.reset();
      setActiveSavedSearchId(null);
      reactions.reset();
      setResultStatusText("Signed out. New searches will not be saved.");
    },
  });
  const loadingStepIndex = useLoadingStep(isLoading, AI_LOADING_STEPS.length);

  function toggleTheme(theme) {
    setThemes((current) => {
      if (current.includes(theme)) {
        return current.filter((item) => item !== theme);
      }
      if (current.length >= MAX_THEMES) {
        return current;
      }
      return [...current, theme];
    });
  }

  function applySearchContext(searchPayload) {
    const context = buildSearchContextFromPayload(searchPayload);
    setOriginCity(context.originCity);
    setStartDate(context.startDate);
    setEndDate(context.endDate);
    setBudgetUsd(String(context.budgetUsd));
    setThemes(context.themes);
    setSearchContext(context);
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const payload = {
      origin_city: originCity.trim(),
      dates_mode: "strict",
      themes,
      budget_usd: Number(budgetUsd),
      travelers_count: 2,
      strict_dates: {
        start_date: startDate,
        end_date: endDate,
      },
    };

    setIsLoading(true);
    setErrorText("");
    setResultStatusText("");
    setResult(null);
    setActiveSavedSearchId(null);
    reactions.reset();
    applySearchContext(payload);

    try {
      const data = await fetchJson("/search", {
        method: "POST",
        token: auth.token,
        body: JSON.stringify(payload),
      });

      setResult(normalizeResultPayload(data));

      if (data?.saved_search_id) {
        setResultStatusText("Saved to your account.");
        setActiveSavedSearchId(data.saved_search_id);
        await savedSearches.load(auth.token);
      } else if (!auth.user) {
        setResultStatusText("Search complete. Sign in to save future results.");
      }
    } catch (error) {
      setResult(null);
      setErrorText(error.message || "Unexpected error");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleLoadSavedSearch(savedSearchId) {
    if (!auth.token) return;

    setErrorText("");
    setResultStatusText("");
    const data = await savedSearches.open(auth.token, savedSearchId);
    if (!data) return;

    applySearchContext(data.request_payload);
    setResult(normalizeResultPayload(data.response_payload, savedSearchId));
    setActiveSavedSearchId(savedSearchId);
    reactions.reset();
    setResultStatusText("Loaded from saved searches.");
  }

  function handleEditSearch() {
    searchShellRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }

  return (
    <main className="page">
      <section className="hero">
        <HeroCopy />

        <AccountPanel
          authMode={auth.mode}
          authEmail={auth.email}
          authPassword={auth.password}
          authUser={auth.user}
          authErrorText={auth.errorText}
          isAuthLoading={auth.isLoading}
          onAuthEmailChange={auth.setEmail}
          onAuthModeChange={auth.setMode}
          onAuthPasswordChange={auth.setPassword}
          onAuthSubmit={auth.submit}
          onLogout={auth.logout}
        />
      </section>

      <SearchForm
        shellRef={searchShellRef}
        originCity={originCity}
        budgetUsd={budgetUsd}
        startDate={startDate}
        endDate={endDate}
        themes={themes}
        authUser={auth.user}
        isLoading={isLoading}
        onOriginCityChange={setOriginCity}
        onBudgetChange={setBudgetUsd}
        onStartDateChange={setStartDate}
        onEndDateChange={setEndDate}
        onToggleTheme={toggleTheme}
        onSubmit={handleSubmit}
      />

      <StatusBanners
        errorText={errorText}
        resultStatusText={resultStatusText}
        isLoading={isLoading}
        loadingStepIndex={loadingStepIndex}
      />

      <section className="results-section">
        <div className="results-layout">
          <ResultsMain
            isLoading={isLoading}
            searchContext={searchContext}
            result={result}
            authUser={auth.user}
            getReactionProps={reactions.getReactionProps}
            onReact={(suggestionId, reaction) =>
              reactions.react(auth.token, suggestionId, reaction)
            }
          />

          <div className="results-sidebar">
            <SearchSummary
              onEditSearch={handleEditSearch}
              searchContext={searchContext}
            />
            <SavedSearchesPanel
              activeSavedSearchId={activeSavedSearchId}
              authUser={auth.user}
              isLoading={savedSearches.isLoading}
              items={savedSearches.items}
              errorText={savedSearches.errorText}
              onSelect={handleLoadSavedSearch}
            />
          </div>
        </div>
      </section>
    </main>
  );
}
