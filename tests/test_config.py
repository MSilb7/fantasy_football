from pathlib import Path
import tempfile
import unittest

from fantasy_assistant.config import (
    ConfigurationError,
    LeagueIdentity,
    LeagueProfile,
    load_espn_credentials,
    load_league_profiles,
    write_league_profiles,
)


class ConfigTests(unittest.TestCase):
    def test_loads_multiple_league_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "leagues.toml"
            path.write_text(
                '[leagues.home]\nleague_id = "123"\nleague_name = "Home League"\n'
                'team_id = "7"\nteam_name = "My Team"\nseasons = [2025, 2026]\n',
                encoding="utf-8",
            )
            profiles = load_league_profiles(path)

        self.assertEqual(profiles["home"].league_id, "123")
        self.assertEqual(profiles["home"].league_name, "Home League")
        self.assertEqual(profiles["home"].team_id, "7")
        self.assertEqual(profiles["home"].seasons, (2025, 2026))

    def test_writes_and_round_trips_discovered_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config" / "leagues.toml"
            write_league_profiles(
                path,
                {
                    "example_league": LeagueProfile(
                        name="example_league",
                        league_id="123456",
                        league_name="Example League",
                        team_id="14",
                        team_name="Example Team",
                        seasons=(2026,),
                    )
                },
            )
            profiles = load_league_profiles(path)

            self.assertEqual(profiles["example_league"].league_id, "123456")
            self.assertEqual(profiles["example_league"].team_name, "Example Team")

            with self.assertRaisesRegex(ConfigurationError, "already exists"):
                write_league_profiles(path, profiles)

    def test_loads_and_resolves_season_specific_identities(self) -> None:
        fixture = (
            Path(__file__).parent
            / "fixtures"
            / "league_profiles_season_identities.toml"
        )

        profile = load_league_profiles(fixture)["example"]

        self.assertEqual(
            profile.identity_for_season(2016),
            LeagueIdentity(league_id="7000", team_id="7"),
        )
        self.assertEqual(
            profile.identity_for_season(2017),
            LeagueIdentity(league_id="8000", team_id="8"),
        )
        self.assertEqual(
            profile.identity_for_season(2018),
            LeagueIdentity(league_id="9000", team_id="9"),
        )

    def test_writes_season_specific_identities(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "leagues.toml"
            write_league_profiles(
                path,
                {
                    "example": LeagueProfile(
                        name="example",
                        league_id="9000",
                        team_id="9",
                        seasons=(2016, 2017, 2018),
                        season_identities={
                            2016: LeagueIdentity(league_id="7000", team_id="7"),
                            2017: LeagueIdentity(league_id="8000", team_id="8"),
                        },
                    )
                },
            )

            profile = load_league_profiles(path)["example"]

        self.assertEqual(profile.identity_for_season(2016).league_id, "7000")
        self.assertEqual(profile.identity_for_season(2018).league_id, "9000")

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
