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


def _chip_gap(spec: PresetSpec) -> int:
    if spec.chip_gap is not None:
        return spec.chip_gap
    return round(spec.chip_height * _CHIP_GAP_RATIO)


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


def _frame_parts(spec: PresetSpec, card_inset: int) -> list[str]:
    """Canvas, card and grid layers shared by every layout."""
    return [
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
    ]


def _chip_parts(
    row: list[tuple[str, int]], chip_x: int, row_y: int, index: int, gap: int, spec: PresetSpec
) -> list[str]:
    parts: list[str] = []
    for chip, width in row:
        cap_height = round(spec.chip_font_size * _CAP_HEIGHT_RATIO)
        text_y = row_y + (spec.chip_height + cap_height) // 2
        parts.append(
            f'<g id="chip-{index}">'
            f'<rect x="{chip_x}" y="{row_y}" width="{width}" height="{spec.chip_height}" '
            f'rx="{spec.chip_radius}" fill="{spec.chip_fill or CHIP_SURFACE}" '
            f'stroke="{spec.chip_stroke or CHIP_BORDER}" stroke-width="{spec.chip_stroke_width}"/>'
            f'<text x="{chip_x + width // 2}" y="{text_y}" text-anchor="middle" '
            f'font-size="{spec.chip_font_size}" font-weight="{spec.chip_font_weight}" '
            f'fill="{spec.chip_text_fill or TEXT_PRIMARY}">'
            f"{escape(chip)}</text></g>"
        )
        chip_x += width + gap
        index += 1
    return parts


def _footer_icon_y(baseline_y: int, spec: PresetSpec) -> int:
    """Top edge of the GitHub mark, vertically centred on the author text's cap height."""
    return (
        baseline_y
        - round(spec.footer_font_size * _CAP_HEIGHT_RATIO) // 2
        - spec.footer_icon_size // 2
    )


def _footer_part(
    author: str, spec: PresetSpec, *, baseline_y: int, icon_x: int, text_x: int, anchor: str
) -> str:
    icon_y = _footer_icon_y(baseline_y, spec)
    icon_scale = spec.footer_icon_size / _GITHUB_MARK_VIEWBOX
    return (
        f'<g id="footer"><path id="github-mark" d="{GITHUB_MARK_PATH}" fill="{FOOTER_COLOR}" '
        f'transform="translate({icon_x} {icon_y}) scale({icon_scale:g})"/>'
        f'<text id="author" x="{text_x}" y="{baseline_y}" text-anchor="{anchor}" '
        f'font-size="{spec.footer_font_size}" font-weight="600" fill="{FOOTER_COLOR}">'
        f"{escape(author)}</text></g>"
    )


def _author_width(author: str, spec: PresetSpec) -> int:
    return round(len(author) * spec.footer_font_size * _FOOTER_GLYPH_RATIO)


def render_svg(config: BannerConfig) -> str:
    spec = get_preset_spec(config.preset)
    if spec.layout == "center":
        return _render_centered(config, spec)
    return _render_left(config, spec)


def _render_left(config: BannerConfig, spec: PresetSpec) -> str:
    x = spec.padding_x
    chip_gap = _chip_gap(spec)
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

    icon_x = (
        footer_right
        - _author_width(config.author, spec)
        - spec.footer_icon_gap
        - spec.footer_icon_size
    )

    parts = _frame_parts(spec, card_inset)
    parts += [
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
        parts += _chip_parts(row, x, row_y, index, chip_gap, spec)
        index += len(row)
        row_y += spec.chip_height + chip_gap

    parts.append(
        _footer_part(
            config.author,
            spec,
            baseline_y=footer_y,
            icon_x=icon_x,
            text_x=footer_right,
            anchor="end",
        )
    )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def _render_centered(config: BannerConfig, spec: PresetSpec) -> str:
    center_x = spec.width // 2
    chip_gap = _chip_gap(spec)
    title_size = _fitted_title_size(config.title, spec)
    rows = _wrap_chips(config.chips, spec, chip_gap)

    title_cap = round(title_size * _CAP_HEIGHT_RATIO)
    tagline_cap = round(spec.tagline_font_size * _CAP_HEIGHT_RATIO)
    title_dy = title_cap
    tagline_dy = title_dy + spec.title_tagline_gap + tagline_cap
    chips_dy = (
        tagline_dy + spec.tagline_chips_gap
        if spec.show_tagline
        else title_dy + spec.title_chips_gap
    )
    block_height = chips_dy + len(rows) * spec.chip_height + (len(rows) - 1) * chip_gap

    card_inset = spec.padding_y // 2
    # The icon is the tallest footer element, so its bottom edge defines the group's bottom.
    cap_half = round(spec.footer_font_size * _CAP_HEIGHT_RATIO) // 2
    icon_below_baseline = spec.footer_icon_size - spec.footer_icon_size // 2 - cap_half
    footer_y = spec.height - card_inset - spec.footer_bottom_inset - icon_below_baseline
    # Centre between the card top and the footer mark (or the card bottom when there is no
    # footer) so the footer band does not skew the balance; the clamp keeps an oversized block
    # inside the card padding.
    limit_bottom = _footer_icon_y(footer_y, spec) if spec.show_footer else spec.height - card_inset
    free_space = limit_bottom - card_inset - block_height
    block_top = max(card_inset + spec.padding_y // 2, card_inset + free_space // 2)

    parts = _frame_parts(spec, card_inset)
    parts += [
        f'<text id="title" x="{center_x}" y="{block_top + title_dy}" text-anchor="middle" '
        f'font-size="{title_size}" font-weight="{spec.title_font_weight}" '
        f'fill="{spec.title_fill or TEXT_PRIMARY}">{escape(config.title)}</text>',
    ]
    if spec.show_tagline:
        parts.append(
            f'<text id="tagline" x="{center_x}" y="{block_top + tagline_dy}" '
            f'text-anchor="middle" font-size="{spec.tagline_font_size}" font-weight="400" '
            f'fill="{TEXT_MUTED}">{escape(config.tagline)}</text>'
        )

    index = 0
    row_y = block_top + chips_dy
    for row in rows:
        row_width = sum(width for _, width in row) + chip_gap * (len(row) - 1)
        parts += _chip_parts(row, center_x - row_width // 2, row_y, index, chip_gap, spec)
        index += len(row)
        row_y += spec.chip_height + chip_gap

    if spec.show_footer:
        footer_width = (
            spec.footer_icon_size + spec.footer_icon_gap + _author_width(config.author, spec)
        )
        icon_x = center_x - footer_width // 2
        parts.append(
            _footer_part(
                config.author,
                spec,
                baseline_y=footer_y,
                icon_x=icon_x,
                text_x=icon_x + spec.footer_icon_size + spec.footer_icon_gap,
                anchor="start",
            )
        )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"
