from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Coroutine
from datetime import date
from typing import Any

import httpx

from app.application.ports.flight_search_provider import FlightSearchProvider, FlightSearchResult
from app.application.ports.origin_airport_resolver import OriginAirportResolver
from app.core.errors import DataAccessError, DomainInvariantError, ProviderUnavailableError
from app.core.settings import settings
from app.domain.models.flight_candidate import FlightCandidate
from app.domain.models.trip_preferences import TripPreferences
from app.shared.enums import DatesMode, SearchDataSource

logger = logging.getLogger(__name__)


class TravelpayoutsProvider(FlightSearchProvider):
    def __init__(
        self,
        api_token: str | None,
        marker: str | None,
        base_url: str,
        timeout_sec: float,
        origin_airport_resolver: OriginAirportResolver | None = None,
    ) -> None:
        self.api_token = api_token
        self.marker = marker
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = timeout_sec
        self.origin_airport_resolver = origin_airport_resolver

    @classmethod
    def from_settings(
        cls,
        *,
        origin_airport_resolver: OriginAirportResolver | None = None,
    ) -> "TravelpayoutsProvider":
        return cls(
            api_token=settings.travelpayouts_api_token,
            marker=settings.travelpayouts_marker,
            base_url=settings.travelpayouts_base_url,
            timeout_sec=settings.travelpayouts_timeout_sec,
            origin_airport_resolver=origin_airport_resolver,
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

        return self._run_async(self._fetch_live_candidates_async(origin_airports, preferences))

    async def _fetch_live_candidates_async(
        self,
        origin_airports: list[str],
        preferences: TripPreferences,
    ) -> list[FlightCandidate]:
        merged_candidates: list[FlightCandidate] = []
        last_error: str | None = None

        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout_sec,
            headers={"Accept": "application/json"},
        ) as client:
            tasks = [
                self._fetch_live_candidates_for_origin(client, origin_airport, preferences)
                for origin_airport in origin_airports
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for origin_airport, result in zip(origin_airports, results, strict=True):
            if isinstance(result, Exception):
                logger.warning(
                    "travelpayouts_origin_request_failed origin=%s reason=%s",
                    origin_airport,
                    str(result),
                )
                if isinstance(result, ProviderUnavailableError):
                    last_error = str(result)
                else:
                    last_error = "provider origin request failed"
                continue
            merged_candidates.extend(result)

        deduplicated = self._deduplicate_candidates(merged_candidates)
        if deduplicated:
            return deduplicated
        if last_error is not None:
            raise ProviderUnavailableError(last_error)
        raise ProviderUnavailableError("provider returned no usable flights")

    def _run_async(
        self,
        coroutine: Coroutine[Any, Any, list[FlightCandidate]],
    ) -> list[FlightCandidate]:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine)
        raise ProviderUnavailableError("cannot run async provider inside active event loop")

    # TODO: split method into smaller ones
    async def _fetch_live_candidates_for_origin(
        self,
        client: httpx.AsyncClient,
        origin_airport: str,
        preferences: TripPreferences,
    ) -> list[FlightCandidate]:
        query = {
            "origin": origin_airport,
            "depart_date": preferences.strict_start_date.isoformat(),
            "return_date": preferences.strict_end_date.isoformat(),
            "currency": "usd",
            "token": self.api_token,
        }
        if self.marker:
            query["marker"] = self.marker

        try:
            response = await client.get("/v1/prices/cheap", params=query)
            response.raise_for_status()
            logger.info(
                "travelpayouts_http_response status=%s url=%s origin=%s",
                response.status_code,
                "/v1/prices/cheap",
                origin_airport,
            )
        except httpx.HTTPStatusError as exc:
            raise ProviderUnavailableError(
                f"provider http error status={exc.response.status_code}"
            ) from exc
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            raise ProviderUnavailableError(str(exc)) from exc

        try:
            parsed = response.json()
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
                    option_id=f"tp_{origin_airport.lower()}_{destination_airport.lower()}_{idx:03d}",
                    destination_city=str(destination_city),
                    origin_airport=origin_airport,
                    destination_airport=destination_airport,
                    price_usd=int(price),
                    departure_date=departure_date,
                    return_date=return_date,
                    themes=frozenset(),
                )
            )
        return candidates

    def _deduplicate_candidates(self, candidates: list[FlightCandidate]) -> list[FlightCandidate]:
        seen: set[tuple[str, date, date, int]] = set()
        unique: list[FlightCandidate] = []
        for candidate in candidates:
            key = (
                candidate.destination_airport.upper(),
                candidate.departure_date,
                candidate.return_date,
                candidate.price_usd,
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(candidate)
        return unique

    def _normalize_offer_item(self, item: dict[str, object]) -> dict[str, object] | None:
        if "price" in item:
            return item

        nested_offers = [value for value in item.values() if isinstance(value, dict)]
        for nested in nested_offers:
            if "price" in nested:
                return nested
        return None

    # TODO: Remove this logic to a separate file for fallbacks
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
        if self.origin_airport_resolver is None:
            return []

        try:
            resolved = self.origin_airport_resolver.resolve_airports(origin_city)
        except DataAccessError as exc:
            logger.warning("origin_airport_resolver_failed reason=%s", str(exc))
            return []

        normalized = [code.strip().upper() for code in resolved if code and code.strip()]
        seen: set[str] = set()
        unique: list[str] = []
        for code in normalized:
            if code in seen:
                continue
            seen.add(code)
            unique.append(code)
        return unique
