from typing import Any

import pytest
from pydantic import ValidationError

from src.core.presets import PRESET_REGISTRY, PresetSpec, UnknownPresetError, get_preset_spec
from src.core.schema import BannerConfig

EXPECTED_DIMENSIONS = {
    "github-og": (1280, 640),
    "linkedin-banner": (1584, 396),
    "upwork-wide": (1280, 720),
    "upwork-square": (1280, 1280),
}


def make_config(**overrides: Any) -> BannerConfig:
    data: dict[str, Any] = {"title": "Dev Tools", "tagline": "Ship faster", "chips": ["Python"]}
    data.update(overrides)
    return BannerConfig(**data)


def test_valid_config_applies_defaults() -> None:
    config = make_config()
    assert config.preset == "github-og"
    assert config.author == "Nazar-Plokhuta"


def test_valid_config_at_upper_bounds() -> None:
    config = make_config(title="t" * 60, tagline="g" * 120, chips=["c" * 24] * 6)
    assert len(config.chips) == 6


def test_config_is_frozen() -> None:
    with pytest.raises(ValidationError):
        make_config().title = "other"


def test_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        make_config(unexpected="x")


@pytest.mark.parametrize(
    "overrides",
    [
        {"title": ""},
        {"title": "t" * 61},
        {"tagline": ""},
        {"tagline": "g" * 121},
        {"chips": []},
        {"chips": ["c"] * 7},
        {"chips": [""]},
        {"chips": ["c" * 25]},
        {"preset": "unknown"},
    ],
)
def test_rejects_invalid_values(overrides: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        make_config(**overrides)


def test_registry_covers_all_presets() -> None:
    assert set(PRESET_REGISTRY) == set(EXPECTED_DIMENSIONS)


@pytest.mark.parametrize(("name", "dimensions"), EXPECTED_DIMENSIONS.items())
def test_preset_dimensions_and_aspect_ratio(name: str, dimensions: tuple[int, int]) -> None:
    spec = get_preset_spec(name)
    assert (spec.width, spec.height) == dimensions
    assert spec.width / spec.height == pytest.approx(dimensions[0] / dimensions[1])


@pytest.mark.parametrize("name", EXPECTED_DIMENSIONS)
def test_preset_bounds_are_positive_and_fit_canvas(name: str) -> None:
    spec = get_preset_spec(name)
    assert all(value > 0 for value in spec.model_dump().values())
    assert 0.06 <= spec.padding_x / spec.width <= 0.08
    assert spec.padding_y * 2 < spec.height
    assert spec.spine_width > 0 and spec.footer_icon_size > 0
    assert spec.tagline_font_size < spec.title_font_size
    assert spec.chip_font_size < spec.chip_height


def test_linkedin_content_fits_narrow_height() -> None:
    spec = get_preset_spec("linkedin-banner")
    stacked = spec.title_font_size + spec.tagline_font_size + spec.chip_height
    assert stacked < spec.height - 2 * spec.padding_y


def test_unknown_preset_raises_domain_error() -> None:
    with pytest.raises(UnknownPresetError):
        get_preset_spec("nope")


def test_preset_spec_is_frozen() -> None:
    spec = get_preset_spec("github-og")
    assert isinstance(spec, PresetSpec)
    with pytest.raises(ValidationError):
        spec.width = 1
