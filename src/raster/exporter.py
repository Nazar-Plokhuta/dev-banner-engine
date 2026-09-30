from pathlib import Path

import resvg_py

from src.core.errors import BannerEngineError
from src.core.schema import BannerConfig
from src.core.svg_builder import render_svg


class RasterizationError(BannerEngineError):
    """Raised when SVG markup cannot be converted to PNG or written to disk."""


def rasterize_svg(svg_data: str) -> bytes:
    # resvg-py is a native extension; wrap every failure so callers only handle domain errors.
    try:
        png: bytes = resvg_py.svg_to_bytes(svg_string=svg_data)
    except Exception as exc:
        raise RasterizationError(f"SVG rasterization failed: {exc}") from exc
    if not png:
        raise RasterizationError("SVG rasterization produced no output")
    return png


def export_banner(config: BannerConfig, output_path: Path | str) -> Path:
    target = Path(output_path)
    png = rasterize_svg(render_svg(config))
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(png)
    except OSError as exc:
        raise RasterizationError(f"Cannot write banner to {target}: {exc}") from exc
    return target
