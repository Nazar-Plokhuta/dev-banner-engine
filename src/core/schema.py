from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Chip = Annotated[str, StringConstraints(min_length=1, max_length=24)]
PresetName = Literal["github-og", "linkedin-banner", "upwork-wide", "upwork-square"]


class BannerConfig(BaseModel):
    """Immutable user-supplied banner content; bounds keep layouts from overflowing."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str = Field(min_length=1, max_length=60)
    tagline: str = Field(min_length=1, max_length=120)
    chips: list[Chip] = Field(min_length=1, max_length=6)
    preset: PresetName = "github-og"
    author: str = "Nazar-Plokhuta"
