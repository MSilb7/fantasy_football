"""Command-line entry points used by humans and prompting agents."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
import re
import sys
import unicodedata

from fantasy_assistant.config import (
    ConfigurationError,
    LeagueProfile,
    load_espn_credentials,
    load_league_profiles,
    write_league_profiles,
)
from fantasy_assistant.espn import (
    DiscoveredLeague,
    ESPNAPIError,
    ESPNClient,
    ESPNLeagueDiscoveryClient,
)
from fantasy_assistant.ingestion import (
    SnapshotStore,
    normalize_draft_snapshot,
    normalize_league_snapshot,
    normalize_player_evidence,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fantasy-assistant")
    parser.add_argument("--config", type=Path, default=Path("config/leagues.toml"))
    parser.add_argument("--dotenv", type=Path, default=Path(".env"))
    subcommands = parser.add_subparsers(dest="command", required=True)

    subcommands.add_parser("doctor", help="Validate local league metadata and ESPN credentials.")

    discover = subcommands.add_parser(
        "discover-leagues",
        help="Discover fantasy football leagues from the authenticated ESPN profile.",
    )
    discover.add_argument("--season", type=int, help="Limit results to one season.")
    discover.add_argument(
        "--write-config",
        action="store_true",
        help="Write discovered identities to the configured leagues TOML file.",
    )
    discover.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing league config when used with --write-config.",
    )

    sync = subcommands.add_parser("sync-league", help="Fetch and store one ESPN league snapshot.")
    sync.add_argument("--league", required=True, help="Profile name from config/leagues.toml.")
    sync.add_argument("--season", required=True, type=int)
    sync.add_argument("--data-dir", type=Path, default=Path("data"))

    sync_draft = subcommands.add_parser(
        "sync-draft",
        help="Fetch and store pick-level ESPN draft state for one league season.",
    )
    sync_draft.add_argument("--league", required=True, help="Profile name from config/leagues.toml.")
    sync_draft.add_argument("--season", required=True, type=int)
    sync_draft.add_argument("--data-dir", type=Path, default=Path("data"))

    sync_players = subcommands.add_parser(
        "sync-player-evidence",
        help="Fetch and store ESPN availability, ADP, ranks, projections, and stats.",
    )
    sync_players.add_argument(
        "--league", required=True, help="Profile name from config/leagues.toml."
    )
    sync_players.add_argument("--season", required=True, type=int)
    sync_players.add_argument("--limit", type=int, default=5000)
    sync_players.add_argument("--data-dir", type=Path, default=Path("data"))
    return parser


def _doctor(args: argparse.Namespace) -> int:
    profiles = load_league_profiles(args.config)
    load_espn_credentials(dotenv_path=args.dotenv)
    print(f"OK: {len(profiles)} league profile(s) loaded; ESPN credentials are present.")
    for profile in profiles.values():
        identity = f"; team={profile.team_name}" if profile.team_name else ""
        league = f"; league={profile.league_name}" if profile.league_name else ""
        print(f"- {profile.name}: league_id={profile.league_id}{league}{identity}")
    return 0


def _slug(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", ascii_value.casefold()).strip("_")


def _profiles_from_discovered(
    leagues: list[DiscoveredLeague],
) -> dict[str, LeagueProfile]:
    grouped: dict[tuple[str, str], list[DiscoveredLeague]] = {}
    for league in leagues:
        grouped.setdefault((league.league_id, league.team_id), []).append(league)

    profiles: dict[str, LeagueProfile] = {}
    for (league_id, team_id), observations in sorted(
        grouped.items(), key=lambda item: (item[1][0].league_name.casefold(), item[0])
    ):
        latest = max(observations, key=lambda league: league.season)
        base_name = _slug(latest.league_name) or f"league_{league_id}"
        profile_name = base_name
        if profile_name in profiles:
            profile_name = f"{base_name}_{league_id}"
        if profile_name in profiles:
            profile_name = f"{profile_name}_{team_id}"
        profiles[profile_name] = LeagueProfile(
            name=profile_name,
            league_id=league_id,
            league_name=latest.league_name,
            team_id=team_id,
            team_name=latest.team_name,
            seasons=tuple(sorted({league.season for league in observations})),
        )
    return profiles


def _discover_leagues(args: argparse.Namespace) -> int:
    credentials = load_espn_credentials(dotenv_path=args.dotenv)
    leagues = ESPNLeagueDiscoveryClient(credentials).discover_football_leagues()
    if args.season is not None:
        leagues = [league for league in leagues if league.season == args.season]
    if not leagues:
        qualifier = f" for {args.season}" if args.season is not None else ""
        raise ConfigurationError(f"No ESPN fantasy football leagues were discovered{qualifier}.")

    print(f"Discovered {len(leagues)} ESPN fantasy football league membership(s):")
    for league in leagues:
        details = []
        if league.league_size is not None:
            details.append(f"{league.league_size} teams")
        if league.draft_type:
            details.append(f"draft={league.draft_type}")
        suffix = f"; {', '.join(details)}" if details else ""
        print(
            f"- {league.league_name} ({league.season}): league_id={league.league_id}; "
            f"team={league.team_name}; team_id={league.team_id}{suffix}"
        )

    if args.write_config:
        profiles = _profiles_from_discovered(leagues)
        write_league_profiles(args.config, profiles, overwrite=args.force)
        print(f"Wrote {len(profiles)} profile(s) to {args.config}.")
    return 0


def _sync_league(args: argparse.Namespace) -> int:
    profile = _load_profile(args)
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


def _load_profile(args: argparse.Namespace) -> LeagueProfile:
    profiles = load_league_profiles(args.config)
    if args.league not in profiles:
        available = ", ".join(sorted(profiles))
        raise ConfigurationError(f"Unknown league profile {args.league!r}. Available: {available}")
    return profiles[args.league]


def _sync_draft(args: argparse.Namespace) -> int:
    profile = _load_profile(args)
    credentials = load_espn_credentials(dotenv_path=args.dotenv)
    fetched_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    raw = ESPNClient(credentials).fetch_draft(
        season=args.season,
        league_id=profile.league_id,
    )
    normalized = normalize_draft_snapshot(raw, season=args.season, fetched_at=fetched_at)
    paths = SnapshotStore(args.data_dir).save(
        source="espn-draft",
        league_id=profile.league_id,
        season=args.season,
        fetched_at=fetched_at,
        raw=raw,
        normalized=normalized,
    )
    draft = normalized["draft"]
    state = (
        "complete"
        if draft["drafted"]
        else "in progress"
        if draft["in_progress"]
        else "not started"
    )
    print(
        f"Saved {draft['pick_count']} selections across {draft['slot_count']} draft slots; "
        f"draft is {state}."
    )
    print(f"Raw: {paths.raw}")
    print(f"Normalized: {paths.normalized}")
    return 0


def _sync_player_evidence(args: argparse.Namespace) -> int:
    profile = _load_profile(args)
    credentials = load_espn_credentials(dotenv_path=args.dotenv)
    fetched_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    raw = ESPNClient(credentials).fetch_player_pool(
        season=args.season,
        league_id=profile.league_id,
        limit=args.limit,
    )
    normalized = normalize_player_evidence(
        raw,
        season=args.season,
        fetched_at=fetched_at,
        league_id=profile.league_id,
    )
    paths = SnapshotStore(args.data_dir).save(
        source="espn-player-evidence",
        league_id=profile.league_id,
        season=args.season,
        fetched_at=fetched_at,
        raw=raw,
        normalized=normalized,
    )
    print(f"Saved evidence for {normalized['player_count']} players.")
    print(f"Raw: {paths.raw}")
    print(f"Normalized: {paths.normalized}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "doctor":
            return _doctor(args)
        if args.command == "discover-leagues":
            return _discover_leagues(args)
        if args.command == "sync-league":
            return _sync_league(args)
        if args.command == "sync-draft":
            return _sync_draft(args)
        if args.command == "sync-player-evidence":
            return _sync_player_evidence(args)
    except (ConfigurationError, ESPNAPIError, OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
