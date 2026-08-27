"""Command-line entry points used by humans and prompting agents."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
import sys

from fantasy_assistant.config import (
    ConfigurationError,
    load_espn_credentials,
    load_league_profiles,
)
from fantasy_assistant.espn import ESPNAPIError, ESPNClient
from fantasy_assistant.ingestion import SnapshotStore, normalize_league_snapshot


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fantasy-assistant")
    parser.add_argument("--config", type=Path, default=Path("config/leagues.toml"))
    parser.add_argument("--dotenv", type=Path, default=Path(".env"))
    subcommands = parser.add_subparsers(dest="command", required=True)

    subcommands.add_parser("doctor", help="Validate local league metadata and ESPN credentials.")

    sync = subcommands.add_parser("sync-league", help="Fetch and store one ESPN league snapshot.")
    sync.add_argument("--league", required=True, help="Profile name from config/leagues.toml.")
    sync.add_argument("--season", required=True, type=int)
    sync.add_argument("--data-dir", type=Path, default=Path("data"))
    return parser


def _doctor(args: argparse.Namespace) -> int:
    profiles = load_league_profiles(args.config)
    load_espn_credentials(dotenv_path=args.dotenv)
    print(f"OK: {len(profiles)} league profile(s) loaded; ESPN credentials are present.")
    for profile in profiles.values():
        identity = f"; team={profile.team_name}" if profile.team_name else ""
        print(f"- {profile.name}: league_id={profile.league_id}{identity}")
    return 0


def _sync_league(args: argparse.Namespace) -> int:
    profiles = load_league_profiles(args.config)
    if args.league not in profiles:
        available = ", ".join(sorted(profiles))
        raise ConfigurationError(f"Unknown league profile {args.league!r}. Available: {available}")
    profile = profiles[args.league]
    credentials = load_espn_credentials(dotenv_path=args.dotenv)
    fetched_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    raw = ESPNClient(credentials).fetch_league(
        season=args.season,
        league_id=profile.league_id,
        matchup_periods=range(1, 19),
    )
    normalized = normalize_league_snapshot(raw, season=args.season, fetched_at=fetched_at)
    paths = SnapshotStore(args.data_dir).save(
        source="espn",
        league_id=profile.league_id,
        season=args.season,
        fetched_at=fetched_at,
        raw=raw,
        normalized=normalized,
    )
    print(
        f"Saved {normalized['league']['team_count']} teams and "
        f"{len(normalized['matchups'])} matchups."
    )
    print(f"Raw: {paths.raw}")
    print(f"Normalized: {paths.normalized}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "doctor":
            return _doctor(args)
        if args.command == "sync-league":
            return _sync_league(args)
    except (ConfigurationError, ESPNAPIError, OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
