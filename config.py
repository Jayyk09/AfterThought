"""Configuration management for AfterThought using Pydantic."""

import os
from pathlib import Path
from typing import Optional
import glob

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Required settings
    gemini_api_key: str = Field(
        ...,
        description="Google Gemini API key for summarization"
    )

    obsidian_output_path: Path = Field(
        ...,
        description="Output directory for Obsidian markdown files"
    )

    # Optional settings with defaults
    apple_podcasts_db_path: Optional[Path] = Field(
        default=None,
        description="Path to Apple Podcasts MTLibrary.sqlite database"
    )

    ttml_cache_path: Optional[Path] = Field(
        default=None,
        description="Path to Apple Podcasts TTML transcript cache"
    )

    tracking_db_path: Path = Field(
        default=Path.home() / ".afterthought" / "tracking.db",
        description="Path to tracking database for processed episodes"
    )

    gemini_model: str = Field(
        default="gemini-2.0-flash-exp",
        description="Gemini model to use for summarization"
    )

    default_days_filter: int = Field(
        default=7,
        ge=1,
        le=365,
        description="Default number of days to look back for episodes"
    )

    preserve_speakers: bool = Field(
        default=True,
        description="Whether to preserve speaker identification in transcripts"
    )

    max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of API retry attempts"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @field_validator("gemini_api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate that API key is not a placeholder."""
        if not v or v == "your_api_key_here":
            raise ValueError(
                "GEMINI_API_KEY is required. Get your API key from "
                "https://aistudio.google.com/app/apikey"
            )
        return v

    @field_validator("obsidian_output_path", "tracking_db_path", mode="before")
    @classmethod
    def expand_path(cls, v: Optional[str]) -> Optional[Path]:
        """Expand ~ and environment variables in paths."""
        if v is None:
            return None
        expanded = os.path.expanduser(os.path.expandvars(str(v)))
        return Path(expanded)

    @model_validator(mode="after")
    def auto_detect_apple_podcasts_paths(self):
        """Auto-detect Apple Podcasts database and cache paths if not provided."""
        # Auto-detect database path
        if self.apple_podcasts_db_path is None:
            db_pattern = os.path.expanduser(
                "~/Library/Group Containers/*.groups.com.apple.podcasts/Documents/MTLibrary.sqlite"
            )
            matches = glob.glob(db_pattern)
            if matches:
                self.apple_podcasts_db_path = Path(matches[0])
            else:
                raise ValueError(
                    "Could not auto-detect Apple Podcasts database. "
                    "Please set APPLE_PODCASTS_DB_PATH in your .env file."
                )

        # Auto-detect TTML cache path
        if self.ttml_cache_path is None:
            cache_pattern = os.path.expanduser(
                "~/Library/Group Containers/*.groups.com.apple.podcasts/Library/Cache/Assets/TTML"
            )
            matches = glob.glob(cache_pattern)
            if matches:
                self.ttml_cache_path = Path(matches[0])
            else:
                raise ValueError(
                    "Could not auto-detect TTML cache directory. "
                    "Please set TTML_CACHE_PATH in your .env file."
                )

        return self

    def validate_paths(self) -> None:
        """Validate that required paths exist and are accessible."""
        # Check database exists and is readable
        if not self.apple_podcasts_db_path.exists():
            raise FileNotFoundError(
                f"Apple Podcasts database not found at: {self.apple_podcasts_db_path}"
            )

        if not os.access(self.apple_podcasts_db_path, os.R_OK):
            raise PermissionError(
                f"Cannot read Apple Podcasts database at: {self.apple_podcasts_db_path}"
            )

        # Check TTML cache directory exists
        if not self.ttml_cache_path.exists():
            raise FileNotFoundError(
                f"TTML cache directory not found at: {self.ttml_cache_path}"
            )

        # Create output directory if it doesn't exist
        if not self.obsidian_output_path.exists():
            try:
                self.obsidian_output_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise PermissionError(
                    f"Cannot create output directory at: {self.obsidian_output_path}. "
                    f"Error: {e}"
                )

        # Check output directory is writable
        if not os.access(self.obsidian_output_path, os.W_OK):
            raise PermissionError(
                f"Output directory is not writable: {self.obsidian_output_path}"
            )

        # Create tracking database directory if it doesn't exist
        tracking_dir = self.tracking_db_path.parent
        if not tracking_dir.exists():
            try:
                tracking_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise PermissionError(
                    f"Cannot create tracking directory at: {tracking_dir}. "
                    f"Error: {e}"
                )


# Global settings instance
_settings: Optional[Settings] = None


def get_settings(validate: bool = True) -> Settings:
    """
    Get the global settings instance.

    Args:
        validate: Whether to validate paths on first load (default: True)

    Returns:
        Settings instance

    Raises:
        ValueError: If required configuration is missing or invalid
        FileNotFoundError: If required paths don't exist
        PermissionError: If paths are not accessible
    """
    global _settings

    if _settings is None:
        try:
            _settings = Settings()
            if validate:
                _settings.validate_paths()
        except Exception as e:
            raise RuntimeError(
                f"Failed to load configuration: {e}\n\n"
                "Make sure you have:\n"
                "1. Created a .env file (copy from .env.example)\n"
                "2. Set GEMINI_API_KEY in your .env file\n"
                "3. Set OBSIDIAN_OUTPUT_PATH in your .env file\n"
                "4. Apple Podcasts is installed and has been used"
            ) from e

    return _settings


def reset_settings() -> None:
    """Reset the global settings instance (useful for testing)."""
    global _settings
    _settings = None
