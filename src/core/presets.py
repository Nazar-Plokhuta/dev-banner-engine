from pydantic import BaseModel, ConfigDict

from src.core.errors import BannerEngineError


class UnknownPresetError(BannerEngineError, KeyError):
    """Raised when a preset key is not present in the registry."""

    def __str__(self) -> str:
        # KeyError.__str__ would wrap the message in repr quotes.
        return Exception.__str__(self)


class PresetSpec(BaseModel):
    """Pixel-exact layout constants for one canvas preset."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    width: int
    height: int
    padding_x: int
    padding_y: int
    title_font_size: int
    tagline_font_size: int
    chip_font_size: int
    chip_height: int
    chip_padding_x: int
    spine_width: int = 5
    spine_gap: int = 8
    # Measured from title baseline to tagline cap top; generous so descenders never touch it.
    title_tagline_gap: int = 34
    tagline_chips_gap: int = 28
    footer_inset: int = 48
    footer_font_size: int = 20
    footer_icon_size: int = 28
    chip_radius: int = 8
    grid_size: int = 56
    footer_icon_gap: int = 12


# padding_x is ~7% of width (brand range 6-8%). The linkedin preset is only 396px tall, so its
# type scale and vertical padding are reduced to keep title, tagline, chips and footer in frame.
PRESET_REGISTRY: dict[str, PresetSpec] = {
    "github-og": PresetSpec(
        width=1280,
        height=640,
        padding_x=88,
        padding_y=72,
        title_font_size=76,
        tagline_font_size=30,
        chip_font_size=15,
        chip_height=38,
        chip_padding_x=16,
    ),
    "linkedin-banner": PresetSpec(
        width=1584,
        height=396,
        padding_x=112,
        padding_y=40,
        title_font_size=44,
        tagline_font_size=22,
        chip_font_size=15,
        chip_height=38,
        chip_padding_x=16,
    ),
    "upwork-wide": PresetSpec(
        width=1280,
        height=720,
        padding_x=88,
        padding_y=80,
        title_font_size=82,
        tagline_font_size=32,
        chip_font_size=21,
        chip_height=38,
        chip_padding_x=16,
    ),
    "upwork-square": PresetSpec(
        width=1280,
        height=1280,
        padding_x=88,
        padding_y=96,
        title_font_size=76,
        tagline_font_size=36,
        chip_font_size=22,
        chip_height=38,
        chip_padding_x=16,
    ),
}


def get_preset_spec(preset: str) -> PresetSpec:
    try:
        return PRESET_REGISTRY[preset]
    except KeyError:
        known = ", ".join(sorted(PRESET_REGISTRY))
        raise UnknownPresetError(f"Unknown preset {preset!r}; expected one of: {known}") from None
