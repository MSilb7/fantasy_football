import json
from pathlib import Path
import unittest

from fantasy_assistant.config import ESPNCredentials
from fantasy_assistant.espn.discovery import (
    ESPNLeagueDiscoveryClient,
    parse_football_leagues,
)


class _Response:
    def __init__(self, payload: dict) -> None:
        self._payload = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._payload


class ESPNDiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        fixture_path = Path(__file__).parent / "fixtures" / "fan_profile_minimal.json"
        self.payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    def test_parses_only_football_league_memberships(self) -> None:
        leagues = parse_football_leagues(self.payload)

        self.assertEqual(len(leagues), 1)
        league = leagues[0]
        self.assertEqual(league.league_id, "123456")
        self.assertEqual(league.league_name, "Example Football League")
        self.assertEqual(league.team_id, "14")
        self.assertEqual(league.team_name, "Example Football Team")
        self.assertEqual(league.season, 2026)
        self.assertEqual(league.league_size, 12)
        self.assertEqual(league.draft_type, "Snake")
        self.assertEqual(league.scoring_type, "Head to Head Points")

    def test_fetches_the_authenticated_fan_profile_without_exposing_cookies(self) -> None:
        observed: dict[str, object] = {}

        def opener(request: object, *, timeout: float) -> _Response:
            observed["request"] = request
            observed["timeout"] = timeout
            return _Response(self.payload)

        client = ESPNLeagueDiscoveryClient(
            ESPNCredentials(espn_s2="private-cookie", swid="{private-id}"),
            timeout_seconds=15,
            opener=opener,
        )
        leagues = client.discover_football_leagues()

        request = observed["request"]
        self.assertEqual(len(leagues), 1)
        self.assertEqual(observed["timeout"], 15)
        self.assertIn("fan.api.espn.com/apis/v2/fans/%7Bprivate-id%7D", request.full_url)
        self.assertIn("espn_s2=private-cookie", request.get_header("Cookie"))


if __name__ == "__main__":
    unittest.main()
