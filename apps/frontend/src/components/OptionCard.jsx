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
  const cardClassName = featured ? "card card-featured" : "card";
  const hasStyleDetails = option.trip_style || option.vibe;
  const tripPlan = option.trip_plan?.trim() || "";
  const canSendReaction =
    canReact && option.suggestion_id && typeof onReact === "function";
  const isTripPlanCollapsible =
    tripPlan.length > 320 || tripPlan.split("\n").filter(Boolean).length > 5;
  const [isTripPlanExpanded, setIsTripPlanExpanded] = useState(false);

  return (
    <article className={cardClassName}>
      <div className="card-topline">
        <div className="badge-row">
          {badges.map((badge) => (
            <span
              className={`result-badge result-badge-${badge.tone}`}
              key={badge.label}
            >
              {badge.label}
            </span>
          ))}
        </div>
        <span className="score-pill">{formatMatchScore(option.score)}</span>
      </div>

      <div className="card-header">
        <div>
          <h3>{option.destination_city}</h3>
          <p className="route">
            {option.origin_airport} to {option.destination_airport}
          </p>
        </div>
        <div className="price-block">
          <strong>{formatCurrency(option.price_usd)}</strong>
          <span>Total for 2 travelers</span>
        </div>
      </div>

      <section className="card-section">
        <p className="section-kicker">Why this works</p>
        <p className="lead">{option.reason}</p>
      </section>

      <section className="card-section reaction-section">
        <p className="section-kicker">Was this useful?</p>
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
          <p className="inline-hint">Sign in to rate recommendations.</p>
        ) : null}
        {reactionErrorText ? (
          <p className="inline-hint inline-hint-error">{reactionErrorText}</p>
        ) : null}
      </section>

      {hasStyleDetails ? (
        <div className="detail-grid">
          {option.trip_style ? (
            <section className="detail-card">
              <span>Trip style</span>
              <strong>{option.trip_style}</strong>
            </section>
          ) : null}
          {option.vibe ? (
            <section className="detail-card">
              <span>Mood</span>
              <strong>{option.vibe}</strong>
            </section>
          ) : null}
        </div>
      ) : null}

      {option.theme_explanation ? (
        <section className="card-section">
          <p className="section-kicker">Theme fit</p>
          <p>{option.theme_explanation}</p>
        </section>
      ) : null}

      {option.highlights?.length ? (
        <section className="card-section">
          <p className="section-kicker">Highlights</p>
          <ul className="plain-list">
            {option.highlights.map((highlight) => (
              <li key={highlight}>{highlight}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {tripPlan ? (
        <section className="card-section trip-plan-section">
          <p className="section-kicker">Trip note</p>
          {isTripPlanCollapsible && !isTripPlanExpanded ? (
            <p className="itinerary-preview">{getTripPlanPreview(tripPlan)}</p>
          ) : (
            <div className="markdown-body">
              <ReactMarkdown>{tripPlan}</ReactMarkdown>
            </div>
          )}
          {isTripPlanCollapsible ? (
            <button
              className="inline-link-button itinerary-toggle"
              type="button"
              onClick={() => setIsTripPlanExpanded((value) => !value)}
            >
              {isTripPlanExpanded ? "Collapse itinerary" : "Expand itinerary"}
            </button>
          ) : null}
        </section>
      ) : null}

      {(option.tradeoff || option.caveat) && !featured ? (
        <div className="detail-grid">
          {option.tradeoff ? (
            <section className="detail-card">
              <span>Tradeoff</span>
              <strong>{option.tradeoff}</strong>
            </section>
          ) : null}
          {option.caveat ? (
            <section className="detail-card">
              <span>Watch for</span>
              <strong>{option.caveat}</strong>
            </section>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}
