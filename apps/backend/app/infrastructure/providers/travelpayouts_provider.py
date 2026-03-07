from __future__ import annotations

import json
import logging
import os
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.application.ports.flight_search_provider import FlightSearchProvider, FlightSearchResult
from app.core.errors import DomainInvariantError, ProviderUnavailableError
from app.core.types import DatesMode, SearchDataSource
from app.domain.models.flight_candidate import FlightCandidate
from app.domain.models.trip_preferences import TripPreferences

CITY_AIRPORTS = {
    "belgrade": ["BEG"],
    "new york": ["JFK", "EWR"],
    "london": ["LHR", "LGW"],
    "paris": ["CDG", "ORY"],
}

logger = logging.getLogger(__name__)


class TravelpayoutsProvider(FlightSearchProvider):
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
    def from_env(cls) -> "TravelpayoutsProvider":
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

    def get_candidates(self, preferences: TripPreferences) -> FlightSearchResult:
        try:
            logger.info(
                "travelpayouts_request_started origin_city=%s dates_mode=%s",
                preferences.origin_city,
                preferences.dates_mode.value,
            )
            live_candidates = self._fetch_live_candidates(preferences)
            if live_candidates:
                logger.info(
                    "travelpayouts_request_succeeded source=live candidates=%s",
                    len(live_candidates),
                )
                return FlightSearchResult(candidates=live_candidates, source=SearchDataSource.live)
        except ProviderUnavailableError as exc:
            logger.warning("travelpayouts_fallback_activated reason=%s", str(exc))
            fallback_reason = str(exc)
        else:
            fallback_reason = "provider returned empty response"

        fallback = self._fallback_candidates(preferences)
        logger.info(
            "travelpayouts_request_succeeded source=fallback candidates=%s",
            len(fallback),
        )
        return FlightSearchResult(
            candidates=fallback,
            source=SearchDataSource.fallback,
            fallback_reason=fallback_reason,
        )

    def _fetch_live_candidates(self, preferences: TripPreferences) -> list[FlightCandidate]:
        if not self.api_token:
            raise ProviderUnavailableError("TRAVELPAYOUTS_API_TOKEN is missing")

        origin_airports = self._resolve_airports(preferences.origin_city)
        if not origin_airports:
            raise ProviderUnavailableError("origin city is not mapped to known airports")

        if preferences.dates_mode != DatesMode.strict:
            raise ProviderUnavailableError("flexible dates live search is not implemented")

        if preferences.strict_start_date is None or preferences.strict_end_date is None:
            raise DomainInvariantError("strict dates are required for strict mode")

        first_origin = origin_airports[0]
        query = {
            "origin": first_origin,
            "depart_date": preferences.strict_start_date.isoformat(),
            "return_date": preferences.strict_end_date.isoformat(),
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

        nested_offers = [value for value in item.values() if isinstance(value, dict)]
        for nested in nested_offers:
            if "price" in nested:
                return nested
        return None

    def _fallback_candidates(self, preferences: TripPreferences) -> list[FlightCandidate]:
        origin_airport = (self._resolve_airports(preferences.origin_city) or ["BEG"])[0]

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
