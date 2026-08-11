from io import BytesIO

from PIL import Image

from app.services import classifier


class DummyResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self._payload


def test_classify_image_accepts_url(monkeypatch) -> None:
    sample_image = Image.new("RGB", (2, 2), color="red")
    image_bytes = BytesIO()
    sample_image.save(image_bytes, format="PNG")

    monkeypatch.setattr(
        classifier,
        "get_classifier",
        lambda: lambda image, candidate_labels, hypothesis_template: [
            {"label": candidate_labels[0], "score": 0.99}
        ],
    )
    monkeypatch.setattr(
        classifier.urllib_request,
        "urlopen",
        lambda url: DummyResponse(image_bytes.getvalue()),
    )

    predictions = classifier.classify_image("https://example.com/image.png")

    assert predictions[0]["label"] == classifier.CANDIDATE_LABELS[0]
    assert predictions[0]["score"] == 0.99
