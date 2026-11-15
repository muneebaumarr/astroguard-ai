from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import dotenv_values


@dataclass(frozen=True)
class Settings:
    repository_backend: str = "memory"
    database_url: str | None = None
    cors_origins: tuple[str, ...] = ("http://127.0.0.1:5173", "http://localhost:5173")

    @classmethod
    def from_env(cls) -> "Settings":
        # Resolve configuration independently of the shell's current directory.
        values = dotenv_values(Path(__file__).resolve().parents[2] / ".env") | dict(os.environ)
        defaults = cls()
        return cls(
            repository_backend=values.get("REPOSITORY_BACKEND", "memory"),
            database_url=values.get("DATABASE_URL") or None,
            cors_origins=tuple(origin.strip() for origin in
                values.get("CORS_ORIGINS", ",".join(defaults.cors_origins)).split(",") if origin.strip()),
        )
