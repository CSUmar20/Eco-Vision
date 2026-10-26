from typing import Any

from app import serve


def test_production_server_uses_runtime_configuration(
    monkeypatch,
) -> None:
    captured_options: dict[str, Any] = {}

    monkeypatch.setenv("PORT", "9000")
    monkeypatch.setenv("FORWARDED_ALLOW_IPS", "10.0.0.10")
    monkeypatch.setattr(
        serve.uvicorn,
        "run",
        lambda application, **options: captured_options.update(
            application=application,
            **options,
        ),
    )

    serve.main()

    assert captured_options == {
        "application": "app.main:app",
        "host": "0.0.0.0",
        "port": 9000,
        "workers": 1,
        "proxy_headers": True,
        "forwarded_allow_ips": "10.0.0.10",
    }
