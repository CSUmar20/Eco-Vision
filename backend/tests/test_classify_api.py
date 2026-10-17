from collections.abc import Iterator
from datetime import UTC, datetime
from io import BytesIO
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from PIL import Image
from sqlalchemy.exc import SQLAlchemyError

from app import main
from app.models import DisposalRule, GeneralDisposalRule, Material, Scan

PREDICTIONS = [
    {"label": "a cardboard box", "score": 0.82},
    {"label": "a sheet of paper", "score": 0.12},
    {"label": "mixed-material packaging", "score": 0.06},
]

MATERIALS_BY_LABEL = {
    "a cardboard box": Material(
        id=uuid4(),
        key="corrugated_cardboard_box",
        display_name="Cardboard box",
        category="paper",
    ),
    "a sheet of paper": Material(
        id=uuid4(),
        key="paper_sheet",
        display_name="Paper",
        category="paper",
    ),
    "mixed-material packaging": Material(
        id=uuid4(),
        key="mixed_material_packaging",
        display_name="Mixed-material packaging",
        category="packaging",
    ),
}

GENERAL_GUIDANCE = GeneralDisposalRule(
    id=uuid4(),
    material_id=MATERIALS_BY_LABEL["a cardboard box"].id,
    country_code="US",
    action="recycle",
    headline="Recycle it",
    instructions="Place the clean cardboard box in recycling.",
    preparation="Remove packing material and food scraps, then flatten the box.",
    warning=None,
    source_title="US EPA: How Do I Recycle Common Recyclables",
    source_url="https://www.epa.gov/recycle/how-do-i-recycle-common-recyclables",
    verified_at=datetime(2026, 10, 16, tzinfo=UTC),
)


class ClassifierStub:
    def __init__(self) -> None:
        self.call_count = 0

    def __call__(self, image: Image.Image) -> list[dict[str, str | float]]:
        self.call_count += 1
        return PREDICTIONS


class FakeDatabaseSession:
    def __init__(self) -> None:
        self.added_scan: Scan | None = None
        self.commit_called = False
        self.refresh_called = False
        self.rollback_called = False
        self.fail_commit = False

    def add(self, scan: Scan) -> None:
        self.added_scan = scan

    def commit(self) -> None:
        self.commit_called = True

        if self.fail_commit:
            raise SQLAlchemyError("database unavailable")

    def refresh(self, scan: Scan) -> None:
        self.refresh_called = True
        scan.id = uuid4()
        scan.created_at = datetime(2026, 8, 11, tzinfo=UTC)

    def get(self, model: type[Scan], scan_id: UUID) -> Scan | None:
        if self.added_scan is not None and self.added_scan.id == scan_id:
            return self.added_scan

        return None

    def rollback(self) -> None:
        self.rollback_called = True


@pytest.fixture
def png_image_bytes() -> bytes:
    image = Image.new("RGB", (4, 4), color="green")
    image_bytes = BytesIO()
    image.save(image_bytes, format="PNG")
    return image_bytes.getvalue()


@pytest.fixture
def api_context(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[TestClient, FakeDatabaseSession, ClassifierStub]]:
    database = FakeDatabaseSession()
    classifier = ClassifierStub()

    main.app.dependency_overrides[main.get_database_session] = lambda: database
    monkeypatch.setattr(main, "classify_image", classifier)
    monkeypatch.setattr(
        main,
        "resolve_material_aliases",
        lambda session, labels: {
            label: MATERIALS_BY_LABEL[label]
            for label in labels
            if label in MATERIALS_BY_LABEL
        },
    )
    monkeypatch.setattr(
        main,
        "get_general_disposal_rule",
        lambda session, material_id, country_code: GENERAL_GUIDANCE,
    )
    monkeypatch.setattr(
        main,
        "get_disposal_rule",
        lambda session, jurisdiction_id, material_key: None,
    )

    try:
        with TestClient(main.app) as client:
            yield client, database, classifier
    finally:
        main.app.dependency_overrides.clear()


def upload(
    client: TestClient,
    content: bytes,
    content_type: str = "image/png",
) -> Response:
    return client.post(
        "/classify",
        files={"file": ("item.png", content, content_type)},
    )


def test_valid_image_returns_201(
    api_context: tuple[TestClient, FakeDatabaseSession, ClassifierStub],
    png_image_bytes: bytes,
) -> None:
    client, database, classifier = api_context

    response = upload(client, png_image_bytes)

    assert response.status_code == 201
    assert response.json()["top_prediction"] == {
        **PREDICTIONS[0],
        "material_key": "corrugated_cardboard_box",
        "material_display_name": "Cardboard box",
    }
    assert response.json()["alternatives"] == [
        {
            **PREDICTIONS[1],
            "material_key": "paper_sheet",
            "material_display_name": "Paper",
        },
        {
            **PREDICTIONS[2],
            "material_key": "mixed_material_packaging",
            "material_display_name": "Mixed-material packaging",
        },
    ]
    assert response.json()["disposal_guidance"] == {
        "scope": "general",
        "material_key": "corrugated_cardboard_box",
        "country_code": "US",
        "action": "recycle",
        "headline": "Recycle it",
        "instructions": "Place the clean cardboard box in recycling.",
        "preparation": "Remove packing material and food scraps, then flatten the box.",
        "warning": None,
        "source_title": "US EPA: How Do I Recycle Common Recyclables",
        "source_url": (
            "https://www.epa.gov/recycle/how-do-i-recycle-common-recyclables"
        ),
        "verified_at": "2026-10-16T00:00:00Z",
    }
    assert UUID(response.json()["scan_id"])
    assert classifier.call_count == 1
    assert database.commit_called


def test_invalid_media_type_returns_415(
    api_context: tuple[TestClient, FakeDatabaseSession, ClassifierStub],
) -> None:
    client, database, classifier = api_context

    response = upload(client, b"plain text", content_type="text/plain")

    assert response.status_code == 415
    assert classifier.call_count == 0
    assert database.added_scan is None


def test_oversized_upload_returns_413(
    api_context: tuple[TestClient, FakeDatabaseSession, ClassifierStub],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, database, classifier = api_context
    monkeypatch.setattr(main.settings, "max_image_bytes", 8)

    response = upload(client, b"123456789")

    assert response.status_code == 413
    assert classifier.call_count == 0
    assert database.added_scan is None


def test_empty_upload_returns_400(
    api_context: tuple[TestClient, FakeDatabaseSession, ClassifierStub],
) -> None:
    client, database, classifier = api_context

    response = upload(client, b"")

    assert response.status_code == 400
    assert response.json()["detail"] == "The uploaded image is empty."
    assert classifier.call_count == 0
    assert database.added_scan is None


def test_corrupt_image_returns_400(
    api_context: tuple[TestClient, FakeDatabaseSession, ClassifierStub],
) -> None:
    client, database, classifier = api_context

    response = upload(client, b"not a real PNG")

    assert response.status_code == 400
    assert response.json()["detail"] == "The uploaded file is not a valid image."
    assert classifier.call_count == 0
    assert database.added_scan is None


def test_prediction_is_saved(
    api_context: tuple[TestClient, FakeDatabaseSession, ClassifierStub],
    png_image_bytes: bytes,
) -> None:
    client, database, classifier = api_context

    response = upload(client, png_image_bytes)

    assert response.status_code == 201
    assert classifier.call_count == 1
    assert database.added_scan is not None
    assert database.added_scan.model_id == main.settings.hf_model
    assert database.added_scan.top_label == PREDICTIONS[0]["label"]
    assert database.added_scan.confidence == PREDICTIONS[0]["score"]
    assert database.added_scan.predictions == PREDICTIONS
    assert database.commit_called
    assert database.refresh_called
    assert not database.rollback_called


def test_selected_jurisdiction_is_saved_with_scan(
    api_context: tuple[TestClient, FakeDatabaseSession, ClassifierStub],
    png_image_bytes: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, database, classifier = api_context
    jurisdiction_id = uuid4()
    monkeypatch.setattr(
        main,
        "get_jurisdiction",
        lambda session, identifier: SimpleNamespace(country_code="US"),
    )

    response = client.post(
        "/classify",
        data={"jurisdiction_id": str(jurisdiction_id)},
        files={"file": ("item.png", png_image_bytes, "image/png")},
    )

    assert response.status_code == 201
    assert response.json()["jurisdiction_id"] == str(jurisdiction_id)
    assert database.added_scan is not None
    assert database.added_scan.jurisdiction_id == jurisdiction_id
    assert classifier.call_count == 1


def test_selected_jurisdiction_guidance_overrides_general_guidance(
    api_context: tuple[TestClient, FakeDatabaseSession, ClassifierStub],
    png_image_bytes: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, _ = api_context
    jurisdiction_id = uuid4()
    local_rule = DisposalRule(
        id=uuid4(),
        jurisdiction_id=jurisdiction_id,
        material_key="corrugated_cardboard_box",
        status="accepted_curbside",
        instructions="Flatten the box and place it in the blue cart.",
        source_title="Official municipal recycling guide",
        source_url="https://example.gov/recycling",
        verified_at=datetime(2026, 10, 17, tzinfo=UTC),
    )
    monkeypatch.setattr(
        main,
        "get_jurisdiction",
        lambda session, identifier: SimpleNamespace(country_code="US"),
    )
    monkeypatch.setattr(
        main,
        "get_disposal_rule",
        lambda session, identifier, material_key: local_rule,
    )

    response = client.post(
        "/classify",
        data={"jurisdiction_id": str(jurisdiction_id)},
        files={"file": ("item.png", png_image_bytes, "image/png")},
    )

    assert response.status_code == 201
    assert response.json()["disposal_guidance"] == {
        "scope": "jurisdiction",
        "material_key": "corrugated_cardboard_box",
        "jurisdiction_id": str(jurisdiction_id),
        "status": "accepted_curbside",
        "instructions": "Flatten the box and place it in the blue cart.",
        "source_title": "Official municipal recycling guide",
        "source_url": "https://example.gov/recycling",
        "verified_at": "2026-10-17T00:00:00Z",
    }


def test_missing_general_guidance_returns_null(
    api_context: tuple[TestClient, FakeDatabaseSession, ClassifierStub],
    png_image_bytes: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, _ = api_context
    monkeypatch.setattr(
        main,
        "get_general_disposal_rule",
        lambda session, material_id, country_code: None,
    )

    response = upload(client, png_image_bytes)

    assert response.status_code == 201
    assert response.json()["disposal_guidance"] is None


def test_unknown_jurisdiction_is_rejected_before_classification(
    api_context: tuple[TestClient, FakeDatabaseSession, ClassifierStub],
    png_image_bytes: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, database, classifier = api_context
    monkeypatch.setattr(main, "get_jurisdiction", lambda session, identifier: None)

    response = client.post(
        "/classify",
        data={"jurisdiction_id": str(uuid4())},
        files={"file": ("item.png", png_image_bytes, "image/png")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Select an active recycling jurisdiction."
    assert database.added_scan is None
    assert classifier.call_count == 0


def test_database_failure_rolls_back_and_returns_500(
    api_context: tuple[TestClient, FakeDatabaseSession, ClassifierStub],
    png_image_bytes: bytes,
) -> None:
    client, database, classifier = api_context
    database.fail_commit = True

    response = upload(client, png_image_bytes)

    assert response.status_code == 500
    assert response.json()["detail"] == "The scan result could not be saved."
    assert classifier.call_count == 1
    assert database.commit_called
    assert database.rollback_called
    assert not database.refresh_called


def test_material_mapping_failure_returns_500_before_scan_is_saved(
    api_context: tuple[TestClient, FakeDatabaseSession, ClassifierStub],
    png_image_bytes: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, database, classifier = api_context

    def fail_mapping(session, labels):
        raise SQLAlchemyError("database unavailable")

    monkeypatch.setattr(main, "resolve_material_aliases", fail_mapping)

    response = upload(client, png_image_bytes)

    assert response.status_code == 500
    assert (
        response.json()["detail"]
        == "Classifier labels could not be mapped to materials."
    )
    assert classifier.call_count == 1
    assert database.added_scan is None
    assert not database.commit_called


def test_guidance_database_failure_returns_500_before_scan_is_saved(
    api_context: tuple[TestClient, FakeDatabaseSession, ClassifierStub],
    png_image_bytes: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, database, classifier = api_context

    def fail_guidance(session, material_id, country_code):
        raise SQLAlchemyError("database unavailable")

    monkeypatch.setattr(main, "get_general_disposal_rule", fail_guidance)

    response = upload(client, png_image_bytes)

    assert response.status_code == 500
    assert response.json()["detail"] == "Disposal guidance could not be loaded."
    assert classifier.call_count == 1
    assert database.added_scan is None
    assert not database.commit_called


def test_scan_prediction_can_be_confirmed(
    api_context: tuple[TestClient, FakeDatabaseSession, ClassifierStub],
    png_image_bytes: bytes,
) -> None:
    client, database, _ = api_context
    scan_response = upload(client, png_image_bytes)
    confirmed_label = PREDICTIONS[1]["label"]

    response = client.patch(
        f"/scans/{scan_response.json()['scan_id']}/confirmation",
        json={"confirmed_label": confirmed_label},
    )

    assert response.status_code == 200
    assert response.json() == {
        "scan_id": scan_response.json()["scan_id"],
        "confirmed_label": confirmed_label,
    }
    assert database.added_scan is not None
    assert database.added_scan.confirmed_label == confirmed_label


def test_confirmation_rejects_label_outside_scan_predictions(
    api_context: tuple[TestClient, FakeDatabaseSession, ClassifierStub],
    png_image_bytes: bytes,
) -> None:
    client, database, _ = api_context
    scan_response = upload(client, png_image_bytes)

    response = client.patch(
        f"/scans/{scan_response.json()['scan_id']}/confirmation",
        json={"confirmed_label": "a label supplied by the client"},
    )

    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == "The confirmed label must be one of the scan predictions."
    )
    assert database.added_scan is not None
    assert database.added_scan.confirmed_label is None


def test_confirmation_returns_404_for_unknown_scan(
    api_context: tuple[TestClient, FakeDatabaseSession, ClassifierStub],
) -> None:
    client, _, _ = api_context

    response = client.patch(
        f"/scans/{uuid4()}/confirmation",
        json={"confirmed_label": PREDICTIONS[0]["label"]},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "The scan could not be found."
