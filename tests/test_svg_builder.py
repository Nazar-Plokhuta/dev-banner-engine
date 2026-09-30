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


def chip_groups(root: ElementTree.Element) -> list[ElementTree.Element]:
    return [g for g in root.iter(f"{SVG_NS}g") if g.get("id", "").startswith("chip-")]


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

    spine = by_id(root, "spine")
    title_y = float(by_id(root, "title").get("y", ""))
    tagline_y = float(by_id(root, "tagline").get("y", ""))
    footer_y = float(by_id(root, "author").get("y", ""))

    chip_rects = [
        rect for group in chip_groups(root) if (rect := group.find(f"{SVG_NS}rect")) is not None
    ]
    assert chip_rects
    tops = [float(r.get("y", "")) for r in chip_rects]
    bottoms = [float(r.get("y", "")) + float(r.get("height", "")) for r in chip_rects]
    rights = [float(r.get("x", "")) + float(r.get("width", "")) for r in chip_rects]

    assert float(spine.get("x", "")) >= 0
    assert title_y < tagline_y - spec.tagline_font_size * 0.5
    assert tagline_y < min(tops)
    assert max(bottoms) < footer_y - spec.footer_icon_size
    assert max(rights) <= spec.width - spec.padding_x


def test_spine_is_vertical_accent_bonded_to_title() -> None:
    root = parse(render_svg(make_config(preset="github-og")))
    spine = by_id(root, "spine")
    title = by_id(root, "title")
    title_y = float(title.get("y", ""))
    cap = round(76 * 0.72)
    height = float(spine.get("height", ""))
    assert title.get("font-size") == "76"
    assert spine.get("fill") == "#3B82F6" and spine.get("rx") == "2.5"
    assert spine.get("width") == "5" and height == round(76 * 0.75)
    assert float(title.get("x", "")) - float(spine.get("x", "")) - 5 == 8
    # Centred on the cap-height band of the title.
    spine_centre = float(spine.get("y", "")) + height / 2
    assert abs(spine_centre - (title_y - cap / 2)) <= 1
    assert root.find(".//*[@id='accent']") is None


def test_grid_is_large_and_ultra_quiet_behind_content() -> None:
    root = parse(render_svg(make_config()))
    pattern = root.find(f".//{SVG_NS}pattern[@id='grid-pattern']")
    assert pattern is not None
    assert pattern.get("width") == "56" and pattern.get("height") == "56"
    line = pattern.find(f"{SVG_NS}path")
    assert line is not None
    assert line.get("stroke") == "#1E293B" and line.get("stroke-opacity") == "0.2"
    order = [el.get("id") for el in root if el.get("id")]
    assert order.index("card") < order.index("grid") < order.index("spine")
    assert order.index("grid") < order.index("title") < order.index("footer")


def test_tagline_and_chip_spacing_on_github_og() -> None:
    root = parse(render_svg(make_config()))
    title_y = float(by_id(root, "title").get("y", ""))
    tagline_y = float(by_id(root, "tagline").get("y", ""))
    assert by_id(root, "tagline").get("fill") == "#8B9BB0"
    assert tagline_y - round(30 * 0.72) - title_y == 34
    first_chip = chip_groups(root)[0].find(f"{SVG_NS}rect")
    assert first_chip is not None
    assert float(first_chip.get("y", "")) - tagline_y == 28


@pytest.mark.parametrize("preset", PRESET_REGISTRY)
def test_chips_are_crisp_rounded_rectangles(preset: str) -> None:
    root = parse(render_svg(make_config(preset=preset)))
    for group in chip_groups(root):
        rect = group.find(f"{SVG_NS}rect")
        text = group.find(f"{SVG_NS}text")
        assert rect is not None and text is not None
        assert rect.get("height") == "38" and rect.get("rx") == "8"
        assert (rect.get("fill"), rect.get("stroke")) == ("#16202E", "#2D3B4E")
        assert text.get("font-weight") == "500" and text.get("fill") == "#E8EEF5"
    github_text = chip_groups(parse(render_svg(make_config())))[0].find(f"{SVG_NS}text")
    assert github_text is not None and github_text.get("font-size") == "15"


def test_footer_groups_github_mark_with_author() -> None:
    root = parse(render_svg(make_config()))
    footer = by_id(root, "footer")
    mark = footer.find(f"{SVG_NS}path")
    author = by_id(root, "author")
    assert mark is not None and mark.get("fill") == "#94A3B8"
    assert mark.get("d", "").startswith("M8 0C3.58")
    assert f"scale({28 / 16:g})" in mark.get("transform", "")
    assert author.get("fill") == "#94A3B8"
    assert author.get("font-size") == "20" and author.get("font-weight") == "600"
    card = by_id(root, "card")
    card_right = float(card.get("x", "")) + float(card.get("width", ""))
    card_bottom = float(card.get("y", "")) + float(card.get("height", ""))
    assert card_right - float(author.get("x", "")) == 48
    assert card_bottom - float(author.get("y", "")) == 48


def test_rendering_is_self_contained() -> None:
    svg = render_svg(make_config())
    assert (
        "href" not in svg
        and "<image" not in svg
        and "http://" not in svg.replace("http://www.w3.org/2000/svg", "")
    )
