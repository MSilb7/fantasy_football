from pathlib import Path
import json
import tempfile
import unittest

from fantasy_assistant.draft import (
    latest_snapshot_path,
    recommend_draft_picks,
    render_draft_board,
)


def _player(player_id, name, position, rank, projection, *, injury="ACTIVE"):
    return {
        "player_id": player_id,
        "full_name": name,
        "active": True,
        "default_position_id": position,
        "injured": injury != "ACTIVE",
        "injury_status": injury,
        "market": {"average_draft_position": rank},
        "draft_ranks": [
            {"rank_type": "PPR", "rank": rank},
            {"rank_type": "STANDARD", "rank": rank},
        ],
        "statistics": [
            {
                "season": 2026,
                "source_kind": "projection",
                "split_type_id": 0,
                "applied_total": projection,
            }
        ],
    }


class DraftRecommendationTests(unittest.TestCase):
    def test_latest_snapshot_uses_timestamped_filename_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot_dir = root / "normalized" / "espn-draft" / "123" / "2026"
            snapshot_dir.mkdir(parents=True)
            older = snapshot_dir / "2026-01-01T00-00-00_00-00.json"
            latest = snapshot_dir / "2026-02-01T00-00-00_00-00.json"
            older.write_text(json.dumps({}), encoding="utf-8")
            latest.write_text(json.dumps({}), encoding="utf-8")

            result = latest_snapshot_path(
                root, source="espn-draft", league_id="123", season=2026
            )

        self.assertEqual(result, latest)

    def test_rankings_exclude_keepers_and_favor_an_open_rb_need(self) -> None:
        league = {
            "settings": {
                "scoring_items": [{"statId": 53, "points": 0.5}],
            }
        }
        draft = {
            "fetched_at": "2026-08-31T23:00:00+00:00",
            "draft": {
                "picks": [
                    {"team_id": 1, "player_id": 10, "keeper": True},
                    {"team_id": 2, "player_id": 20, "keeper": True},
                ],
                "slots": [
                    {
                        "overall_pick_number": 1,
                        "round_id": 1,
                        "team_id": 1,
                        "player_id": None,
                        "reserved_for_keeper": False,
                    },
                    {
                        "overall_pick_number": 2,
                        "round_id": 1,
                        "team_id": 2,
                        "player_id": None,
                        "reserved_for_keeper": False,
                    },
                    {
                        "overall_pick_number": 3,
                        "round_id": 2,
                        "team_id": 2,
                        "player_id": None,
                        "reserved_for_keeper": False,
                    },
                    {
                        "overall_pick_number": 4,
                        "round_id": 2,
                        "team_id": 1,
                        "player_id": None,
                        "reserved_for_keeper": False,
                    },
                ],
            },
        }
        evidence = {
            "season": 2026,
            "players": [
                _player(10, "My Keeper WR", 3, 25, 230),
                _player(20, "Their Keeper WR", 3, 20, 220),
                _player(30, "Best Running Back", 2, 1, 320),
                _player(31, "Second Running Back", 2, 5, 270),
                _player(40, "Best Receiver", 3, 2, 280),
                _player(41, "Replacement Receiver", 3, 40, 180),
                _player(50, "Best Tight End", 4, 15, 210),
                _player(51, "Replacement Tight End", 4, 80, 120),
                _player(60, "Replacement QB", 1, 50, 250),
            ],
        }

        board = recommend_draft_picks(
            league, draft, evidence, user_team_id=1, limit=9
        )

        self.assertEqual(board.current_overall_pick, 1)
        self.assertEqual(board.next_user_pick, 1)
        self.assertEqual(board.opponent_picks_before_user, 2)
        self.assertEqual(board.recommendations[0].player_name, "Best Running Back")
        self.assertNotIn(
            "My Keeper WR", [item.player_name for item in board.recommendations]
        )
        self.assertGreater(
            board.recommendations[0].need,
            next(item.need for item in board.recommendations if item.position == "QB"),
        )
        rendered = render_draft_board(board)
        self.assertIn("ON THE CLOCK", rendered)
        self.assertIn("| Opp demand | Gone next |", rendered)


if __name__ == "__main__":
    unittest.main()
