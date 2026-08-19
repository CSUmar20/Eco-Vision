from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app import main
from app.models import DisposalRule, Jurisdiction, JurisdictionPostalCode


def build_jurisdiction(
    *,
    name: str = "Example City",
    display_name: str = "Example City, IL",
    postal_code: str = "60601",
) -> Jurisdiction:
    jurisdiction = Jurisdiction(
        id=uuid4(),
        slug=f"us-il-{name.lower().replace(' ', '-')}",
        name=name,
        display_name=display_name,
        jurisdiction_type="municipality",
        country_code="US",
        state_code="IL",
        county_name="Example County",
        waste_provider=None,
        parent_id=None,
        active=True,
    )
    jurisdiction.postal_codes = [
        JurisdictionPostalCode(
            jurisdiction_id=jurisdiction.id,
            postal_code=postal_code,
        )
    ]
    return jurisdiction


@pytest.fixture
def jurisdiction_client() -> Iterator[TestClient]:
    main.app.dependency_overrides[main.get_database_session] = object

    try:
        with TestClient(main.app) as client:
            yield client
    finally:
        main.app.dependency_overrides.clear()


def test_search_returns_every_matching_jurisdiction_for_a_zip(
    jurisdiction_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    city = build_jurisdiction()
    county = build_jurisdiction(
        name="Second City",
        display_name="Second City, IL",
    )
    captured_search: dict[str, str | int] = {}

    def search_stub(database: object, query: str, limit: int) -> list[Jurisdiction]:
        captured_search.update(query=query, limit=limit)
        return [city, county]

    monkeypatch.setattr(main, "search_jurisdictions", search_stub)

    response = jurisdiction_client.get(
        "/jurisdictions",
        params={"query": " 60601 ", "limit": 5},
    )

    assert response.status_code == 200
    assert captured_search == {"query": "60601", "limit": 5}
    assert [result["display_name"] for result in response.json()] == [
        "Example City, IL",
        "Second City, IL",
    ]
    assert all(result["postal_codes"] == ["60601"] for result in response.json())


def test_search_rejects_whitespace_only_query(
    jurisdiction_client: TestClient,
) -> None:
    response = jurisdiction_client.get(
        "/jurisdictions",
        params={"query": "  "},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "The jurisdiction search must contain at least two characters."
    )


def test_search_database_failure_returns_500(
    jurisdiction_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failing_search(database: object, query: str, limit: int) -> list[Jurisdiction]:
        raise SQLAlchemyError("database unavailable")

    monkeypatch.setattr(main, "search_jurisdictions", failing_search)

    response = jurisdiction_client.get(
        "/jurisdictions",
        params={"query": "60601"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Jurisdictions could not be searched."


def test_rules_include_source_and_verification_metadata(
    jurisdiction_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jurisdiction = build_jurisdiction()
    verified_at = datetime(2026, 8, 19, tzinfo=UTC)
    rule = DisposalRule(
        id=uuid4(),
        jurisdiction_id=jurisdiction.id,
        material_key="aluminum_can",
        status="accepted_curbside",
        instructions="Empty and rinse the container.",
        source_title="Official recycling guidance",
        source_url="https://example.gov/recycling",
        verified_at=verified_at,
    )
    monkeypatch.setattr(main, "get_jurisdiction", lambda database, identifier: jurisdiction)
    monkeypatch.setattr(main, "get_disposal_rules", lambda database, identifier: [rule])

    response = jurisdiction_client.get(f"/jurisdictions/{jurisdiction.id}/rules")

    assert response.status_code == 200
    assert response.json()["coverage_status"] == "available"
    assert response.json()["rules"] == [
        {
            "material_key": "aluminum_can",
            "status": "accepted_curbside",
            "instructions": "Empty and rinse the container.",
            "source_title": "Official recycling guidance",
            "source_url": "https://example.gov/recycling",
            "verified_at": "2026-08-19T00:00:00Z",
        }
    ]


def test_empty_rules_are_reported_as_unavailable(
    jurisdiction_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jurisdiction = build_jurisdiction()
    monkeypatch.setattr(main, "get_jurisdiction", lambda database, identifier: jurisdiction)
    monkeypatch.setattr(main, "get_disposal_rules", lambda database, identifier: [])

    response = jurisdiction_client.get(f"/jurisdictions/{jurisdiction.id}/rules")

    assert response.status_code == 200
    assert response.json()["coverage_status"] == "unavailable"
    assert response.json()["rules"] == []


def test_rules_return_404_for_unknown_jurisdiction(
    jurisdiction_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main, "get_jurisdiction", lambda database, identifier: None)

    response = jurisdiction_client.get(f"/jurisdictions/{uuid4()}/rules")

    assert response.status_code == 404
    assert response.json()["detail"] == "The recycling jurisdiction could not be found."
