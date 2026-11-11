import { useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  formatCurrency,
  formatMatchScore,
  getOptionBadges,
  getTripPlanPreview,
} from "../utils/format";

export function OptionCard({
  option,
  index,
  options,
  featured = false,
  canReact = false,
  reactionValue = "",
  reactionErrorText = "",
  isReactionLoading = false,
  onReact = null,
}) {
  const badges = getOptionBadges(option, index, options);
  const hasStyleDetails = option.trip_style || option.vibe;
  const tripPlan = option.trip_plan?.trim() || "";
  const canSendReaction =
    canReact && option.suggestion_id && typeof onReact === "function";
  const isTripPlanCollapsible =
    tripPlan.length > 320 || tripPlan.split("\n").filter(Boolean).length > 5;
  const [isTripPlanExpanded, setIsTripPlanExpanded] = useState(false);

  return (
    <article className={featured ? "option-row option-row-best" : "option-row"}>
      <div className="option-code">
        {option.destination_airport}
        <small>#{index + 1}</small>
      </div>

      <div className="option-body">
        <div>
          <div className="option-title">
            <h3>{option.destination_city}</h3>
            {badges.map((badge) => (
              <span className={`tag tag-${badge.tone}`} key={badge.label}>
                {badge.label}
              </span>
            ))}
          </div>
          <p className="route">
            {option.origin_airport} → {option.destination_airport}
          </p>
        </div>

        <p className="option-reason">{option.reason}</p>

        {hasStyleDetails || option.theme_explanation ? (
          <div className="facts">
            {option.trip_style ? (
              <div className="fact">
                <span>Trip style</span>
                {option.trip_style}
              </div>
            ) : null}
            {option.vibe ? (
              <div className="fact">
                <span>Mood</span>
                {option.vibe}
              </div>
            ) : null}
            {option.theme_explanation ? (
              <div className="fact fact-wide">
                <span>Theme fit</span>
                {option.theme_explanation}
              </div>
            ) : null}
          </div>
        ) : null}

        {option.highlights?.length ? (
          <div className="fact">
            <span>Highlights</span>
            <ul className="plain-list">
              {option.highlights.map((highlight) => (
                <li key={highlight}>{highlight}</li>
              ))}
            </ul>
          </div>
        ) : null}

        {tripPlan ? (
          <div className="fact">
            <span>Trip note</span>
            {isTripPlanCollapsible && !isTripPlanExpanded ? (
              <p className="itinerary-preview">
                {getTripPlanPreview(tripPlan)}
              </p>
            ) : (
              <div className="markdown-body">
                <ReactMarkdown>{tripPlan}</ReactMarkdown>
              </div>
            )}
            {isTripPlanCollapsible ? (
              <button
                className="inline-link-button"
                type="button"
                onClick={() => setIsTripPlanExpanded((value) => !value)}
              >
                {isTripPlanExpanded ? "Collapse itinerary" : "Expand itinerary"}
              </button>
            ) : null}
          </div>
        ) : null}

        {(option.tradeoff || option.caveat) && !featured ? (
          <div className="facts">
            {option.tradeoff ? (
              <div className="fact">
                <span>Tradeoff</span>
                {option.tradeoff}
              </div>
            ) : null}
            {option.caveat ? (
              <div className="fact">
                <span>Watch for</span>
                {option.caveat}
              </div>
            ) : null}
          </div>
        ) : null}
      </div>

      <div className="option-side">
        <div>
          <div className="price-block">
            <strong>{formatCurrency(option.price_usd)}</strong>
            <span>Total for 2 travelers</span>
          </div>
          <p className="score">
            <b>{formatMatchScore(option.score)}</b>
          </p>
        </div>

        <div>
          <div className="reaction-row">
            <button
              className={
                reactionValue === "like"
                  ? "reaction-button reaction-button-like-active"
                  : "reaction-button"
              }
              type="button"
              disabled={!canSendReaction || isReactionLoading}
              onClick={() => onReact(option.suggestion_id, "like")}
            >
              <span>Like</span>
              <strong>{option.likes ?? 0}</strong>
            </button>
            <button
              className={
                reactionValue === "dislike"
                  ? "reaction-button reaction-button-dislike-active"
                  : "reaction-button"
              }
              type="button"
              disabled={!canSendReaction || isReactionLoading}
              onClick={() => onReact(option.suggestion_id, "dislike")}
            >
              <span>Dislike</span>
              <strong>{option.dislikes ?? 0}</strong>
            </button>
          </div>
          {!canReact ? (
            <p className="inline-hint reaction-hint">
              Sign in to rate recommendations.
            </p>
          ) : null}
          {reactionErrorText ? (
            <p className="inline-hint inline-hint-error reaction-hint">
              {reactionErrorText}
            </p>
          ) : null}
        </div>
      </div>
    </article>
  );
}
