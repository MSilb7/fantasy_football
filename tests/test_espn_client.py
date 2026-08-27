import json
import unittest

from fantasy_assistant.config import ESPNCredentials
from fantasy_assistant.espn.client import ESPNClient


class _Response:
    def __init__(self, payload: dict) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


class ESPNClientTests(unittest.TestCase):
    def test_builds_one_multi_view_request_with_matchup_filter(self) -> None:
        observed: dict[str, object] = {}

        def opener(request: object, *, timeout: float) -> _Response:
            observed["request"] = request
            observed["timeout"] = timeout
            return _Response({"id": 12345})

        client = ESPNClient(
            ESPNCredentials(espn_s2="private-cookie", swid="{private-id}"),
            timeout_seconds=12.5,
            opener=opener,
        )
        result = client.fetch_league(
            season=2026,
            league_id="12345",
            views=("mTeam", "mRoster"),
            matchup_periods=(1, 2),
        )

        request = observed["request"]
        self.assertEqual(result["id"], 12345)
        self.assertEqual(observed["timeout"], 12.5)
        self.assertIn("view=mTeam&view=mRoster", request.full_url)
        self.assertEqual(
            json.loads(request.get_header("X-fantasy-filter")),
            {"schedule": {"filterMatchupPeriodIds": {"value": [1, 2]}}},
        )
        self.assertIn("espn_s2=private-cookie", request.get_header("Cookie"))


if __name__ == "__main__":
    unittest.main()
