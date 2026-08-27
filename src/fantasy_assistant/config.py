"""Configuration loading with an explicit boundary between metadata and secrets."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import tomllib
from typing import Mapping


class ConfigurationError(ValueError):
    """Raised when required local configuration is missing or invalid."""


@dataclass(frozen=True)
class LeagueProfile:
    """Non-secret identity and preferences for one fantasy league."""

    name: str
    league_id: str
    team_name: str | None = None
    seasons: tuple[int, ...] = ()


@dataclass(frozen=True)
class ESPNCredentials:
    """Private ESPN browser-cookie credentials.

    Values are intentionally excluded from the representation so an error or log
    cannot accidentally print them.
    """

    espn_s2: str
    swid: str

    def __repr__(self) -> str:
        return "ESPNCredentials(espn_s2=<redacted>, swid=<redacted>)"


def load_league_profiles(path: Path) -> dict[str, LeagueProfile]:
    """Load named league profiles from a local TOML file."""

    if not path.exists():
        raise ConfigurationError(
            f"League config not found: {path}. Copy config/leagues.example.toml "
            "to config/leagues.toml and fill in your league metadata."
        )

    with path.open("rb") as handle:
        document = tomllib.load(handle)

    raw_profiles = document.get("leagues")
    if not isinstance(raw_profiles, dict) or not raw_profiles:
        raise ConfigurationError("The config must define at least one [leagues.<name>] table.")

    profiles: dict[str, LeagueProfile] = {}
    for name, raw in raw_profiles.items():
        if not isinstance(raw, dict):
            raise ConfigurationError(f"League profile {name!r} must be a TOML table.")
        league_id = str(raw.get("league_id", "")).strip()
        if not league_id:
            raise ConfigurationError(f"League profile {name!r} is missing league_id.")
        seasons = tuple(int(value) for value in raw.get("seasons", ()))
        team_name = str(raw["team_name"]).strip() if raw.get("team_name") else None
        profiles[name] = LeagueProfile(
            name=name,
            league_id=league_id,
            team_name=team_name,
            seasons=seasons,
        )
    return profiles


def _read_dotenv(path: Path) -> dict[str, str]:
    """Read the small KEY=VALUE subset needed by this project."""

    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.removeprefix("export ").split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key.strip()] = value
    return values


def load_espn_credentials(
    *,
    environ: Mapping[str, str] | None = None,
    dotenv_path: Path = Path(".env"),
) -> ESPNCredentials:
    """Load ESPN credentials, preferring process environment over `.env`.

    Uppercase names are canonical. Lowercase names remain supported so the
    preserved payout notebooks continue to share the same local `.env` file.
    """

    environment = dict(os.environ if environ is None else environ)
    dotenv = _read_dotenv(dotenv_path)

    def first(*names: str) -> str:
        for source in (environment, dotenv):
            for name in names:
                value = source.get(name, "").strip()
                if value:
                    return value
        return ""

    espn_s2 = first("ESPN_S2", "espn_s2")
    swid = first("ESPN_SWID", "SWID", "swid")
    missing = [name for name, value in (("ESPN_S2", espn_s2), ("ESPN_SWID", swid)) if not value]
    if missing:
        raise ConfigurationError(f"Missing ESPN credential(s): {', '.join(missing)}")
    return ESPNCredentials(espn_s2=espn_s2, swid=swid)
