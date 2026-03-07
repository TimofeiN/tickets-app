from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.schemas import SearchRequest

CITY_AIRPORTS = {
    "belgrade": ["BEG"],
    "new york": ["JFK", "EWR"],
    "london": ["LHR", "LGW"],
    "paris": ["CDG", "ORY"],
}

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FlightCandidate:
    option_id: str
    destination_city: str
    origin_airport: str
    destination_airport: str
    price_usd: int
    departure_date: date
    return_date: date
    themes: frozenset[str]


class ProviderUnavailableError(Exception):
    pass


class TravelpayoutsClient:
    def __init__(
        self,
        api_token: str | None,
        marker: str | None,
        base_url: str,
        timeout_sec: float,
    ) -> None:
        self.api_token = api_token
        self.marker = marker
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = timeout_sec

    @classmethod
    def from_env(cls) -> "TravelpayoutsClient":
        timeout_raw = os.getenv("TRAVELPAYOUTS_TIMEOUT_SEC", "3")
        try:
            timeout_sec = float(timeout_raw)
        except ValueError:
            timeout_sec = 3.0

        return cls(
            api_token=os.getenv("TRAVELPAYOUTS_API_TOKEN") or None,
            marker=os.getenv("TRAVELPAYOUTS_MARKER") or None,
            base_url=os.getenv("TRAVELPAYOUTS_BASE_URL", "https://api.travelpayouts.com"),
            timeout_sec=max(timeout_sec, 1.0),
        )

    def get_candidates(self, payload: SearchRequest) -> list[FlightCandidate]:
        try:
            logger.info(
                "travelpayouts_request_started origin_city=%s dates_mode=%s",
                payload.origin_city,
                payload.dates_mode.value,
            )
            live_candidates = self._fetch_live_candidates(payload)
            if live_candidates:
                logger.info(
                    "travelpayouts_request_succeeded source=live candidates=%s",
                    len(live_candidates),
                )
                return live_candidates
        except ProviderUnavailableError as exc:
            # Fallback keeps /search usable when external provider is unavailable.
            logger.warning("travelpayouts_fallback_activated reason=%s", str(exc))

        fallback = self._fallback_candidates(payload)
        logger.info(
            "travelpayouts_request_succeeded source=fallback candidates=%s",
            len(fallback),
        )
        return fallback

    def _fetch_live_candidates(self, payload: SearchRequest) -> list[FlightCandidate]:
        if not self.api_token:
            raise ProviderUnavailableError("TRAVELPAYOUTS_API_TOKEN is missing")

        origin_airports = self._resolve_airports(payload.origin_city)
        if not origin_airports:
            raise ProviderUnavailableError("origin city is not mapped to known airports")

        if payload.strict_dates is None:
            # For MVP without LLM and without month-batching, flexible searches use fallback data.
            raise ProviderUnavailableError("flexible dates live search is not implemented")

        first_origin = origin_airports[0]
        query = {
            "origin": first_origin,
            "depart_date": payload.strict_dates.start_date.isoformat(),
            "return_date": payload.strict_dates.end_date.isoformat(),
            "currency": "usd",
            "token": self.api_token,
        }
        if self.marker:
            query["marker"] = self.marker

        url = f"{self.base_url}/v1/prices/cheap?{urlencode(query)}"
        request = Request(url, headers={"Accept": "application/json"})

        try:
            with urlopen(request, timeout=self.timeout_sec) as response:
                logger.info(
                    "travelpayouts_http_response status=%s url=%s",
                    getattr(response, "status", "unknown"),
                    f"{self.base_url}/v1/prices/cheap",
                )
                raw_body = response.read().decode("utf-8")
        except HTTPError as exc:
            raise ProviderUnavailableError(f"provider http error status={exc.code}") from exc
        except (URLError, TimeoutError) as exc:
            raise ProviderUnavailableError(str(exc)) from exc

        try:
            parsed = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise ProviderUnavailableError("provider returned malformed json") from exc

        data = parsed.get("data")
        if not isinstance(data, dict):
            raise ProviderUnavailableError("provider response has unexpected shape")

        candidates: list[FlightCandidate] = []
        for idx, (destination_airport, item) in enumerate(data.items(), start=1):
            if not isinstance(item, dict):
                continue
            normalized_item = self._normalize_offer_item(item)
            if normalized_item is None:
                continue

            price = normalized_item.get("price")
            depart_date_raw = normalized_item.get("departure_at", "")
            return_date_raw = normalized_item.get("return_at", "")
            destination_city = normalized_item.get("destination") or destination_airport
            if not isinstance(price, (int, float)):
                continue

            try:
                departure_date = date.fromisoformat(str(depart_date_raw)[:10])
                return_date = date.fromisoformat(str(return_date_raw)[:10])
            except ValueError:
                continue

            candidates.append(
                FlightCandidate(
                    option_id=f"tp_{destination_airport.lower()}_{idx:03d}",
                    destination_city=str(destination_city),
                    origin_airport=first_origin,
                    destination_airport=destination_airport,
                    price_usd=int(price),
                    departure_date=departure_date,
                    return_date=return_date,
                    themes=frozenset({"beach", "history", "nightlife", "gastronomy"}),
                )
            )

        if not candidates:
            raise ProviderUnavailableError("provider returned no usable flights")

        return candidates

    def _normalize_offer_item(self, item: dict[str, object]) -> dict[str, object] | None:
        if "price" in item:
            return item

        # `/v1/prices/cheap` can return nested offers keyed by transfers count ("0", "1", ...).
        nested_offers = [value for value in item.values() if isinstance(value, dict)]
        for nested in nested_offers:
            if "price" in nested:
                return nested
        return None

    def _fallback_candidates(self, payload: SearchRequest) -> list[FlightCandidate]:
        origin_airport = (self._resolve_airports(payload.origin_city) or ["BEG"])[0]

        return [
            FlightCandidate(
                option_id="opt_bcn_001",
                destination_city="Barcelona",
                origin_airport=origin_airport,
                destination_airport="BCN",
                price_usd=640,
                departure_date=date(2026, 6, 10),
                return_date=date(2026, 6, 17),
                themes=frozenset({"beach", "history", "nightlife"}),
            ),
            FlightCandidate(
                option_id="opt_ath_002",
                destination_city="Athens",
                origin_airport=origin_airport,
                destination_airport="ATH",
                price_usd=590,
                departure_date=date(2026, 6, 10),
                return_date=date(2026, 6, 17),
                themes=frozenset({"history", "beach", "gastronomy"}),
            ),
            FlightCandidate(
                option_id="opt_lis_003",
                destination_city="Lisbon",
                origin_airport=origin_airport,
                destination_airport="LIS",
                price_usd=710,
                departure_date=date(2026, 6, 10),
                return_date=date(2026, 6, 17),
                themes=frozenset({"nightlife", "history", "beach"}),
            ),
            FlightCandidate(
                option_id="opt_nap_004",
                destination_city="Naples",
                origin_airport=origin_airport,
                destination_airport="NAP",
                price_usd=520,
                departure_date=date(2026, 7, 5),
                return_date=date(2026, 7, 12),
                themes=frozenset({"history", "gastronomy", "beach"}),
            ),
            FlightCandidate(
                option_id="opt_tiv_005",
                destination_city="Tivat",
                origin_airport=origin_airport,
                destination_airport="TIV",
                price_usd=300,
                departure_date=date(2026, 7, 8),
                return_date=date(2026, 7, 15),
                themes=frozenset({"beach", "family"}),
            ),
            FlightCandidate(
                option_id="opt_ist_006",
                destination_city="Istanbul",
                origin_airport=origin_airport,
                destination_airport="IST",
                price_usd=430,
                departure_date=date(2026, 6, 20),
                return_date=date(2026, 6, 27),
                themes=frozenset({"history", "nightlife", "gastronomy"}),
            ),
        ]

    def _resolve_airports(self, origin_city: str) -> list[str]:
        return CITY_AIRPORTS.get(origin_city.strip().lower(), [])
