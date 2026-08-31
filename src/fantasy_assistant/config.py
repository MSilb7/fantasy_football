"""Configuration loading with an explicit boundary between metadata and secrets."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import tempfile
import tomllib
from typing import Mapping


class ConfigurationError(ValueError):
    """Raised when required local configuration is missing or invalid."""


@dataclass(frozen=True)
class LeagueIdentity:
    """ESPN identifiers used for one season of a logical league."""

    league_id: str
    team_id: str | None = None


@dataclass(frozen=True)
class LeagueProfile:
    """Non-secret identity and preferences for one fantasy league."""

    name: str
    league_id: str
    league_name: str | None = None
    team_id: str | None = None
    team_name: str | None = None
    seasons: tuple[int, ...] = ()
    season_identities: Mapping[int, LeagueIdentity] = field(default_factory=dict)

    def identity_for_season(self, season: int) -> LeagueIdentity:
        """Resolve ESPN IDs for a season, falling back to the profile defaults."""

        identity = self.season_identities.get(season)
        if identity is None:
            return LeagueIdentity(league_id=self.league_id, team_id=self.team_id)
        return LeagueIdentity(
            league_id=identity.league_id,
            team_id=identity.team_id if identity.team_id is not None else self.team_id,
        )


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
            f"League config not found: {path}. Run discover-leagues --write-config, or copy "
            "config/leagues.example.toml to config/leagues.toml and fill it in manually."
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
        league_name = str(raw["league_name"]).strip() if raw.get("league_name") else None
        team_id = str(raw["team_id"]).strip() if raw.get("team_id") is not None else None
        team_name = str(raw["team_name"]).strip() if raw.get("team_name") else None
        raw_season_identities = raw.get("season_identities", {})
        if not isinstance(raw_season_identities, dict):
            raise ConfigurationError(
                f"League profile {name!r} season_identities must be a TOML table."
            )
        season_identities: dict[int, LeagueIdentity] = {}
        for raw_season, raw_identity in raw_season_identities.items():
            try:
                season = int(raw_season)
            except (TypeError, ValueError) as error:
                raise ConfigurationError(
                    f"League profile {name!r} has invalid identity season {raw_season!r}."
                ) from error
            if not isinstance(raw_identity, dict):
                raise ConfigurationError(
                    f"League profile {name!r} identity for {season} must be a TOML table."
                )
            season_league_id = str(raw_identity.get("league_id", "")).strip()
            if not season_league_id:
                raise ConfigurationError(
                    f"League profile {name!r} identity for {season} is missing league_id."
                )
            season_team_id = (
                str(raw_identity["team_id"]).strip()
                if raw_identity.get("team_id") is not None
                else None
            )
            season_identities[season] = LeagueIdentity(
                league_id=season_league_id,
                team_id=season_team_id,
            )
        profiles[name] = LeagueProfile(
            name=name,
            league_id=league_id,
            league_name=league_name,
            team_id=team_id,
            team_name=team_name,
            seasons=seasons,
            season_identities=season_identities,
        )
    return profiles


def write_league_profiles(
    path: Path,
    profiles: Mapping[str, LeagueProfile],
    *,
    overwrite: bool = False,
) -> None:
    """Write non-secret league profiles as TOML using an atomic local update."""

    if path.exists() and not overwrite:
        raise ConfigurationError(f"League config already exists: {path}")
    if not profiles:
        raise ConfigurationError("Cannot write an empty league configuration.")

    lines = [
        "# Generated from the authenticated ESPN profile.",
        "# Credentials remain in .env and are never written here.",
        "",
    ]
    for name, profile in sorted(profiles.items()):
        if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
            raise ConfigurationError(f"Unsafe league profile name: {name!r}")
        lines.extend(
            [
                f"[leagues.{name}]",
                f"league_id = {json.dumps(profile.league_id, ensure_ascii=False)}",
            ]
        )
        if profile.league_name:
            lines.append(
                f"league_name = {json.dumps(profile.league_name, ensure_ascii=False)}"
            )
        if profile.team_id:
            lines.append(f"team_id = {json.dumps(profile.team_id, ensure_ascii=False)}")
        if profile.team_name:
            lines.append(f"team_name = {json.dumps(profile.team_name, ensure_ascii=False)}")
        lines.append(f"seasons = [{', '.join(str(season) for season in profile.seasons)}]")
        lines.append("")
        for season, identity in sorted(profile.season_identities.items()):
            lines.extend(
                [
                    f'[leagues.{name}.season_identities."{season}"]',
                    f"league_id = {json.dumps(identity.league_id, ensure_ascii=False)}",
                ]
            )
            if identity.team_id is not None:
                lines.append(
                    f"team_id = {json.dumps(identity.team_id, ensure_ascii=False)}"
                )
            lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        handle.write("\n".join(lines).rstrip() + "\n")
        temporary_path = Path(handle.name)
    temporary_path.replace(path)


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
