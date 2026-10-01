from typing import Literal

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
    chip_font_weight: int = 500
    # Colour and stroke overrides fall back to the brand tokens in the SVG builder when None.
    chip_fill: str | None = None
    chip_stroke: str | None = None
    chip_stroke_width: int = 1
    chip_text_fill: str | None = None
    chip_gap: int | None = None
    title_font_weight: int = 700
    title_fill: str | None = None
    grid_size: int = 56
    footer_icon_gap: int = 12
    layout: Literal["left", "center"] = "left"
    # Thumbnail-first presets drop the tagline: it is unreadable once the card is downscaled.
    show_tagline: bool = True
    show_footer: bool = True
    title_chips_gap: int = 48
    # Centered layout only: distance from the card bottom to the lowest edge of the footer group.
    footer_bottom_inset: int = 44


# padding_x is ~7% of the github-og width (brand range 6-8%). upwork-card uses a 56px margin as
# its type scale is sized to fill the 4:3 crop container.
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
    # Upwork shows this card at roughly 240x180, so it is built like an app icon: only a giant
    # title and heavy, high-contrast badges. Tagline and footer are dropped as they turn to noise.
    "upwork-card": PresetSpec(
        width=1200,
        height=900,
        padding_x=56,
        padding_y=80,
        title_font_size=136,
        title_font_weight=800,
        title_fill="#FFFFFF",
        tagline_font_size=28,
        chip_font_size=44,
        chip_height=92,
        chip_padding_x=36,
        chip_radius=18,
        chip_font_weight=700,
        chip_fill="#1E293B",
        chip_stroke="#3B82F6",
        chip_stroke_width=2,
        chip_text_fill="#FFFFFF",
        chip_gap=16,
        grid_size=64,
        layout="center",
        show_tagline=False,
        show_footer=False,
        title_chips_gap=44,
    ),
}


def get_preset_spec(preset: str) -> PresetSpec:
    try:
        return PRESET_REGISTRY[preset]
    except KeyError:
        known = ", ".join(sorted(PRESET_REGISTRY))
        raise UnknownPresetError(f"Unknown preset {preset!r}; expected one of: {known}") from None
