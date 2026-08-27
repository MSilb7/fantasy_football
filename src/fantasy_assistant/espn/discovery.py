"""Discover ESPN fantasy football memberships from an authenticated fan profile."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from fantasy_assistant.config import ESPNCredentials
from fantasy_assistant.espn.client import ESPNAPIError


FOOTBALL_GAME_ID = 1


@dataclass(frozen=True)
class DiscoveredLeague:
    """League and team identity exposed by ESPN's authenticated fan profile."""

    league_id: str
    league_name: str
    team_id: str
    team_name: str
    season: int
    league_size: int | None = None
    draft_date: int | None = None
    draft_status: str | None = None
    draft_type: str | None = None
    league_status: str | None = None
    scoring_type: str | None = None


def _integer(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def parse_football_leagues(payload: Mapping[str, Any]) -> list[DiscoveredLeague]:
    """Extract football league memberships from an ESPN fan-profile payload."""

    discovered: dict[tuple[int, str, str], DiscoveredLeague] = {}
    for preference in payload.get("preferences", []):
        if not isinstance(preference, Mapping):
            continue
        preference_type = preference.get("type", {})
        if not isinstance(preference_type, Mapping) or preference_type.get("code") != "fantasy":
            continue
        metadata = preference.get("metaData", {})
        entry = metadata.get("entry", {}) if isinstance(metadata, Mapping) else {}
        if not isinstance(entry, Mapping) or _integer(entry.get("gameId")) != FOOTBALL_GAME_ID:
            continue

        season = _integer(entry.get("seasonId"))
        team_id = entry.get("entryId")
        if season is None or team_id is None:
            continue
        entry_metadata = entry.get("entryMetadata", {})
        if not isinstance(entry_metadata, Mapping):
            entry_metadata = {}
        team_name = str(entry_metadata.get("teamName") or entry.get("name") or "Unknown team")

        for group in entry.get("groups", []):
            if not isinstance(group, Mapping) or group.get("groupId") is None:
                continue
            league_id = str(group["groupId"])
            league = DiscoveredLeague(
                league_id=league_id,
                league_name=str(group.get("groupName") or f"League {league_id}"),
                team_id=str(team_id),
                team_name=team_name,
                season=season,
                league_size=_integer(group.get("groupSize")),
                draft_date=_integer(group.get("draftDate")),
                draft_status=(
                    str(group["draftStatus"]) if group.get("draftStatus") is not None else None
                ),
                draft_type=(
                    str(group.get("draftTypeName") or group.get("draftType"))
                    if group.get("draftTypeName") is not None or group.get("draftType") is not None
                    else None
                ),
                league_status=(
                    str(group["leagueStatus"]) if group.get("leagueStatus") is not None else None
                ),
                scoring_type=(
                    str(entry_metadata["scoringTypeName"])
                    if entry_metadata.get("scoringTypeName") is not None
                    else None
                ),
            )
            discovered[(season, league_id, str(team_id))] = league

    return sorted(
        discovered.values(),
        key=lambda league: (-league.season, league.league_name.casefold(), league.team_name.casefold()),
    )


class ESPNLeagueDiscoveryClient:
    """Read league memberships from ESPN without requiring known league IDs."""

    FAN_PROFILE_URL = "https://fan.api.espn.com/apis/v2/fans/{swid}?displayEvents=true"

    def __init__(
        self,
        credentials: ESPNCredentials,
        *,
        timeout_seconds: float = 30.0,
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        self._credentials = credentials
        self._timeout_seconds = timeout_seconds
        self._opener = opener

    def discover_football_leagues(self) -> list[DiscoveredLeague]:
        url = self.FAN_PROFILE_URL.format(swid=quote(self._credentials.swid, safe=""))
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "Cookie": (
                    f"espn_s2={self._credentials.espn_s2}; SWID={self._credentials.swid}"
                ),
                "User-Agent": "fantasy-football-assistant/0.1",
            },
            method="GET",
        )
        try:
            with self._opener(request, timeout=self._timeout_seconds) as response:
                body = response.read()
        except HTTPError as error:
            raise ESPNAPIError(
                f"ESPN returned HTTP {error.code} while discovering leagues."
            ) from error
        except URLError as error:
            raise ESPNAPIError("Could not reach ESPN while discovering leagues.") from error

        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ESPNAPIError("ESPN returned invalid league-discovery JSON.") from error
        if not isinstance(payload, Mapping):
            raise ESPNAPIError("ESPN returned an unexpected league-discovery response shape.")
        return parse_football_leagues(payload)
