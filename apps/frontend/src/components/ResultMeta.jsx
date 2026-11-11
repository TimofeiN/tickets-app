import {
  FRIENDLY_ENRICHMENT,
  FRIENDLY_FALLBACK_REASON,
  FRIENDLY_RANKING,
  FRIENDLY_SOURCE,
} from "../config/constants";

export function ResultMeta({ meta }) {
  if (!meta) return null;

  const pills = [
    FRIENDLY_SOURCE[meta.data_source],
    FRIENDLY_RANKING[meta.ranking_mode],
    FRIENDLY_ENRICHMENT[meta.enrichment_mode],
  ].filter(Boolean);

  const notices = (meta.fallback_reasons || [])
    .map((reason) => FRIENDLY_FALLBACK_REASON[reason])
    .filter(Boolean);

  return (
    <>
      {pills.length ? (
        <div className="meta-panel">
          {pills.map((pill) => (
            <span className="meta-pill" key={pill}>
              {pill}
            </span>
          ))}
        </div>
      ) : null}
      {notices.length ? (
        <div className="notice-stack">
          {notices.map((notice) => (
            <p className="notice" key={notice}>
              {notice}
            </p>
          ))}
        </div>
      ) : null}
    </>
  );
}
