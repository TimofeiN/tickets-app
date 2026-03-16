from __future__ import annotations

import json
from urllib.request import urlopen

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import ProgrammingError

from app.core.settings import settings
from app.infrastructure.db.models.iata_city_map import IataCityMap
from app.infrastructure.db.session import get_session


def fetch_json(url: str) -> list[dict[str, object]]:
    with urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def build_city_lookup(cities: list[dict[str, object]]) -> dict[str, str]:
    city_lookup: dict[str, str] = {}
    for city in cities:
        code = str(city.get("code", "")).strip().upper()
        name = str(city.get("name", "")).strip()
        if not code or not name:
            continue
        city_lookup[code] = name
    return city_lookup


def build_records(
    airports: list[dict[str, object]],
    city_lookup: dict[str, str],
) -> list[tuple[str, str, str, str, str, str]]:
    records: dict[str, tuple[str, str, str, str, str, str]] = {}

    for airport in airports:
        iata_code = str(airport.get("code", "")).strip().upper()
        city_code = str(airport.get("city_code", "")).strip().upper()
        country_code = str(airport.get("country_code", "")).strip().upper()
        airport_name = str(airport.get("name", "")).strip()
        if not iata_code or len(iata_code) != 3:
            continue

        city_name = city_lookup.get(city_code) or airport_name
        if not city_name:
            continue

        records[iata_code] = (
            iata_code,
            city_code,
            city_name,
            airport_name,
            country_code,
            "travelpayouts_data_api",
        )

    return list(records.values())


def upsert_records(records: list[tuple[str, str, str, str, str, str]]) -> None:
    try:
        payload = [
            {
                "iata_code": iata_code,
                "city_code": city_code,
                "city_name": city_name,
                "airport_name": airport_name,
                "country_code": country_code,
                "source": source,
            }
            for iata_code, city_code, city_name, airport_name, country_code, source in records
        ]
        statement = insert(IataCityMap).values(payload)
        statement = statement.on_conflict_do_update(
            index_elements=[IataCityMap.iata_code],
            set_={
                "city_code": statement.excluded.city_code,
                "city_name": statement.excluded.city_name,
                "airport_name": statement.excluded.airport_name,
                "country_code": statement.excluded.country_code,
                "source": statement.excluded.source,
            },
        )
        with get_session() as session:
            session.execute(statement)
            session.commit()
    except ProgrammingError as exc:
        if "iata_city_map" in str(exc).lower():
            raise RuntimeError(
                "Table iata_city_map does not exist. Run `make backend-db-upgrade` first."
            ) from exc
        raise


def main() -> None:
    base_url = settings.travelpayouts_data_base_url
    lang = settings.travelpayouts_data_lang

    airports_url = f"{base_url.rstrip('/')}/{lang}/airports.json"
    cities_url = f"{base_url.rstrip('/')}/{lang}/cities.json"

    print(f"Fetching airports dataset: {airports_url}")
    airports = fetch_json(airports_url)
    print(f"Fetched airports: {len(airports)}")

    print(f"Fetching cities dataset: {cities_url}")
    cities = fetch_json(cities_url)
    print(f"Fetched cities: {len(cities)}")

    city_lookup = build_city_lookup(cities)
    records = build_records(airports, city_lookup)
    print(f"Prepared iata records: {len(records)}")

    upsert_records(records)
    print("Sync completed: iata_city_map updated")


if __name__ == "__main__":
    main()
