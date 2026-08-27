"""Normalize the stable subset of an ESPN league response used across features."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


SCHEMA_VERSION = 2


def _owner_name(member: Mapping[str, Any]) -> str:
    full_name = " ".join(
        part for part in (member.get("firstName", ""), member.get("lastName", "")) if part
    ).strip()
    return full_name or str(member.get("displayName") or member.get("id") or "Unknown owner")


def _normalize_roster(team: Mapping[str, Any]) -> list[dict[str, Any]]:
    entries = team.get("roster", {}).get("entries", [])
    normalized: list[dict[str, Any]] = []
    for entry in entries:
        player = entry.get("playerPoolEntry", {}).get("player", {})
        player_id = player.get("id")
        if player_id is None:
            continue
        normalized.append(
            {
                "player_id": player_id,
                "full_name": player.get("fullName"),
                "default_position_id": player.get("defaultPositionId"),
                "pro_team_id": player.get("proTeamId"),
                "eligible_slot_ids": player.get("eligibleSlots", []),
                "lineup_slot_id": entry.get("lineupSlotId"),
                "injury_status": player.get("injuryStatus"),
                "acquisition_type": entry.get("acquisitionType"),
                "acquisition_date": entry.get("acquisitionDate"),
            }
        )
    return normalized


def normalize_league_snapshot(
    payload: Mapping[str, Any],
    *,
    season: int,
    fetched_at: str,
) -> dict[str, Any]:
    """Create a source-neutral league snapshot while retaining ESPN identifiers."""

    members = {
        str(member.get("id")): {
            "owner_id": member.get("id"),
            "display_name": _owner_name(member),
        }
        for member in payload.get("members", [])
        if member.get("id") is not None
    }

    teams: list[dict[str, Any]] = []
    for team in payload.get("teams", []):
        owner_ids = [str(owner_id) for owner_id in team.get("owners", [])]
        record = team.get("record", {}).get("overall", {})
        teams.append(
            {
                "team_id": team.get("id"),
                "name": team.get("name"),
                "abbreviation": team.get("abbrev"),
                "owner_ids": owner_ids,
                "owner_names": [
                    members[owner_id]["display_name"]
                    for owner_id in owner_ids
                    if owner_id in members
                ],
                "wins": record.get("wins"),
                "losses": record.get("losses"),
                "ties": record.get("ties"),
                "points_for": record.get("pointsFor"),
                "points_against": record.get("pointsAgainst"),
                "playoff_seed": team.get("playoffSeed"),
                "final_rank": team.get("rankCalculatedFinal") or team.get("rankFinal"),
                "roster": _normalize_roster(team),
            }
        )

    matchups: list[dict[str, Any]] = []
    for matchup in payload.get("schedule", []):
        normalized_matchup: dict[str, Any] = {
            "matchup_period_id": matchup.get("matchupPeriodId"),
            "winner": matchup.get("winner"),
        }
        for side in ("home", "away"):
            side_data = matchup.get(side)
            normalized_matchup[side] = (
                {
                    "team_id": side_data.get("teamId"),
                    "total_points": side_data.get("totalPoints"),
                }
                if side_data
                else None
            )
        matchups.append(normalized_matchup)

    settings = payload.get("settings", {})
    schedule_settings = settings.get("scheduleSettings", {})
    roster_settings = settings.get("rosterSettings", {})
    scoring_settings = settings.get("scoringSettings", {})
    draft_settings = settings.get("draftSettings", {})
    draft_detail = payload.get("draftDetail", {})

    return {
        "schema_version": SCHEMA_VERSION,
        "source": "espn",
        "fetched_at": fetched_at,
        "season": season,
        "league": {
            "league_id": payload.get("id"),
            "name": payload.get("name") or settings.get("name"),
            "team_count": len(teams),
            "status": payload.get("status", {}),
        },
        "draft": {
            "drafted": draft_detail.get("drafted"),
            "in_progress": draft_detail.get("inProgress"),
            "date": draft_settings.get("date"),
            "available_date": draft_settings.get("availableDate"),
            "type": draft_settings.get("type"),
            "auction_budget": draft_settings.get("auctionBudget"),
            "keeper_count": draft_settings.get("keeperCount"),
            "keeper_count_future": draft_settings.get("keeperCountFuture"),
            "keeper_order_type": draft_settings.get("keeperOrderType"),
            "pick_order": draft_settings.get("pickOrder", []),
            "time_per_selection": draft_settings.get("timePerSelection"),
            "trading_enabled": draft_settings.get("isTradingEnabled"),
        },
        "settings": {
            "matchup_period_count": schedule_settings.get("matchupPeriodCount"),
            "playoff_team_count": schedule_settings.get("playoffTeamCount"),
            "lineup_slot_counts": roster_settings.get("lineupSlotCounts", {}),
            "scoring_type": scoring_settings.get("scoringType"),
            "scoring_items": scoring_settings.get("scoringItems", []),
        },
        "members": list(members.values()),
        "teams": teams,
        "matchups": matchups,
    }
