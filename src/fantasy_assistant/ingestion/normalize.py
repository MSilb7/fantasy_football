"""Normalize the stable subset of an ESPN league response used across features."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


LEAGUE_SCHEMA_VERSION = 3
DRAFT_SCHEMA_VERSION = 1
PLAYER_EVIDENCE_SCHEMA_VERSION = 1


def _draft_order_status(
    draft_detail: Mapping[str, Any], draft_settings: Mapping[str, Any]
) -> str:
    if draft_detail.get("drafted") or draft_detail.get("inProgress"):
        return "confirmed"
    order_type = draft_settings.get("orderType")
    if order_type == "DRAFT_START":
        return "unset"
    if order_type == "MANUAL" and draft_settings.get("pickOrder"):
        return "provisional"
    return "unknown"


def _stat_source_kind(source_id: Any) -> str:
    if source_id == 0:
        return "actual"
    if source_id == 1:
        return "projection"
    return "unknown"


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

    order_type = draft_settings.get("orderType")
    order_status = _draft_order_status(draft_detail, draft_settings)

    return {
        "schema_version": LEAGUE_SCHEMA_VERSION,
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
            "order_type": order_type,
            "order_status": order_status,
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


def normalize_draft_snapshot(
    payload: Mapping[str, Any],
    *,
    season: int,
    fetched_at: str,
) -> dict[str, Any]:
    """Normalize live or completed pick-level draft evidence."""

    draft_detail = payload.get("draftDetail", {})
    if not isinstance(draft_detail, Mapping):
        draft_detail = {}
    slots = []
    for pick in draft_detail.get("picks", []) or []:
        if not isinstance(pick, Mapping):
            continue
        player_id = pick.get("playerId")
        slots.append(
            {
                "pick_id": pick.get("id"),
                "overall_pick_number": pick.get("overallPickNumber"),
                "round_id": pick.get("roundId"),
                "round_pick_number": pick.get("roundPickNumber"),
                "team_id": pick.get("teamId"),
                "member_id": pick.get("memberId"),
                "player_id": player_id if player_id not in (None, -1) else None,
                "lineup_slot_id": pick.get("lineupSlotId"),
                "keeper": pick.get("keeper"),
                "reserved_for_keeper": pick.get("reservedForKeeper"),
                "bid_amount": pick.get("bidAmount"),
                "auto_draft_type_id": pick.get("autoDraftTypeId"),
            }
        )
    slots.sort(
        key=lambda pick: (
            pick["overall_pick_number"] is None,
            pick["overall_pick_number"] or 0,
        )
    )
    picks = [slot for slot in slots if slot["player_id"] is not None]
    settings = payload.get("settings", {})
    if not isinstance(settings, Mapping):
        settings = {}
    draft_settings = settings.get("draftSettings", {})
    if not isinstance(draft_settings, Mapping):
        draft_settings = {}
    return {
        "schema_version": DRAFT_SCHEMA_VERSION,
        "source": "espn",
        "fetched_at": fetched_at,
        "season": season,
        "league": {
            "league_id": payload.get("id"),
            "name": payload.get("name") or settings.get("name"),
        },
        "draft": {
            "drafted": draft_detail.get("drafted"),
            "in_progress": draft_detail.get("inProgress"),
            "complete_date": draft_detail.get("completeDate"),
            "type": draft_settings.get("type"),
            "order_type": draft_settings.get("orderType"),
            "order_status": _draft_order_status(draft_detail, draft_settings),
            "pick_order": draft_settings.get("pickOrder", []),
            "slot_count": len(slots),
            "pick_count": len(picks),
            "slots": slots,
            "picks": picks,
        },
    }


def normalize_player_evidence(
    payload: Mapping[str, Any],
    *,
    season: int,
    fetched_at: str,
    league_id: str,
) -> dict[str, Any]:
    """Normalize ESPN availability, ADP, ranks, projections, and historical stats."""

    players: list[dict[str, Any]] = []
    for entry in payload.get("players", []) or []:
        if not isinstance(entry, Mapping):
            continue
        player = entry.get("player", {})
        if not isinstance(player, Mapping):
            continue
        player_id = player.get("id")
        if player_id is None:
            continue
        ownership = player.get("ownership", {})
        if not isinstance(ownership, Mapping):
            ownership = {}
        ranks_by_type = player.get("draftRanksByRankType", {})
        if not isinstance(ranks_by_type, Mapping):
            ranks_by_type = {}
        ranks = []
        for rank_type, rank in sorted(ranks_by_type.items()):
            if not isinstance(rank, Mapping):
                continue
            ranks.append(
                {
                    "rank_type": rank_type,
                    "rank": rank.get("rank"),
                    "auction_value": rank.get("auctionValue"),
                    "published": rank.get("published"),
                    "rank_source_id": rank.get("rankSourceId"),
                    "slot_id": rank.get("slotId"),
                }
            )
        statistics = []
        for stat in player.get("stats", []) or []:
            if not isinstance(stat, Mapping):
                continue
            source_id = stat.get("statSourceId")
            statistics.append(
                {
                    "season": stat.get("seasonId"),
                    "scoring_period_id": stat.get("scoringPeriodId"),
                    "source_id": source_id,
                    "source_kind": _stat_source_kind(source_id),
                    "split_type_id": stat.get("statSplitTypeId"),
                    "pro_team_id": stat.get("proTeamId"),
                    "applied_total": stat.get("appliedTotal"),
                    "values_by_stat_id": stat.get("stats", {}),
                }
            )
        players.append(
            {
                "player_id": player_id,
                "full_name": player.get("fullName"),
                "first_name": player.get("firstName"),
                "last_name": player.get("lastName"),
                "active": player.get("active"),
                "default_position_id": player.get("defaultPositionId"),
                "eligible_slot_ids": player.get("eligibleSlots", []),
                "pro_team_id": player.get("proTeamId"),
                "injured": player.get("injured"),
                "injury_status": player.get("injuryStatus"),
                "availability": {
                    "status": entry.get("status"),
                    "on_team_id": entry.get("onTeamId"),
                    "lineup_locked": entry.get("lineupLocked"),
                    "roster_locked": entry.get("rosterLocked"),
                },
                "market": {
                    "average_draft_position": ownership.get("averageDraftPosition"),
                    "auction_value_average": ownership.get("auctionValueAverage"),
                    "percent_owned": ownership.get("percentOwned"),
                    "percent_started": ownership.get("percentStarted"),
                    "observed_at": ownership.get("date"),
                },
                "draft_ranks": ranks,
                "statistics": statistics,
            }
        )
    players.sort(key=lambda player: player["player_id"])
    return {
        "schema_version": PLAYER_EVIDENCE_SCHEMA_VERSION,
        "source": "espn",
        "fetched_at": fetched_at,
        "season": season,
        "league_id": league_id,
        "player_count": len(players),
        "players": players,
    }
