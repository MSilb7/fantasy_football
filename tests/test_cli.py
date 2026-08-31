from pathlib import Path
import tempfile
import unittest

from fantasy_assistant.cli import _profiles_from_discovered, _sync_history_seasons
from fantasy_assistant.config import LeagueIdentity, LeagueProfile
from fantasy_assistant.espn import ESPNAPIError
from fantasy_assistant.espn.discovery import DiscoveredLeague
from fantasy_assistant.ingestion import SnapshotStore


class _HistoryClient:
    def __init__(self) -> None:
        self.calls: list[tuple[int, str]] = []

    def fetch_league(self, *, season, league_id, matchup_periods):
        self.calls.append((season, league_id))
        if season == 2016:
            raise ESPNAPIError(
                "ESPN returned HTTP 404 for a redacted league.", status_code=404
            )
        return {
            "id": int(league_id),
            "seasonId": season,
            "settings": {},
            "status": {},
            "draftDetail": {},
            "members": [],
            "teams": [],
            "schedule": [],
        }


class CLITests(unittest.TestCase):
    def test_discovered_leagues_become_unique_profiles_with_merged_seasons(self) -> None:
        leagues = [
            DiscoveredLeague(
                league_id="123",
                league_name="The League!",
                team_id="7",
                team_name="My Team",
                season=2026,
            ),
            DiscoveredLeague(
                league_id="123",
                league_name="The League!",
                team_id="7",
                team_name="My Team",
                season=2025,
            ),
            DiscoveredLeague(
                league_id="456",
                league_name="The League!",
                team_id="8",
                team_name="Other Team",
                season=2026,
            ),
        ]

        profiles = _profiles_from_discovered(leagues)

        self.assertEqual(set(profiles), {"the_league", "the_league_456"})
        self.assertEqual(profiles["the_league"].seasons, (2025, 2026))
        self.assertEqual(profiles["the_league_456"].team_id, "8")

    def test_historical_sync_uses_season_identity_and_continues_after_404(self) -> None:
        profile = LeagueProfile(
            name="example",
            league_id="9000",
            team_id="9",
            seasons=(2016, 2017, 2018),
            season_identities={
                2016: LeagueIdentity(league_id="7000", team_id="7"),
                2017: LeagueIdentity(league_id="8000", team_id="8"),
            },
        )
        client = _HistoryClient()
        with tempfile.TemporaryDirectory() as directory:
            results = _sync_history_seasons(
                profile=profile,
                seasons=profile.seasons,
                client=client,
                store=SnapshotStore(Path(directory)),
                fetched_at_for_season=lambda season: f"{season}-01-01T00:00:00+00:00",
            )
            saved_files = sorted(Path(directory).glob("normalized/espn/*/*/*.json"))

        self.assertEqual(
            client.calls,
            [(2016, "7000"), (2017, "8000"), (2018, "9000")],
        )
        self.assertEqual(
            [(result.season, result.status) for result in results],
            [(2016, "inaccessible"), (2017, "saved"), (2018, "saved")],
        )
        self.assertEqual(len(saved_files), 2)

    def test_historical_sync_does_not_hide_non_404_failures(self) -> None:
        class AuthenticationFailureClient:
            def fetch_league(self, **_kwargs):
                raise ESPNAPIError("ESPN returned HTTP 401.", status_code=401)

        profile = LeagueProfile(name="example", league_id="9000", seasons=(2018,))
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ESPNAPIError, "401"):
                _sync_history_seasons(
                    profile=profile,
                    seasons=profile.seasons,
                    client=AuthenticationFailureClient(),
                    store=SnapshotStore(Path(directory)),
                )


if __name__ == "__main__":
    unittest.main()
