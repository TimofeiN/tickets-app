from __future__ import annotations

from contextlib import contextmanager

from sqlmodel import Session, SQLModel, create_engine

from app.infrastructure.db.models.iata_city_map import IataCityMap
from app.infrastructure.db.repositories.origin_airport_repository import OriginAirportRepository


def test_resolve_airports_returns_only_airport_rows(monkeypatch) -> None:
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
                country_code="GB",
                source="test",
            )
        )
        session.commit()

    @contextmanager
    def _fake_get_session():
        with Session(engine) as session:
            yield session

    monkeypatch.setattr(
        "app.infrastructure.db.repositories.origin_airport_repository.get_session",
        _fake_get_session,
    )

    repository = OriginAirportRepository()

    assert repository.resolve_airports("London") == ["LGW", "LHR"]
