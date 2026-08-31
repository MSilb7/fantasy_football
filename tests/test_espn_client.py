import json
import unittest
from urllib.error import HTTPError

from fantasy_assistant.config import ESPNCredentials
from fantasy_assistant.espn.client import ESPNAPIError, ESPNClient


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

    def test_builds_player_evidence_request_with_league_relative_filter(self) -> None:
        observed: dict[str, object] = {}

        def opener(request: object, *, timeout: float) -> _Response:
            observed["request"] = request
            return _Response({"players": []})

        client = ESPNClient(
            ESPNCredentials(espn_s2="private-cookie", swid="{private-id}"),
            opener=opener,
        )
        result = client.fetch_player_pool(season=2026, league_id="12345", limit=2500)

        request = observed["request"]
        fantasy_filter = json.loads(request.get_header("X-fantasy-filter"))
        self.assertEqual(result, {"players": []})
        self.assertIn("view=kona_player_info", request.full_url)
        self.assertEqual(fantasy_filter["players"]["limit"], 2500)
        self.assertEqual(
            fantasy_filter["players"]["filterStatus"]["value"],
            ["FREEAGENT", "WAIVERS", "ONTEAM"],
        )

    def test_draft_request_uses_pick_level_view(self) -> None:
        observed: dict[str, object] = {}

        def opener(request: object, *, timeout: float) -> _Response:
            observed["request"] = request
            return _Response({"draftDetail": {"picks": []}})

        client = ESPNClient(
            ESPNCredentials(espn_s2="private-cookie", swid="{private-id}"),
            opener=opener,
        )
        client.fetch_draft(season=2025, league_id="12345")

        self.assertIn("view=mDraftDetail", observed["request"].full_url)

    def test_http_errors_preserve_status_without_exposing_credentials(self) -> None:
        def opener(request: object, *, timeout: float) -> _Response:
            raise HTTPError(request.full_url, 404, "Not Found", {}, None)

        client = ESPNClient(
            ESPNCredentials(espn_s2="private-cookie", swid="{private-id}"),
            opener=opener,
        )

        with self.assertRaises(ESPNAPIError) as raised:
            client.fetch_league(season=2016, league_id="12345")

        self.assertEqual(raised.exception.status_code, 404)
        self.assertNotIn("private-cookie", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
