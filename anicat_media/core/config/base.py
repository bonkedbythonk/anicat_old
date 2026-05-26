"""Shared base config classes — no domain imports, so safe for all modules."""

from pathlib import Path

from pydantic import BaseModel, field_validator


class BaseConfig(BaseModel):
    """Base config with automatic `~` expansion in any string field."""

    @field_validator("*", mode="before")
    @classmethod
    def expand_path(cls, v, info):
        if isinstance(v, str) and "~" in v:
            return Path(v).expanduser()
        return v


class OtherConfig(BaseConfig):
    """Marker base for configs that don't need their own path expansion."""

    pass
