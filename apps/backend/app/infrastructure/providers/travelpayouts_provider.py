from __future__ import annotations

import asyncio
import json
import logging
from datetime import date

import httpx

from app.application.ports.flight_search_provider import (
    FlightOffer,
    FlightProviderResult,
    FlightSearchProvider,
)
from app.core.errors import DomainInvariantError, ProviderUnavailableError
from app.core.settings import settings
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
    ) -> None:
        self.api_token = api_token
        self.marker = marker
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = timeout_sec

    @classmethod
    def from_settings(cls) -> TravelpayoutsProvider:
        return cls(
            api_token=settings.travelpayouts_api_token,
            marker=settings.travelpayouts_marker,
            base_url=settings.travelpayouts_base_url,
            timeout_sec=settings.travelpayouts_timeout_sec,
        )

    def get_offers(
        self,
        preferences: TripPreferences,
        *,
        origin_airports: list[str],
    ) -> FlightProviderResult:
        logger.info(
            "travelpayouts_request_started origin_city=%s dates_mode=%s",
            preferences.origin_city,
            preferences.dates_mode.value,
        )
        offers = self._fetch_live_offers(preferences, origin_airports=origin_airports)
        if not offers:
            raise ProviderUnavailableError("provider returned empty response")

        logger.info(
            "travelpayouts_request_succeeded source=live offers=%s",
            len(offers),
        )
        return FlightProviderResult(offers=offers, source=SearchDataSource.live)

    def _fetch_live_offers(
        self,
        preferences: TripPreferences,
        *,
        origin_airports: list[str],
    ) -> list[FlightOffer]:
        if not self.api_token:
            raise ProviderUnavailableError("TRAVELPAYOUTS_API_TOKEN is missing")

        if not origin_airports:
            raise ProviderUnavailableError("origin city is not mapped to known airports")

        if preferences.dates_mode != DatesMode.strict:
            raise ProviderUnavailableError("flexible dates live search is not implemented")

        if preferences.strict_start_date is None or preferences.strict_end_date is None:
            raise DomainInvariantError("strict dates are required for strict mode")

        return self._run_fetch_live_offers(origin_airports, preferences)

    def _run_fetch_live_offers(
        self,
        origin_airports: list[str],
        preferences: TripPreferences,
    ) -> list[FlightOffer]:
        with asyncio.Runner() as runner:
            return runner.run(self._fetch_live_offers_async(origin_airports, preferences))

    async def _fetch_live_offers_async(
        self,
        origin_airports: list[str],
        preferences: TripPreferences,
    ) -> list[FlightOffer]:
        merged_offers: list[FlightOffer] = []
        last_error: str | None = None

        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout_sec,
            headers={"Accept": "application/json"},
        ) as client:
            tasks = [
                self._fetch_live_offers_for_origin(client, origin_airport, preferences)
                for origin_airport in origin_airports
            ]
            results: list[list[FlightOffer] | BaseException] = await asyncio.gather(
                *tasks,
                return_exceptions=True,
            )

        for origin_airport, result in zip(origin_airports, results, strict=True):
            if isinstance(result, BaseException):
                details = self._error_details(result)
                logger.warning(
                    "travelpayouts_origin_request_failed origin=%s error=%s",
                    origin_airport,
                    details,
                )
                if isinstance(result, ProviderUnavailableError):
                    last_error = details
                else:
                    last_error = f"provider origin request failed: {details}"
                continue
            merged_offers.extend(result)

        if merged_offers:
            return merged_offers
        if last_error is not None:
            raise ProviderUnavailableError(last_error)
        raise ProviderUnavailableError("provider returned no usable flights")

    async def _fetch_live_offers_for_origin(
        self,
        client: httpx.AsyncClient,
        origin_airport: str,
        preferences: TripPreferences,
    ) -> list[FlightOffer]:
        query = self._build_prices_query(origin_airport, preferences)
        response = await self._request_prices(client, origin_airport, query)
        data = self._parse_prices_data(response)
        return self._build_offers_from_data(origin_airport, data)

    def _build_prices_query(
        self,
        origin_airport: str,
        preferences: TripPreferences,
    ) -> dict[str, str]:
        if preferences.strict_start_date is None or preferences.strict_end_date is None:
            raise DomainInvariantError("strict dates are required for strict mode")
        if not self.api_token:
            raise ProviderUnavailableError("TRAVELPAYOUTS_API_TOKEN is missing")

        query = {
            "origin": origin_airport,
            "depart_date": preferences.strict_start_date.isoformat(),
            "return_date": preferences.strict_end_date.isoformat(),
            "currency": "usd",
            "token": self.api_token,
        }
        if self.marker:
            query["marker"] = self.marker
        return query

    async def _request_prices(
        self,
        client: httpx.AsyncClient,
        origin_airport: str,
        query: dict[str, str],
    ) -> httpx.Response:
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
            response_text = exc.response.text[:300].replace("\n", " ").strip()
            request_url = str(exc.request.url)
            raise ProviderUnavailableError(
                "provider http error "
                f"origin={origin_airport} status={exc.response.status_code} "
                f"url={request_url} body={response_text or '<empty>'}"
            ) from exc
        except httpx.TimeoutException as exc:
            request_url = str(exc.request.url) if exc.request is not None else "<unknown>"
            raise ProviderUnavailableError(
                "provider timeout "
                f"origin={origin_airport} url={request_url} "
                f"detail={str(exc) or exc.__class__.__name__}"
            ) from exc
        except httpx.RequestError as exc:
            request_url = str(exc.request.url) if exc.request is not None else "<unknown>"
            raise ProviderUnavailableError(
                "provider request error "
                f"origin={origin_airport} url={request_url} "
                f"detail={str(exc) or exc.__class__.__name__}"
            ) from exc
        return response

    @staticmethod
    def _parse_prices_data(response: httpx.Response) -> dict[str, object]:
        try:
            parsed = response.json()
        except json.JSONDecodeError as exc:
            raise ProviderUnavailableError("provider returned malformed json") from exc

        data = parsed.get("data")
        if not isinstance(data, dict):
            raise ProviderUnavailableError("provider response has unexpected shape")
        return data

    def _build_offers_from_data(
        self,
        origin_airport: str,
        data: dict[str, object],
    ) -> list[FlightOffer]:
        offers: list[FlightOffer] = []
        for destination_airport, item in data.items():
            if not isinstance(item, dict):
                continue
            normalized_item = self._normalize_offer_item(item)
            if normalized_item is None:
                continue

            offer = self._build_offer(
                origin_airport=origin_airport,
                destination_airport=destination_airport,
                item=normalized_item,
            )
            if offer is None:
                continue
            offers.append(offer)
        return offers

    @staticmethod
    def _build_offer(
        *,
        origin_airport: str,
        destination_airport: str,
        item: dict[str, object],
    ) -> FlightOffer | None:
        price = item.get("price")
        if not isinstance(price, (int, float)):
            return None

        depart_date_raw = item.get("departure_at", "")
        return_date_raw = item.get("return_at", "")
        try:
            departure_date = date.fromisoformat(str(depart_date_raw)[:10])
            return_date = date.fromisoformat(str(return_date_raw)[:10])
        except ValueError:
            return None

        destination_city_raw = item.get("destination") or destination_airport
        return FlightOffer(
            origin_airport=origin_airport,
            destination_airport=destination_airport,
            destination_city=str(destination_city_raw),
            price_usd=int(price),
            departure_date=departure_date,
            return_date=return_date,
            stops_count=TravelpayoutsProvider._extract_stops_count(item),
            travel_time_minutes=TravelpayoutsProvider._extract_travel_time_minutes(item),
        )

    @staticmethod
    def _normalize_offer_item(item: dict[str, object]) -> dict[str, object] | None:
        if "price" in item:
            return item

        nested_offers = [value for value in item.values() if isinstance(value, dict)]
        for nested in nested_offers:
            if "price" in nested:
                return nested
        return None

    @staticmethod
    def _extract_stops_count(item: dict[str, object]) -> int | None:
        raw_value = item.get("transfers", item.get("number_of_changes"))
        if isinstance(raw_value, int) and raw_value >= 0:
            return raw_value
        return None

    @staticmethod
    def _extract_travel_time_minutes(item: dict[str, object]) -> int | None:
        duration = item.get("duration")
        if isinstance(duration, int) and duration > 0:
            return duration

        duration_to = item.get("duration_to")
        duration_back = item.get("duration_back")
        if isinstance(duration_to, int) and isinstance(duration_back, int):
            total = duration_to + duration_back
            if total > 0:
                return total
        return None

    @staticmethod
    def _error_details(exc: BaseException) -> str:
        message = str(exc).strip()
        if message:
            return f"{exc.__class__.__name__}: {message}"
        return f"{exc.__class__.__name__}"
