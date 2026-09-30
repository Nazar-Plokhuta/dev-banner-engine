import json
import re
from pathlib import Path
from typing import Annotated, Literal

import typer
from pydantic import TypeAdapter, ValidationError

from src.core.errors import BannerEngineError
from src.core.presets import PRESET_REGISTRY
from src.core.schema import BannerConfig
from src.core.svg_builder import render_svg
from src.raster.exporter import RasterizationError, export_banner

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Generate deterministic developer banners.",
)

OutputFormat = Literal["png", "svg"]

_CONFIG_LIST_ADAPTER: TypeAdapter[list[BannerConfig]] = TypeAdapter(list[BannerConfig])


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "banner"


def _split_chips(raw: list[str]) -> list[str]:
    return [chip.strip() for value in raw for chip in value.split(",") if chip.strip()]


def _format_validation_error(error: ValidationError) -> str:
    lines = []
    for detail in error.errors():
        location = ".".join(str(part) for part in detail["loc"]) or "config"
        lines.append(f"  {location}: {detail['msg']}")
    return "Invalid banner configuration:\n" + "\n".join(lines)


def _export(config: BannerConfig, out_dir: Path, fmt: OutputFormat) -> Path:
    target = out_dir / f"{_slugify(config.title)}-{config.preset}.{fmt}"
    if fmt == "png":
        return export_banner(config, target)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_svg(config), encoding="utf-8")
    except OSError as exc:
        raise RasterizationError(f"Cannot write banner to {target}: {exc}") from exc
    return target


def _fail(message: str) -> typer.Exit:
    typer.echo(f"Error: {message}", err=True)
    return typer.Exit(code=1)


def _export_all(configs: list[BannerConfig], out_dir: Path, fmt: OutputFormat) -> None:
    targets = [f"{_slugify(c.title)}-{c.preset}" for c in configs]
    if len(set(targets)) != len(targets):
        raise _fail("multiple configurations would write to the same output file")
    for config in configs:
        typer.echo(str(_export(config, out_dir, fmt)))


@app.command()
def generate(
    title: Annotated[str, typer.Option(help="Banner title (1-60 characters).")],
    tagline: Annotated[str, typer.Option(help="Banner tagline (1-120 characters).")],
    chips: Annotated[
        list[str] | None,
        typer.Option(help="Tech chips; comma-separated and/or repeated (1-6 total)."),
    ] = None,
    preset: Annotated[str, typer.Option(help="Canvas preset.")] = "github-og",
    author: Annotated[str, typer.Option(help="Footer author mark.")] = "Nazar-Plokhuta",
    out: Annotated[Path, typer.Option(help="Output directory.")] = Path("output"),
    all_presets: Annotated[
        bool, typer.Option("--all-presets", help="Export every preset.")
    ] = False,
    fmt: Annotated[OutputFormat, typer.Option("--format", help="Output file format.")] = "png",
) -> None:
    """Generate one banner, or one per preset with --all-presets."""
    presets = list(PRESET_REGISTRY) if all_presets else [preset]
    try:
        configs = [
            BannerConfig.model_validate(
                {
                    "title": title,
                    "tagline": tagline,
                    "chips": _split_chips(chips or []),
                    "preset": name,
                    "author": author,
                }
            )
            for name in presets
        ]
        _export_all(configs, out, fmt)
    except ValidationError as exc:
        raise _fail(_format_validation_error(exc)) from None
    except BannerEngineError as exc:
        raise _fail(str(exc)) from None


@app.command()
def batch(
    config: Annotated[Path, typer.Option(help="JSON file with one config or a list of configs.")],
    out: Annotated[Path, typer.Option(help="Output directory.")] = Path("output"),
    fmt: Annotated[OutputFormat, typer.Option("--format", help="Output file format.")] = "png",
) -> None:
    """Generate banners from a JSON configuration file."""
    try:
        try:
            payload = json.loads(config.read_text(encoding="utf-8"))
        except OSError as exc:
            raise _fail(f"cannot read {config}: {exc.strerror or exc}") from None
        except json.JSONDecodeError as exc:
            raise _fail(f"{config} is not valid JSON: {exc}") from None
        items = payload if isinstance(payload, list) else [payload]
        _export_all(_CONFIG_LIST_ADAPTER.validate_python(items), out, fmt)
    except ValidationError as exc:
        raise _fail(_format_validation_error(exc)) from None
    except BannerEngineError as exc:
        raise _fail(str(exc)) from None
