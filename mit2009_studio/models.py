"""The public API deliberately exposes few controls."""

import unicodedata
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Stage = Literal["audio", "video", "text", "assembly"]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class NewProject(Input):
    name: str = Field(min_length=1, max_length=100)
    author: str = Field(min_length=1, max_length=80)
    aspect: Literal["vertical", "horizontal"] = "vertical"


class Generate(Input):
    stage: Stage
    asset_ids: list[str] = Field(default_factory=list, max_length=12)
    keyword: str = Field(default="", max_length=32)

    @field_validator("keyword")
    @classmethod
    def one_word(cls, value):
        value = unicodedata.normalize("NFC", value)
        if value and (
            any(c.isspace() or unicodedata.category(c).startswith("C") for c in value)
            or not any(c.isalnum() for c in value)
        ):
            raise ValueError("Enter exactly one word, without spaces.")
        return value


class Rating(Input):
    stars: int = Field(strict=True, ge=1, le=5)


class Approval(Input):
    candidate_id: str
    explanation: str = Field(min_length=5, max_length=1000)
    confirmed: Literal[True]
