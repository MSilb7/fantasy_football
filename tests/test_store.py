import json
from pathlib import Path
import tempfile
import unittest

from fantasy_assistant.ingestion.store import SnapshotStore


class SnapshotStoreTests(unittest.TestCase):
    def test_writes_raw_and_normalized_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = SnapshotStore(Path(directory)).save(
                source="espn",
                league_id="12345",
                season=2026,
                fetched_at="2026-08-27T12:00:00+00:00",
                raw={"id": 12345},
                normalized={"schema_version": 1},
            )

            self.assertEqual(json.loads(paths.raw.read_text())["id"], 12345)
            self.assertEqual(json.loads(paths.normalized.read_text())["schema_version"], 1)
            self.assertIn("2026-08-27T12-00-00_00-00.json", paths.raw.name)

    def test_rejects_unsafe_path_components(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                SnapshotStore(Path(directory)).save(
                    source="../espn",
                    league_id="12345",
                    season=2026,
                    fetched_at="2026-08-27T12:00:00+00:00",
                    raw={},
                    normalized={},
                )


if __name__ == "__main__":
    unittest.main()
