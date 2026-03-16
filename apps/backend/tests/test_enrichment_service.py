from app.application.services.enrichment_service import EnrichmentService, build_empty_enrichment


class _FakeProvider:
    def __init__(self, trip_plan: str) -> None:
        self.trip_plan = trip_plan
        self.calls: list[tuple[str, int, str]] = []

    def render_trip_summary(self, *, city: str, num_days: int, themes: str) -> str:
        self.calls.append((city, num_days, themes))
        return self.trip_plan


def test_enrichment_service_returns_trip_plan() -> None:
    provider = _FakeProvider("Day 1: waterfront. Day 2: old town.")
    enrichment = EnrichmentService.enrich(
        provider,
        city="Tivat",
        num_days=3,
        themes="beach, history",
    )

    assert enrichment.trip_plan == "Day 1: waterfront. Day 2: old town."
    assert provider.calls == [("Tivat", 3, "beach, history")]


def test_enrichment_service_returns_empty_payload_for_invalid_input() -> None:
    provider = _FakeProvider("unused")
    enrichment = EnrichmentService.enrich(
        provider,
        city="",
        num_days=0,
        themes="beach, history",
    )

    assert enrichment.trip_plan == ""
    assert provider.calls == []


def test_build_empty_enrichment_returns_blank_trip_plan() -> None:
    enrichment = build_empty_enrichment()

    assert enrichment.trip_plan == ""
