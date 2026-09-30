from xml.sax.saxutils import escape

from src.core.presets import PresetSpec, get_preset_spec
from src.core.schema import BannerConfig

CANVAS_BG = "#0B0F14"
SURFACE = "#121821"
TEXT_PRIMARY = "#E8EEF5"
TEXT_MUTED = "#8B9BB0"
ACCENT = "#3B82F6"
BORDER = "#1E293B"
CHIP_SURFACE = "#16202E"
CHIP_BORDER = "#2D3B4E"
FOOTER_COLOR = "#94A3B8"
GRID_OPACITY = "0.2"
FONT_STACK = 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'

# Rasterizers expose no text metrics, so widths are estimated with a conservative average glyph
# width. Overestimating keeps pills and titles from clipping; underestimating would not.
_CHIP_GLYPH_RATIO = 0.6
_TITLE_GLYPH_RATIO = 0.58
_CHIP_GAP_RATIO = 0.3
_MIN_TITLE_FONT_RATIO = 0.6
_CAP_HEIGHT_RATIO = 0.72
_FOOTER_GLYPH_RATIO = 0.56
_SPINE_HEIGHT_RATIO = 0.75

# Octicons "mark-github" (16x16 viewBox, MIT licensed), embedded so rendering needs no assets.
GITHUB_MARK_PATH = (
    "M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49"
    "-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 "
    "1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59"
    ".82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 "
    "1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 "
    "3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42"
    "-3.58-8-8-8z"
)
_GITHUB_MARK_VIEWBOX = 16


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
    chip_gap = round(spec.chip_height * _CHIP_GAP_RATIO)
    title_size = _fitted_title_size(config.title, spec)

    rows = _wrap_chips(config.chips, spec, chip_gap)

    # Offsets are relative to the block top so the whole group can be centred afterwards.
    title_cap = round(title_size * _CAP_HEIGHT_RATIO)
    tagline_cap = round(spec.tagline_font_size * _CAP_HEIGHT_RATIO)
    title_dy = title_cap
    tagline_dy = title_dy + spec.title_tagline_gap + tagline_cap
    chips_dy = tagline_dy + spec.tagline_chips_gap
    block_height = chips_dy + len(rows) * spec.chip_height + (len(rows) - 1) * chip_gap

    card_inset = spec.padding_y // 2
    footer_right = spec.width - card_inset - spec.footer_inset
    footer_y = spec.height - card_inset - spec.footer_inset
    # The footer owns the bottom band, so the block is centred in the space above it rather than
    # on the raw canvas; clamping keeps an oversized block inside the card.
    region_top = card_inset + spec.padding_y // 2
    region_bottom = footer_y - spec.footer_icon_size
    block_top = max(region_top, region_top + (region_bottom - region_top - block_height) // 2)
    title_y = block_top + title_dy
    tagline_y = block_top + tagline_dy
    chips_top = block_top + chips_dy

    spine_height = round(title_size * _SPINE_HEIGHT_RATIO)
    spine_y = title_y - (title_cap + spine_height) // 2

    author_width = round(len(config.author) * spec.footer_font_size * _FOOTER_GLYPH_RATIO)
    icon_x = footer_right - author_width - spec.footer_icon_gap - spec.footer_icon_size
    icon_y = footer_y - round(spec.footer_font_size * _CAP_HEIGHT_RATIO) // 2
    icon_y -= spec.footer_icon_size // 2
    icon_scale = spec.footer_icon_size / _GITHUB_MARK_VIEWBOX

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{spec.width}" height="{spec.height}" '
        f'viewBox="0 0 {spec.width} {spec.height}">',
        f'<defs><pattern id="grid-pattern" x="{card_inset}" y="{card_inset}" '
        f'width="{spec.grid_size}" height="{spec.grid_size}" patternUnits="userSpaceOnUse">'
        f'<path d="M {spec.grid_size} 0 L 0 0 L 0 {spec.grid_size}" fill="none" '
        f'stroke="{BORDER}" stroke-opacity="{GRID_OPACITY}" stroke-width="1"/></pattern></defs>',
        f"<style>text {{ font-family: {FONT_STACK.replace(chr(34), chr(39))}; }}</style>",
        f'<rect id="canvas" width="{spec.width}" height="{spec.height}" fill="{CANVAS_BG}"/>',
        f'<rect id="card" x="{card_inset}" y="{card_inset}" '
        f'width="{spec.width - 2 * card_inset}" height="{spec.height - 2 * card_inset}" '
        f'rx="16" fill="{SURFACE}" stroke="{BORDER}" stroke-width="1"/>',
        f'<rect id="grid" x="{card_inset}" y="{card_inset}" '
        f'width="{spec.width - 2 * card_inset}" height="{spec.height - 2 * card_inset}" '
        f'rx="16" fill="url(#grid-pattern)"/>',
        f'<rect id="spine" x="{x - spec.spine_gap - spec.spine_width}" y="{spine_y}" '
        f'width="{spec.spine_width}" height="{spine_height}" rx="{spec.spine_width / 2:g}" '
        f'fill="{ACCENT}"/>',
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
            text_y = row_y + (spec.chip_height + spec.chip_font_size) // 2 - 2
            parts.append(
                f'<g id="chip-{index}">'
                f'<rect x="{chip_x}" y="{row_y}" width="{width}" height="{spec.chip_height}" '
                f'rx="{spec.chip_radius}" fill="{CHIP_SURFACE}" stroke="{CHIP_BORDER}" '
                f'stroke-width="1"/>'
                f'<text x="{chip_x + width // 2}" y="{text_y}" text-anchor="middle" '
                f'font-size="{spec.chip_font_size}" font-weight="500" fill="{TEXT_PRIMARY}">'
                f"{escape(chip)}</text></g>"
            )
            chip_x += width + chip_gap
            index += 1
        row_y += spec.chip_height + chip_gap

    parts.append(
        f'<g id="footer"><path id="github-mark" d="{GITHUB_MARK_PATH}" fill="{FOOTER_COLOR}" '
        f'transform="translate({icon_x} {icon_y}) scale({icon_scale:g})"/>'
        f'<text id="author" x="{footer_right}" y="{footer_y}" text-anchor="end" '
        f'font-size="{spec.footer_font_size}" font-weight="600" fill="{FOOTER_COLOR}">'
        f"{escape(config.author)}</text></g>"
    )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"
