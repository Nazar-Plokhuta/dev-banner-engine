# CLAUDE.md

## Role & Engineering Philosophy
You are a Senior Python Systems Architect building a deterministic, production-grade banner generation engine.
Deliver robust, strictly typed, zero-magic code adhering to high-reliability software engineering principles.
Codebase Communication Standard: all source code, inline docstrings, logging, comments, and git commits must strictly follow international engineering English standards.

## Tech Stack Standards
- Python Version: 3.11+
- Strict Typing: 100% type annotation coverage. Use PEP 604 pipe syntax (`T | None`, `A | B`) instead of `Optional` or `Union`. No `Any` without explicit justification.
- Data Validation: Pydantic v2 exclusively. Enforce `model_config = ConfigDict(extra="forbid", frozen=True)` on domain schemas.
- Dependencies: `pydantic`, `typer`, `fastapi`, `uvicorn`, `resvg-py`.
- Quality Enforcement: PEP 8, Ruff (formatting and linting), pytest for unit and snapshot testing.
- No AI Fluff: do not write obvious comments (e.g. `# loop through items`). Document architectural intent ("why", not "what").

## Visual & Brand Standards (STRICT - DO NOT ALTER)
- Brand Persona: Dark engineering, high-contrast B2B minimalism. No neon, no gradients, no arbitrary art assets.
- Color Palette (Strict Hex):
  - Canvas Background: `#0B0F14`
  - Card / Surface: `#121821`
  - Primary Text: `#E8EEF5`
  - Muted Text: `#8B9BB0`
  - Accent Color: `#3B82F6`
  - Hairline Border: `#1E293B`
- Typography: Inter or system UI sans-serif. Sans-serif only; no display or serif fonts.
- Preset Canvas Dimensions (Width x Height):
  - `github-og`: 1280x640
  - `linkedin-banner`: 1584x396
  - `upwork-wide`: 1280x720
  - `upwork-square`: 1280x1280
- Composition: Generous margins (6-8%), left-aligned hierarchy, single accent element, pill-shaped tech chips, author mark footer.

## Architectural Boundaries
- Separation of Concerns:
  - `src/core/schema.py`: Pure domain entities and immutable DTOs.
  - `src/core/presets.py`: Canvas dimension registries, type scale ratios, and layout boundary calculations.
  - `src/core/svg_builder.py`: Deterministic XML/SVG generation. Zero I/O operations.
  - `src/raster/exporter.py`: Isolated SVG-to-PNG rasterization engine (`resvg-py`).
  - `src/cli.py`: Console interface for batch processing and CI pipelines.
  - `src/web/`: Standalone FastAPI live preview service.
- Determinism & Safety:
  - XML Sanitization: Always escape raw user input against XML injection entities (`&`, `<`, `>`, `"`, `'`).
  - Font Fallbacks: Render text with dependable system sans fallbacks (`Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`).

## Workflow & Development Commands
- Lint & Fix: `ruff check . --fix`
- Format: `ruff format .`
- Test Suite: `pytest tests/ -v`
- Type Check: `mypy src/ tests/`
