from collections.abc import Iterator
from datetime import UTC, datetime
from io import BytesIO
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from PIL import Image
from sqlalchemy.exc import SQLAlchemyError

from app import main
from app.models import Scan

PREDICTIONS = [
    {"label": "a cardboard box", "score": 0.82},
    {"label": "a sheet of paper", "score": 0.12},
    {"label": "mixed-material packaging", "score": 0.06},
]


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
    assert response.json()["top_prediction"] == PREDICTIONS[0]
    assert response.json()["alternatives"] == PREDICTIONS[1:]
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
    monkeypatch.setattr(main, "get_jurisdiction", lambda session, identifier: object())

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
