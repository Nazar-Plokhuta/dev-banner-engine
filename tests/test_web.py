from typing import Any
from xml.etree import ElementTree

import pytest
from fastapi.testclient import TestClient

from src.cli import app as cli_app
from src.web.app import app

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
client = TestClient(app)

PAYLOAD: dict[str, Any] = {
    "title": "Dev Banner",
    "tagline": "Ship faster",
    "chips": ["Python", "FastAPI"],
    "preset": "upwork-card",
}


def test_index_serves_dashboard() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "#0B0F14" in response.text and "/api/render/svg" in response.text


def test_security_headers_present() -> None:
    headers = client.get("/").headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in headers["content-security-policy"]


def test_render_svg_returns_valid_svg() -> None:
    response = client.post("/api/render/svg", json=PAYLOAD)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")
    root = ElementTree.fromstring(response.text)
    assert root.get("width") == "1200" and root.get("height") == "900"


def test_render_png_returns_attachment() -> None:
    response = client.post("/api/render/png", json=PAYLOAD)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.headers["content-disposition"] == (
        'attachment; filename="dev-banner-upwork-card.png"'
    )
    assert response.content.startswith(PNG_MAGIC)


@pytest.mark.parametrize("route", ["/api/render/svg", "/api/render/png"])
@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"title": "t" * 61}, "title"),
        ({"chips": []}, "chips"),
        ({"preset": "nope"}, "preset"),
        ({"unexpected": 1}, "unexpected"),
    ],
)
def test_validation_errors_are_structured(
    route: str, overrides: dict[str, Any], field: str
) -> None:
    response = client.post(route, json={**PAYLOAD, **overrides})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any(field in error["loc"] for error in detail)
    assert all("msg" in error for error in detail)


def test_cors_allows_only_localhost_origins() -> None:
    allowed = client.get("/", headers={"Origin": "http://localhost:3000"})
    denied = client.get("/", headers={"Origin": "https://evil.example"})
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert "access-control-allow-origin" not in denied.headers


def test_serve_command_runs_uvicorn(monkeypatch: pytest.MonkeyPatch) -> None:
    import uvicorn
    from typer.testing import CliRunner

    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(uvicorn, "run", lambda application, **kwargs: calls.append(kwargs))
    result = CliRunner().invoke(cli_app, ["serve", "--port", "9001"])
    assert result.exit_code == 0, result.output
    assert calls == [{"host": "127.0.0.1", "port": 9001}]


def test_render_svg_supports_upwork_card() -> None:
    response = client.post("/api/render/svg", json={**PAYLOAD, "preset": "upwork-card"})
    assert response.status_code == 200
    root = ElementTree.fromstring(response.text)
    assert root.get("width") == "1200" and root.get("height") == "900"
