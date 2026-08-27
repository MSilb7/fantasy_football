import json
from pathlib import Path
import unittest

from fantasy_assistant.ingestion.normalize import normalize_league_snapshot


class NormalizeTests(unittest.TestCase):
    def test_normalizes_league_team_roster_and_matchup(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "league_minimal.json"
        payload = json.loads(fixture.read_text(encoding="utf-8"))

        result = normalize_league_snapshot(
            payload,
            season=2026,
            fetched_at="2026-08-27T12:00:00+00:00",
        )

        self.assertEqual(result["schema_version"], 2)
        self.assertEqual(result["league"]["team_count"], 2)
        self.assertEqual(result["league"]["name"], "Example League")
        self.assertEqual(result["draft"]["type"], "SNAKE")
        self.assertEqual(result["draft"]["pick_order"], [1, 2])
        self.assertFalse(result["draft"]["drafted"])
        self.assertEqual(result["teams"][0]["owner_names"], ["Alex Manager"])
        self.assertEqual(result["teams"][0]["roster"][0]["player_id"], 9001)
        self.assertEqual(result["matchups"][0]["home"]["total_points"], 101.5)
        self.assertEqual(result["settings"]["matchup_period_count"], 14)


if __name__ == "__main__":
    unittest.main()
