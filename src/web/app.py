from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response

from src.core.naming import slugify
from src.core.schema import BannerConfig
from src.core.svg_builder import render_svg
from src.raster.exporter import RasterizationError, rasterize_svg

_INDEX_HTML = Path(__file__).parent / "static" / "index.html"

# The dashboard ships one inline script/style block, so 'unsafe-inline' is required; everything
# else is pinned to same-origin. Previews are shown via blob: images, which never execute scripts.
_CONTENT_SECURITY_POLICY = (
    "default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' blob:; connect-src 'self'; base-uri 'none'; form-action 'none'; "
    "frame-ancestors 'none'"
)

app = FastAPI(title="Dev Banner Engine Preview", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def security_headers(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = _CONTENT_SECURITY_POLICY
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return HTMLResponse(_INDEX_HTML.read_text(encoding="utf-8"))


@app.post("/api/render/svg")
def render_svg_endpoint(config: BannerConfig) -> Response:
    return Response(content=render_svg(config), media_type="image/svg+xml")


@app.post("/api/render/png")
def render_png_endpoint(config: BannerConfig) -> Response:
    try:
        png = rasterize_svg(render_svg(config))
    except RasterizationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    filename = f"{slugify(config.title)}-{config.preset}.png"
    return Response(
        content=png,
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
