from typing import Any
from xml.etree import ElementTree

import pytest

from src.core.presets import PRESET_REGISTRY, get_preset_spec
from src.core.schema import BannerConfig
from src.core.svg_builder import render_svg

SVG_NS = "{http://www.w3.org/2000/svg}"


def make_config(**overrides: Any) -> BannerConfig:
    data: dict[str, Any] = {
        "title": "Dev Banner Engine",
        "tagline": "Deterministic banners for engineers",
        "chips": ["Python", "FastAPI", "Pydantic"],
    }
    data.update(overrides)
    return BannerConfig(**data)


def parse(svg: str) -> ElementTree.Element:
    return ElementTree.fromstring(svg)


def by_id(root: ElementTree.Element, element_id: str) -> ElementTree.Element:
    found = root.find(f".//*[@id='{element_id}']")
    assert found is not None
    return found


def test_output_is_well_formed_and_deterministic() -> None:
    config = make_config()
    assert render_svg(config) == render_svg(config)
    assert parse(render_svg(config)).tag == f"{SVG_NS}svg"


def test_brand_colors_and_font_stack_present() -> None:
    svg = render_svg(make_config())
    for color in ("#0B0F14", "#121821", "#1E293B", "#3B82F6", "#E8EEF5", "#8B9BB0"):
        assert color in svg
    assert "Inter, -apple-system, BlinkMacSystemFont" in svg


@pytest.mark.parametrize("preset", PRESET_REGISTRY)
def test_dimensions_match_preset_spec(preset: str) -> None:
    spec = get_preset_spec(preset)
    root = parse(render_svg(make_config(preset=preset)))
    assert root.get("width") == str(spec.width)
    assert root.get("height") == str(spec.height)
    assert root.get("viewBox") == f"0 0 {spec.width} {spec.height}"


def test_user_strings_are_escaped() -> None:
    nasty = "<&\"'>"
    config = make_config(title=nasty, tagline=nasty, chips=[nasty], author=nasty)
    root = parse(render_svg(config))
    assert by_id(root, "title").text == nasty
    assert by_id(root, "tagline").text == nasty
    assert by_id(root, "author").text == nasty
    chip_text = by_id(root, "chip-0").find(f"{SVG_NS}text")
    assert chip_text is not None and chip_text.text == nasty


def test_script_injection_is_inert() -> None:
    root = parse(render_svg(make_config(title="</text><script>alert(1)</script>")))
    assert root.find(f".//{SVG_NS}script") is None


@pytest.mark.parametrize("preset", PRESET_REGISTRY)
@pytest.mark.parametrize(
    "config_overrides",
    [
        {},
        {"title": "T" * 60, "tagline": "g" * 120, "chips": ["c" * 24] * 6},
    ],
)
def test_layout_has_no_vertical_overlap(preset: str, config_overrides: dict[str, Any]) -> None:
    spec = get_preset_spec(preset)
    root = parse(render_svg(make_config(preset=preset, **config_overrides)))

    accent = by_id(root, "accent")
    accent_bottom = float(accent.get("y", "")) + float(accent.get("height", ""))
    title_y = float(by_id(root, "title").get("y", ""))
    tagline_y = float(by_id(root, "tagline").get("y", ""))
    footer_y = float(by_id(root, "author").get("y", ""))

    chip_rects = [
        rect
        for group in root.iter(f"{SVG_NS}g")
        if (rect := group.find(f"{SVG_NS}rect")) is not None
    ]
    assert chip_rects
    tops = [float(r.get("y", "")) for r in chip_rects]
    bottoms = [float(r.get("y", "")) + float(r.get("height", "")) for r in chip_rects]
    rights = [float(r.get("x", "")) + float(r.get("width", "")) for r in chip_rects]

    assert accent_bottom < title_y - spec.title_font_size * 0.5
    assert title_y < tagline_y - spec.tagline_font_size * 0.5
    assert tagline_y < min(tops)
    assert max(bottoms) < footer_y - spec.chip_font_size
    assert max(rights) <= spec.width - spec.padding_x
