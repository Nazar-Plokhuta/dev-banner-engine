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

    spine = by_id(root, "spine") if spec.layout == "left" else None
    title_y = float(by_id(root, "title").get("y", ""))
    tagline = root.find(".//*[@id='tagline']")
    author = root.find(".//*[@id='author']")

    chip_rects = [
        rect for group in chip_groups(root) if (rect := group.find(f"{SVG_NS}rect")) is not None
    ]
    assert chip_rects
    tops = [float(r.get("y", "")) for r in chip_rects]
    bottoms = [float(r.get("y", "")) + float(r.get("height", "")) for r in chip_rects]
    rights = [float(r.get("x", "")) + float(r.get("width", "")) for r in chip_rects]

    if spine is not None:
        assert float(spine.get("x", "")) >= 0
    if tagline is not None:
        tagline_y = float(tagline.get("y", ""))
        assert title_y < tagline_y - spec.tagline_font_size * 0.5
        assert tagline_y < min(tops)
    else:
        assert title_y < min(tops)
    if author is not None:
        assert max(bottoms) < float(author.get("y", "")) - spec.footer_icon_size
    else:
        card = by_id(root, "card")
        assert max(bottoms) < float(card.get("y", "")) + float(card.get("height", ""))
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
        spec = get_preset_spec(preset)
        assert rect.get("height") == str(spec.chip_height)
        assert rect.get("rx") == str(spec.chip_radius)
        assert rect.get("fill") == (spec.chip_fill or "#16202E")
        assert rect.get("stroke") == (spec.chip_stroke or "#2D3B4E")
        assert rect.get("stroke-width") == str(spec.chip_stroke_width)
        assert text.get("font-weight") == str(spec.chip_font_weight)
        assert text.get("fill") == (spec.chip_text_fill or "#E8EEF5")
        assert text.get("font-size") == str(spec.chip_font_size)


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


def test_upwork_card_is_an_icon_like_title_and_badges_stack() -> None:
    spec = get_preset_spec("upwork-card")
    github = get_preset_spec("github-og")
    assert spec.layout == "center" and github.layout == "left"
    assert not spec.show_tagline and not spec.show_footer
    assert github.show_tagline and github.show_footer
    assert (spec.title_font_size, spec.title_font_weight, spec.title_fill) == (136, 800, "#FFFFFF")
    assert (spec.chip_height, spec.chip_padding_x, spec.chip_radius) == (92, 36, 18)
    assert (spec.chip_font_size, spec.chip_font_weight, spec.chip_text_fill) == (44, 700, "#FFFFFF")
    assert (spec.chip_fill, spec.chip_stroke, spec.chip_stroke_width) == ("#1E293B", "#3B82F6", 2)
    assert spec.chip_gap == 16 and spec.title_chips_gap == 44

    # A short title keeps the nominal 136px; longer ones are fitted by the shared shrink rule.
    root = parse(render_svg(make_config(preset="upwork-card", title="Dev Kit")))
    center = spec.width / 2
    for removed in ("spine", "tagline", "footer", "author", "github-mark"):
        assert root.find(f".//*[@id='{removed}']") is None
    assert "Ship faster" not in render_svg(make_config(preset="upwork-card"))

    title = by_id(root, "title")
    assert title.get("text-anchor") == "middle" and float(title.get("x", "")) == center
    assert title.get("font-size") == "136" and title.get("font-weight") == "800"
    assert title.get("fill") == "#FFFFFF"

    title_y = float(title.get("y", ""))
    rects = [r for g in chip_groups(root) if (r := g.find(f"{SVG_NS}rect")) is not None]
    assert float(rects[0].get("y", "")) - title_y == 44
    xs = sorted((float(r.get("x", "")), float(r.get("width", ""))) for r in rects)
    assert all(nx - (x + w) == 16 for (x, w), (nx, _) in zip(xs, xs[1:], strict=False))
    left, right = xs[0][0], xs[-1][0] + xs[-1][1]
    assert abs((left + right) / 2 - center) <= 1

    block_top = title_y - round(136 * 0.72)
    block_bottom = float(rects[-1].get("y", "")) + 92
    assert abs((block_top + block_bottom) / 2 - spec.height / 2) <= 1


def test_upwork_card_title_fits_content_width() -> None:
    spec = get_preset_spec("upwork-card")
    root = parse(render_svg(make_config(preset="upwork-card", title="Dev Banner Engine")))
    size = int(by_id(root, "title").get("font-size", ""))
    assert int(spec.title_font_size * 0.6) <= size < spec.title_font_size
    assert len("Dev Banner Engine") * size * 0.58 <= spec.width - 2 * spec.padding_x
