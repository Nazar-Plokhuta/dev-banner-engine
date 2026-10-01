import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from src.cli import app
from src.core.errors import BannerEngineError
from src.core.presets import PRESET_REGISTRY, UnknownPresetError

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
runner = CliRunner()


def base_args(out: Path, *extra: str) -> list[str]:
    return [
        "generate",
        "--title",
        "Dev Banner",
        "--tagline",
        "Ship faster",
        "--chips",
        "Python,FastAPI",
        "--out",
        str(out),
        *extra,
    ]


def test_generate_png(tmp_path: Path) -> None:
    result = runner.invoke(app, base_args(tmp_path))
    assert result.exit_code == 0, result.output
    target = tmp_path / "dev-banner-github-og.png"
    assert target.read_bytes().startswith(PNG_MAGIC)


def test_generate_with_custom_filename(tmp_path: Path) -> None:
    result = runner.invoke(app, base_args(tmp_path, "--filename", "hero.png"))
    assert result.exit_code == 0, result.output
    assert (tmp_path / "hero.png").read_bytes().startswith(PNG_MAGIC)


@pytest.mark.parametrize("filename", ["../escape.png", "nested/hero.png"])
def test_filename_rejects_paths(tmp_path: Path, filename: str) -> None:
    result = runner.invoke(app, base_args(tmp_path, "--filename", filename))
    assert result.exit_code == 1
    assert list(tmp_path.iterdir()) == []


def test_filename_rejects_all_presets(tmp_path: Path) -> None:
    result = runner.invoke(app, base_args(tmp_path, "--all-presets", "--filename", "hero.png"))
    assert result.exit_code == 1
    assert list(tmp_path.iterdir()) == []


def test_generate_svg_with_repeated_chip_flags(tmp_path: Path) -> None:
    args = base_args(tmp_path, "--format", "svg", "--preset", "upwork-card", "--chips", "Rust")
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    svg = (tmp_path / "dev-banner-upwork-card.svg").read_text(encoding="utf-8")
    assert svg.startswith("<svg") and "Rust" in svg and "FastAPI" in svg


def test_all_presets_generates_both_preset_files(tmp_path: Path) -> None:
    result = runner.invoke(app, base_args(tmp_path, "--all-presets"))
    assert result.exit_code == 0, result.output
    names = sorted(p.name for p in tmp_path.iterdir())
    assert names == sorted(f"dev-banner-{name}.png" for name in PRESET_REGISTRY)
    assert len(names) == 2


def write_config(path: Path, payload: Any) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


SAMPLE: dict[str, Any] = {
    "title": "Alpha",
    "tagline": "First",
    "chips": ["Python"],
    "preset": "github-og",
}


def test_batch_with_single_config(tmp_path: Path) -> None:
    config = write_config(tmp_path / "c.json", SAMPLE)
    result = runner.invoke(app, ["batch", "--config", str(config), "--out", str(tmp_path / "o")])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "o" / "alpha-github-og.png").is_file()


def test_batch_with_config_list(tmp_path: Path) -> None:
    config = write_config(tmp_path / "c.json", [SAMPLE, {**SAMPLE, "title": "Beta"}])
    out = tmp_path / "o"
    args = ["batch", "--config", str(config), "--out", str(out), "--format", "svg"]
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    assert sorted(p.name for p in out.iterdir()) == [
        "alpha-github-og.svg",
        "beta-github-og.svg",
    ]


def test_batch_rejects_colliding_outputs(tmp_path: Path) -> None:
    config = write_config(tmp_path / "c.json", [SAMPLE, SAMPLE])
    result = runner.invoke(app, ["batch", "--config", str(config), "--out", str(tmp_path / "o")])
    assert result.exit_code == 1
    assert "same output file" in result.output


def test_title_too_long_reports_field(tmp_path: Path) -> None:
    args = base_args(tmp_path)
    args[args.index("Dev Banner")] = "t" * 61
    result = runner.invoke(app, args)
    assert result.exit_code == 1
    assert "title" in result.output and "at most 60" in result.output
    assert "Traceback" not in result.output
    assert not any(tmp_path.iterdir())


def test_missing_required_option_fails(tmp_path: Path) -> None:
    result = runner.invoke(app, ["generate", "--tagline", "x", "--out", str(tmp_path)])
    assert result.exit_code != 0
    assert "--title" in result.output


def test_missing_chips_is_actionable(tmp_path: Path) -> None:
    args = ["generate", "--title", "a", "--tagline", "b", "--out", str(tmp_path)]
    result = runner.invoke(app, args)
    assert result.exit_code == 1
    assert "chips" in result.output


def test_unknown_preset_fails_cleanly(tmp_path: Path) -> None:
    result = runner.invoke(app, base_args(tmp_path, "--preset", "nope"))
    assert result.exit_code == 1
    assert "preset" in result.output


@pytest.mark.parametrize("content", ["{not json", '"just a string"', "[1]"])
def test_batch_invalid_content_fails_cleanly(tmp_path: Path, content: str) -> None:
    config = tmp_path / "c.json"
    config.write_text(content, encoding="utf-8")
    result = runner.invoke(app, ["batch", "--config", str(config), "--out", str(tmp_path / "o")])
    assert result.exit_code == 1
    assert "Traceback" not in result.output


def test_batch_missing_file_fails_cleanly(tmp_path: Path) -> None:
    result = runner.invoke(app, ["batch", "--config", str(tmp_path / "missing.json")])
    assert result.exit_code == 1
    assert "cannot read" in result.output


def test_unknown_preset_error_keeps_domain_and_key_semantics() -> None:
    error = UnknownPresetError("Unknown preset 'x'")
    assert isinstance(error, BannerEngineError)
    assert isinstance(error, KeyError)
    assert str(error) == "Unknown preset 'x'"


def test_upwork_card_preset_is_accepted(tmp_path: Path) -> None:
    args = base_args(tmp_path, "--format", "svg", "--preset", "upwork-card")
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    svg = (tmp_path / "dev-banner-upwork-card.svg").read_text(encoding="utf-8")
    assert 'width="1200" height="900"' in svg
