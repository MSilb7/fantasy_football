import unittest

from fantasy_assistant.cli import _profiles_from_discovered
from fantasy_assistant.espn.discovery import DiscoveredLeague


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


if __name__ == "__main__":
    unittest.main()
