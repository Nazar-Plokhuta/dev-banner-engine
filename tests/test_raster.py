import struct
from pathlib import Path

import pytest

from src.core.errors import BannerEngineError
from src.core.presets import PRESET_REGISTRY, get_preset_spec
from src.core.schema import BannerConfig
from src.core.svg_builder import render_svg
from src.raster.exporter import RasterizationError, export_banner, rasterize_svg

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def make_config(preset: str) -> BannerConfig:
    return BannerConfig.model_validate(
        {
            "title": "Dev Banner Engine",
            "tagline": "Deterministic banners for engineers",
            "chips": ["Python", "FastAPI"],
            "preset": preset,
        }
    )


def png_size(png: bytes) -> tuple[int, int]:
    width, height = struct.unpack(">II", png[16:24])
    return int(width), int(height)


def test_rasterize_svg_returns_png_bytes() -> None:
    png = rasterize_svg(render_svg(make_config("github-og")))
    assert png.startswith(PNG_MAGIC)


@pytest.mark.parametrize("preset", PRESET_REGISTRY)
def test_export_banner_writes_png_with_preset_dimensions(tmp_path: Path, preset: str) -> None:
    target = tmp_path / "nested" / "out" / f"{preset}.png"
    result = export_banner(make_config(preset), target)
    spec = get_preset_spec(preset)
    assert result == target
    data = target.read_bytes()
    assert data.startswith(PNG_MAGIC)
    assert png_size(data) == (spec.width, spec.height)


def test_export_banner_accepts_string_path(tmp_path: Path) -> None:
    result = export_banner(make_config("github-og"), str(tmp_path / "a.png"))
    assert result.is_file()


@pytest.mark.parametrize("svg", ["", "not svg at all", "<svg", "<svg><unclosed></svg>"])
def test_malformed_input_raises_rasterization_error(svg: str) -> None:
    with pytest.raises(RasterizationError):
        rasterize_svg(svg)


def test_rasterization_error_is_domain_error() -> None:
    assert issubclass(RasterizationError, BannerEngineError)


def test_unwritable_target_raises_rasterization_error(tmp_path: Path) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("x")
    with pytest.raises(RasterizationError):
        export_banner(make_config("github-og"), blocker / "out.png")
