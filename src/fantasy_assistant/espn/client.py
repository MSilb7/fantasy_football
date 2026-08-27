"""Small, dependency-free client for the ESPN league endpoint."""

from __future__ import annotations

import json
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
        headers = {
            "Accept": "application/json",
            "Cookie": f"espn_s2={self._credentials.espn_s2}; SWID={self._credentials.swid}",
            "User-Agent": "fantasy-football-assistant/0.1",
        }
        if matchup_periods is not None:
            headers["X-Fantasy-Filter"] = json.dumps(
                {
                    "schedule": {
                        "filterMatchupPeriodIds": {"value": list(matchup_periods)}
                    }
                },
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
