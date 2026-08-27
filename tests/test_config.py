from pathlib import Path
import tempfile
import unittest

from fantasy_assistant.config import (
    ConfigurationError,
    load_espn_credentials,
    load_league_profiles,
)


class ConfigTests(unittest.TestCase):
    def test_loads_multiple_league_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "leagues.toml"
            path.write_text(
                '[leagues.home]\nleague_id = "123"\nteam_name = "My Team"\nseasons = [2025, 2026]\n',
                encoding="utf-8",
            )
            profiles = load_league_profiles(path)

        self.assertEqual(profiles["home"].league_id, "123")
        self.assertEqual(profiles["home"].seasons, (2025, 2026))

    def test_environment_credentials_override_dotenv(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("espn_s2=file-secret\nswid={file-id}\n", encoding="utf-8")
            credentials = load_espn_credentials(
                environ={"ESPN_S2": "env-secret", "ESPN_SWID": "{env-id}"},
                dotenv_path=path,
            )

        self.assertEqual(credentials.espn_s2, "env-secret")
        self.assertEqual(credentials.swid, "{env-id}")
        self.assertNotIn("env-secret", repr(credentials))

    def test_missing_credentials_names_only_missing_fields(self) -> None:
        with self.assertRaisesRegex(ConfigurationError, "ESPN_SWID"):
            load_espn_credentials(environ={"ESPN_S2": "secret"}, dotenv_path=Path("missing"))


if __name__ == "__main__":
    unittest.main()
