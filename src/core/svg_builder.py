from xml.sax.saxutils import escape

from src.core.presets import PresetSpec, get_preset_spec
from src.core.schema import BannerConfig

CANVAS_BG = "#0B0F14"
SURFACE = "#121821"
TEXT_PRIMARY = "#E8EEF5"
TEXT_MUTED = "#8B9BB0"
ACCENT = "#3B82F6"
BORDER = "#1E293B"
FONT_STACK = 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'

# Rasterizers expose no text metrics, so widths are estimated with a conservative average glyph
# width. Overestimating keeps pills and titles from clipping; underestimating would not.
_CHIP_GLYPH_RATIO = 0.6
_TITLE_GLYPH_RATIO = 0.58
_CHIP_GAP_RATIO = 0.3
_BLOCK_GAP_RATIO = 0.25
_MIN_TITLE_FONT_RATIO = 0.6
_TITLE_TAGLINE_RATIO = 0.25


def _chip_width(text: str, spec: PresetSpec) -> int:
    return round(len(text) * spec.chip_font_size * _CHIP_GLYPH_RATIO) + 2 * spec.chip_padding_x


def _fitted_title_size(title: str, spec: PresetSpec) -> int:
    """Shrink the title just enough to fit the content width, never below a readable floor."""
    available = spec.width - 2 * spec.padding_x
    estimated = len(title) * spec.title_font_size * _TITLE_GLYPH_RATIO
    if estimated <= available:
        return spec.title_font_size
    fitted = int(spec.title_font_size * available / estimated)
    return max(fitted, int(spec.title_font_size * _MIN_TITLE_FONT_RATIO))


def _wrap_chips(chips: list[str], spec: PresetSpec, gap: int) -> list[list[tuple[str, int]]]:
    available = spec.width - 2 * spec.padding_x
    rows: list[list[tuple[str, int]]] = [[]]
    used = 0
    for chip in chips:
        width = _chip_width(chip, spec)
        needed = width if not rows[-1] else used + gap + width
        if rows[-1] and needed > available:
            rows.append([])
            needed = width
        rows[-1].append((chip, width))
        used = needed
    return rows


def render_svg(config: BannerConfig) -> str:
    spec = get_preset_spec(config.preset)
    x = spec.padding_x
    gap = round(spec.tagline_font_size * _BLOCK_GAP_RATIO)
    chip_gap = round(spec.chip_height * _CHIP_GAP_RATIO)
    title_size = _fitted_title_size(config.title, spec)

    rows = _wrap_chips(config.chips, spec, chip_gap)

    # Offsets are relative to the block top so the whole group can be centred afterwards.
    title_dy = spec.accent_bar_height + gap * 2 + title_size
    tagline_dy = title_dy + spec.tagline_font_size + round(title_size * _TITLE_TAGLINE_RATIO)
    chips_dy = tagline_dy + gap * 2
    block_height = chips_dy + len(rows) * spec.chip_height + (len(rows) - 1) * chip_gap

    card_inset = spec.padding_y // 2
    footer_y = spec.height - spec.padding_y
    # The footer owns the bottom band, so the block is centred in the space above it rather than
    # on the raw canvas; clamping keeps an oversized block inside the card.
    region_top = card_inset + spec.padding_y // 2
    region_bottom = footer_y - spec.chip_font_size
    bar_y = max(region_top, region_top + (region_bottom - region_top - block_height) // 2)
    title_y = bar_y + title_dy
    tagline_y = bar_y + tagline_dy
    chips_top = bar_y + chips_dy

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{spec.width}" height="{spec.height}" '
        f'viewBox="0 0 {spec.width} {spec.height}">',
        f"<style>text {{ font-family: {FONT_STACK.replace(chr(34), chr(39))}; }}</style>",
        f'<rect id="canvas" width="{spec.width}" height="{spec.height}" fill="{CANVAS_BG}"/>',
        f'<rect id="card" x="{card_inset}" y="{card_inset}" '
        f'width="{spec.width - 2 * card_inset}" height="{spec.height - 2 * card_inset}" '
        f'rx="16" fill="{SURFACE}" stroke="{BORDER}" stroke-width="1"/>',
        f'<rect id="accent" x="{x}" y="{bar_y}" width="{spec.accent_bar_width}" '
        f'height="{spec.accent_bar_height}" fill="{ACCENT}"/>',
        f'<text id="title" x="{x}" y="{title_y}" font-size="{title_size}" font-weight="700" '
        f'fill="{TEXT_PRIMARY}">{escape(config.title)}</text>',
        f'<text id="tagline" x="{x}" y="{tagline_y}" font-size="{spec.tagline_font_size}" '
        f'font-weight="400" fill="{TEXT_MUTED}">{escape(config.tagline)}</text>',
    ]

    index = 0
    row_y = chips_top
    for row in rows:
        chip_x = x
        for chip, width in row:
            radius = spec.chip_height // 2
            text_y = row_y + (spec.chip_height + spec.chip_font_size) // 2 - 2
            parts.append(
                f'<g id="chip-{index}">'
                f'<rect x="{chip_x}" y="{row_y}" width="{width}" height="{spec.chip_height}" '
                f'rx="{radius}" fill="{SURFACE}" stroke="{BORDER}" stroke-width="1"/>'
                f'<text x="{chip_x + width // 2}" y="{text_y}" text-anchor="middle" '
                f'font-size="{spec.chip_font_size}" font-weight="500" fill="{TEXT_PRIMARY}">'
                f"{escape(chip)}</text></g>"
            )
            chip_x += width + chip_gap
            index += 1
        row_y += spec.chip_height + chip_gap

    parts.append(
        f'<text id="author" x="{spec.width - x}" y="{footer_y}" text-anchor="end" '
        f'font-size="{spec.chip_font_size}" font-weight="400" fill="{TEXT_MUTED}">'
        f"{escape(config.author)}</text>"
    )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"
