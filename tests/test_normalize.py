import json
from pathlib import Path
import unittest

from fantasy_assistant.ingestion.normalize import (
    normalize_draft_snapshot,
    normalize_league_snapshot,
    normalize_player_evidence,
)


class NormalizeTests(unittest.TestCase):
    def test_normalizes_league_team_roster_and_matchup(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "league_minimal.json"
        payload = json.loads(fixture.read_text(encoding="utf-8"))

        result = normalize_league_snapshot(
            payload,
            season=2026,
            fetched_at="2026-08-27T12:00:00+00:00",
        )

        self.assertEqual(result["schema_version"], 3)
        self.assertEqual(result["league"]["team_count"], 2)
        self.assertEqual(result["league"]["name"], "Example League")
        self.assertEqual(result["draft"]["type"], "SNAKE")
        self.assertEqual(result["draft"]["pick_order"], [1, 2])
        self.assertEqual(result["draft"]["order_type"], "DRAFT_START")
        self.assertEqual(result["draft"]["order_status"], "unset")
        self.assertFalse(result["draft"]["drafted"])
        self.assertEqual(result["teams"][0]["owner_names"], ["Alex Manager"])
        self.assertEqual(result["teams"][0]["roster"][0]["player_id"], 9001)
        self.assertEqual(result["matchups"][0]["home"]["total_points"], 101.5)
        self.assertEqual(result["settings"]["matchup_period_count"], 14)

    def test_manual_pre_draft_order_is_provisional_and_started_order_is_confirmed(self) -> None:
        payload = {
            "draftDetail": {"drafted": False, "inProgress": False},
            "settings": {
                "draftSettings": {"orderType": "MANUAL", "pickOrder": [2, 1]}
            },
        }

        result = normalize_league_snapshot(
            payload,
            season=2026,
            fetched_at="2026-08-27T12:00:00+00:00",
        )
        self.assertEqual(result["draft"]["order_status"], "provisional")

        payload["draftDetail"]["inProgress"] = True
        result = normalize_league_snapshot(
            payload,
            season=2026,
            fetched_at="2026-08-27T12:01:00+00:00",
        )
        self.assertEqual(result["draft"]["order_status"], "confirmed")

    def test_normalizes_pick_level_draft_history(self) -> None:
        payload = {
            "id": 123,
            "settings": {
                "name": "Example League",
                "draftSettings": {
                    "type": "SNAKE",
                    "orderType": "MANUAL",
                    "pickOrder": [2, 1],
                },
            },
            "draftDetail": {
                "drafted": True,
                "inProgress": False,
                "completeDate": 1756684800000,
                "picks": [
                    {
                        "id": 12,
                        "overallPickNumber": 2,
                        "roundId": 1,
                        "roundPickNumber": 2,
                        "teamId": 1,
                        "memberId": "owner-1",
                        "playerId": 9002,
                        "keeper": False,
                    },
                    {
                        "id": 11,
                        "overallPickNumber": 1,
                        "roundId": 1,
                        "roundPickNumber": 1,
                        "teamId": 2,
                        "memberId": "owner-2",
                        "playerId": 9001,
                        "keeper": False,
                    },
                ],
            },
        }

        result = normalize_draft_snapshot(
            payload,
            season=2025,
            fetched_at="2026-08-27T12:00:00+00:00",
        )

        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["draft"]["pick_count"], 2)
        self.assertEqual(result["draft"]["slot_count"], 2)
        self.assertEqual(result["draft"]["order_status"], "confirmed")
        self.assertEqual(result["draft"]["picks"][0]["player_id"], 9001)
        self.assertEqual(result["draft"]["picks"][1]["overall_pick_number"], 2)

    def test_pre_draft_placeholders_are_slots_not_selections(self) -> None:
        payload = {
            "settings": {
                "draftSettings": {
                    "orderType": "DRAFT_START",
                    "pickOrder": [1, 2],
                }
            },
            "draftDetail": {
                "drafted": False,
                "inProgress": False,
                "picks": [
                    {"id": 1, "overallPickNumber": 1, "teamId": 1, "playerId": -1},
                    {"id": 2, "overallPickNumber": 2, "teamId": 2, "playerId": -1},
                ],
            },
        }

        result = normalize_draft_snapshot(
            payload,
            season=2026,
            fetched_at="2026-08-27T12:00:00+00:00",
        )

        self.assertEqual(result["draft"]["order_status"], "unset")
        self.assertEqual(result["draft"]["slot_count"], 2)
        self.assertEqual(result["draft"]["pick_count"], 0)
        self.assertIsNone(result["draft"]["slots"][0]["player_id"])

    def test_normalizes_player_adp_ranks_projections_and_historical_actuals(self) -> None:
        payload = {
            "players": [
                {
                    "status": "FREEAGENT",
                    "onTeamId": 0,
                    "player": {
                        "id": 9001,
                        "fullName": "Example Receiver",
                        "defaultPositionId": 3,
                        "eligibleSlots": [4, 5, 23],
                        "proTeamId": 10,
                        "injured": False,
                        "injuryStatus": "ACTIVE",
                        "ownership": {
                            "averageDraftPosition": 18.4,
                            "auctionValueAverage": 23.1,
                            "percentOwned": 99.5,
                        },
                        "draftRanksByRankType": {
                            "PPR": {
                                "rank": 17,
                                "auctionValue": 25,
                                "rankSourceId": 1,
                            }
                        },
                        "stats": [
                            {
                                "seasonId": 2026,
                                "scoringPeriodId": 0,
                                "statSourceId": 1,
                                "statSplitTypeId": 0,
                                "appliedTotal": 240.5,
                                "stats": {"53": 85.0},
                            },
                            {
                                "seasonId": 2025,
                                "scoringPeriodId": 0,
                                "statSourceId": 0,
                                "statSplitTypeId": 0,
                                "appliedTotal": 221.2,
                                "stats": {"53": 77.0},
                            },
                        ],
                    },
                }
            ]
        }

        result = normalize_player_evidence(
            payload,
            season=2026,
            fetched_at="2026-08-27T12:00:00+00:00",
            league_id="123",
        )

        player = result["players"][0]
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(player["market"]["average_draft_position"], 18.4)
        self.assertEqual(player["draft_ranks"][0]["rank_type"], "PPR")
        self.assertEqual(player["statistics"][0]["source_kind"], "projection")
        self.assertEqual(player["statistics"][1]["source_kind"], "actual")


if __name__ == "__main__":
    unittest.main()
