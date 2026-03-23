from __future__ import annotations

from sqlmodel import Session, SQLModel, create_engine

from app.infrastructure.db.models.iata_city_map import IataCityMap
from app.infrastructure.db.repositories.origin_airport_repository import OriginAirportRepository


def test_resolve_airports_returns_only_airport_rows() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            IataCityMap(
                iata_code="LON",
                city_code="LON",
                city_name="London",
                airport_name=None,
                country_code="GB",
                source="test",
            )
        )
        session.add(
            IataCityMap(
                iata_code="LGW",
                city_code="LON",
                city_name="London",
                airport_name="Gatwick Airport",
                is_flightable=True,
                country_code="GB",
                source="test",
            )
        )
        session.add(
            IataCityMap(
                iata_code="LHR",
                city_code="LON",
                city_name="London",
                airport_name="Heathrow Airport",
                is_flightable=True,
                country_code="GB",
                source="test",
            )
        )
        session.commit()

    with Session(engine) as session:
        repository = OriginAirportRepository(session=session)
        assert repository.resolve_airports("London") == ["LGW", "LHR"]


def test_resolve_airports_skips_non_flightable_airports() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            IataCityMap(
                iata_code="BEG",
                city_code="BEG",
                city_name="Belgrade",
                airport_name="Belgrad Nikola Tesla Airport",
                is_flightable=True,
                country_code="RS",
                source="test",
            )
        )
        session.add(
            IataCityMap(
                iata_code="BJY",
                city_code="BEG",
                city_name="Belgrade",
                airport_name="Batajnica",
                is_flightable=False,
                country_code="RS",
                source="test",
            )
        )
        session.add(
            IataCityMap(
                iata_code="BZN",
                city_code="BZN",
                city_name="Belgrade",
                airport_name="Bozeman Yellowstone International Airport",
                is_flightable=True,
                country_code="US",
                source="test",
            )
        )
        session.commit()

    with Session(engine) as session:
        repository = OriginAirportRepository(session=session)
        assert repository.resolve_airports("Belgrade") == ["BEG"]
