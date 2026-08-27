"""Small, dependency-free client for the ESPN league endpoint."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fantasy_assistant.config import ESPNCredentials


DEFAULT_LEAGUE_VIEWS = (
    "mTeam",
    "mRoster",
    "mSettings",
    "mMatchup",
    "mMatchupScore",
    "mStandings",
)


class ESPNAPIError(RuntimeError):
    """A sanitized ESPN request or response failure."""


class ESPNClient:
    """Fetch ESPN league snapshots while keeping HTTP details in one place."""

    BASE_URL = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl"

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

    def _request_json(
        self,
        *,
        url: str,
        league_id: str,
        fantasy_filter: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        headers = {
            "Accept": "application/json",
            "Cookie": f"espn_s2={self._credentials.espn_s2}; SWID={self._credentials.swid}",
            "User-Agent": "fantasy-football-assistant/0.1",
        }
        if fantasy_filter is not None:
            headers["X-Fantasy-Filter"] = json.dumps(
                fantasy_filter,
                separators=(",", ":"),
            )

        request = Request(url, headers=headers, method="GET")
        try:
            with self._opener(request, timeout=self._timeout_seconds) as response:
                body = response.read()
        except HTTPError as error:
            raise ESPNAPIError(f"ESPN returned HTTP {error.code} for league {league_id}.") from error
        except URLError as error:
            raise ESPNAPIError(f"Could not reach ESPN for league {league_id}.") from error

        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ESPNAPIError("ESPN returned a response that was not valid JSON.") from error
        if not isinstance(payload, dict):
            raise ESPNAPIError("ESPN returned an unexpected top-level response shape.")
        return payload

    def fetch_league(
        self,
        *,
        season: int,
        league_id: str,
        views: Iterable[str] = DEFAULT_LEAGUE_VIEWS,
        matchup_periods: Iterable[int] | None = None,
    ) -> dict[str, Any]:
        """Fetch a league payload using composable ESPN views."""

        query = urlencode([("view", view) for view in views])
        url = f"{self.BASE_URL}/seasons/{season}/segments/0/leagues/{league_id}?{query}"
        fantasy_filter = None
        if matchup_periods is not None:
            fantasy_filter = {
                "schedule": {
                    "filterMatchupPeriodIds": {"value": list(matchup_periods)}
                }
            }
        return self._request_json(
            url=url,
            league_id=league_id,
            fantasy_filter=fantasy_filter,
        )

    def fetch_draft(self, *, season: int, league_id: str) -> dict[str, Any]:
        """Fetch settings, teams, and pick-level draft state for one league season."""

        return self.fetch_league(
            season=season,
            league_id=league_id,
            views=("mSettings", "mTeam", "mDraftDetail"),
        )

    def fetch_player_pool(
        self,
        *,
        season: int,
        league_id: str,
        limit: int = 5000,
    ) -> dict[str, Any]:
        """Fetch league-relative player availability and ESPN evidence."""

        if limit < 1:
            raise ValueError("Player limit must be positive.")
        query = urlencode([("view", "kona_player_info")])
        url = f"{self.BASE_URL}/seasons/{season}/segments/0/leagues/{league_id}?{query}"
        fantasy_filter = {
            "players": {
                "filterStatus": {"value": ["FREEAGENT", "WAIVERS", "ONTEAM"]},
                "limit": limit,
                "sortPercOwned": {"sortAsc": False, "sortPriority": 1},
            }
        }
        return self._request_json(
            url=url,
            league_id=league_id,
            fantasy_filter=fantasy_filter,
        )
