from pydantic import BaseModel, ConfigDict


class UnknownPresetError(KeyError):
    """Raised when a preset key is not present in the registry."""


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
    accent_bar_width: int
    accent_bar_height: int


# padding_x is ~7% of width (brand range 6-8%). The linkedin preset is only 396px tall, so its
# type scale and vertical padding are reduced to keep title, tagline, chips and footer in frame.
PRESET_REGISTRY: dict[str, PresetSpec] = {
    "github-og": PresetSpec(
        width=1280,
        height=640,
        padding_x=88,
        padding_y=72,
        title_font_size=64,
        tagline_font_size=30,
        chip_font_size=20,
        chip_height=44,
        chip_padding_x=20,
        accent_bar_width=72,
        accent_bar_height=6,
    ),
    "linkedin-banner": PresetSpec(
        width=1584,
        height=396,
        padding_x=112,
        padding_y=40,
        title_font_size=44,
        tagline_font_size=22,
        chip_font_size=15,
        chip_height=32,
        chip_padding_x=14,
        accent_bar_width=56,
        accent_bar_height=4,
    ),
    "upwork-wide": PresetSpec(
        width=1280,
        height=720,
        padding_x=88,
        padding_y=80,
        title_font_size=68,
        tagline_font_size=32,
        chip_font_size=21,
        chip_height=46,
        chip_padding_x=22,
        accent_bar_width=80,
        accent_bar_height=6,
    ),
    "upwork-square": PresetSpec(
        width=1280,
        height=1280,
        padding_x=88,
        padding_y=96,
        title_font_size=76,
        tagline_font_size=36,
        chip_font_size=22,
        chip_height=48,
        chip_padding_x=24,
        accent_bar_width=96,
        accent_bar_height=8,
    ),
}


def get_preset_spec(preset: str) -> PresetSpec:
    try:
        return PRESET_REGISTRY[preset]
    except KeyError:
        known = ", ".join(sorted(PRESET_REGISTRY))
        raise UnknownPresetError(f"Unknown preset {preset!r}; expected one of: {known}") from None
