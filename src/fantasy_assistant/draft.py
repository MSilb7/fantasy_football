"""Deterministic, league-aware recommendations for a live ESPN snake draft."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence


POSITION_NAMES = {1: "QB", 2: "RB", 3: "WR", 4: "TE", 5: "K", 16: "D/ST"}
STARTER_REQUIREMENTS = {1: 1, 2: 2, 3: 2, 4: 1}
FLEX_POSITIONS = {2, 3, 4}


@dataclass(frozen=True)
class DraftRecommendation:
    player_id: int
    player_name: str
    position: str
    projected_points: float
    value: int
    need: int
    scarcity: int
    opponent_demand: int
    gone_before_next_pick: int
    health: int
    score: int
    description: str


@dataclass(frozen=True)
class DraftBoard:
    fetched_at: str
    current_overall_pick: int | None
    current_team_id: int | None
    next_user_pick: int | None
    opponent_picks_before_user: int
    user_roster: tuple[str, ...]
    recommendations: tuple[DraftRecommendation, ...]


def latest_snapshot_path(
    data_dir: Path, *, source: str, league_id: str, season: int
) -> Path:
    directory = data_dir / "normalized" / source / str(league_id) / str(season)
    paths = sorted(directory.glob("*.json"))
    if not paths:
        raise ValueError(
            f"No normalized {source} snapshot for league {league_id}, season {season}."
        )
    return paths[-1]


def load_latest_snapshot(
    data_dir: Path, *, source: str, league_id: str, season: int
) -> dict[str, Any]:
    path = latest_snapshot_path(
        data_dir, source=source, league_id=league_id, season=season
    )
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Snapshot must contain a JSON object: {path}")
    return value


def _projection(player: Mapping[str, Any], season: int) -> float | None:
    candidates = [
        stat.get("applied_total")
        for stat in player.get("statistics", [])
        if stat.get("season") == season
        and stat.get("source_kind") == "projection"
        and stat.get("split_type_id") == 0
        and isinstance(stat.get("applied_total"), (int, float))
    ]
    return float(max(candidates)) if candidates else None


def _reception_points(league: Mapping[str, Any]) -> float:
    for item in league.get("settings", {}).get("scoring_items", []):
        if item.get("statId") == 53 and isinstance(item.get("points"), (int, float)):
            return float(item["points"])
    return 1.0


def _rank(player: Mapping[str, Any], reception_points: float) -> float:
    ranks = {
        rank.get("rank_type"): float(rank["rank"])
        for rank in player.get("draft_ranks", [])
        if isinstance(rank.get("rank"), (int, float))
    }
    ppr = ranks.get("PPR")
    standard = ranks.get("STANDARD")
    if ppr is not None and standard is not None:
        ppr_weight = min(1.0, max(0.0, reception_points))
        rank_value = ppr * ppr_weight + standard * (1.0 - ppr_weight)
    else:
        rank_value = ppr or standard or 300.0
    adp = player.get("market", {}).get("average_draft_position")
    if isinstance(adp, (int, float)) and adp > 0:
        return 0.7 * rank_value + 0.3 * float(adp)
    return rank_value


def _health(player: Mapping[str, Any]) -> int:
    status = str(player.get("injury_status") or "UNKNOWN").upper()
    if status in {"ACTIVE", "NORMAL"} and not player.get("injured"):
        return 100
    if status in {"QUESTIONABLE", "PROBABLE"}:
        return 65
    if status in {"DOUBTFUL", "INJURED_RESERVE", "IR"}:
        return 25
    if status in {"OUT", "SUSPENSION"}:
        return 5
    return 75


def _rosters_by_team(
    picks: Sequence[Mapping[str, Any]], players_by_id: Mapping[int, Mapping[str, Any]]
) -> dict[int, Counter[int]]:
    rosters: dict[int, Counter[int]] = {}
    for pick in picks:
        team_id = pick.get("team_id")
        player = players_by_id.get(pick.get("player_id"))
        position = player.get("default_position_id") if player else None
        if isinstance(team_id, int) and isinstance(position, int):
            rosters.setdefault(team_id, Counter())[position] += 1
    return rosters


def _need_score(roster: Counter[int], position: int) -> int:
    required = STARTER_REQUIREMENTS.get(position, 0)
    missing = max(0, required - roster[position])
    flex_surplus = sum(
        max(0, roster[pos] - STARTER_REQUIREMENTS[pos]) for pos in FLEX_POSITIONS
    )
    flex_open = flex_surplus == 0
    if position in {2, 3}:
        score = 25 + (75 * missing / required if required else 0)
        if missing == 0 and flex_open:
            score += 20
    elif position in {1, 4}:
        score = 15 + (55 if missing else 0)
        if position == 4 and missing == 0 and flex_open:
            score += 15
    else:
        score = 10
    return round(min(100, score))


def _current_and_next_user_slots(
    slots: Sequence[Mapping[str, Any]], user_team_id: int
) -> tuple[Mapping[str, Any] | None, Mapping[str, Any] | None, list[Mapping[str, Any]]]:
    open_slots = [
        slot
        for slot in slots
        if slot.get("player_id") is None and not slot.get("reserved_for_keeper")
    ]
    open_slots.sort(key=lambda slot: slot.get("overall_pick_number") or 10_000)
    current = open_slots[0] if open_slots else None
    if current is None:
        return None, None, []
    current_pick = current.get("overall_pick_number") or 0
    user_slots = [
        slot
        for slot in open_slots
        if slot.get("team_id") == user_team_id
        and (slot.get("overall_pick_number") or 0) >= current_pick
    ]
    next_user = user_slots[0] if user_slots else None
    if next_user is None:
        return current, None, []
    horizon_user = (
        user_slots[1]
        if next_user is current and len(user_slots) > 1
        else next_user
    )
    next_pick = horizon_user.get("overall_pick_number") or current_pick
    intervening = [
        slot
        for slot in open_slots
        if current_pick <= (slot.get("overall_pick_number") or 0) < next_pick
        and slot.get("team_id") != user_team_id
    ]
    return current, next_user, intervening


def recommend_draft_picks(
    league: Mapping[str, Any],
    draft: Mapping[str, Any],
    player_evidence: Mapping[str, Any],
    *,
    user_team_id: int,
    limit: int = 10,
) -> DraftBoard:
    """Rank available players using only normalized, explainable inputs."""

    season = int(player_evidence["season"])
    all_players = [
        player
        for player in player_evidence.get("players", [])
        if isinstance(player, Mapping) and isinstance(player.get("player_id"), int)
    ]
    players_by_id = {player["player_id"]: player for player in all_players}
    draft_state = draft.get("draft", {})
    picks = draft_state.get("picks", [])
    slots = draft_state.get("slots", [])
    taken = {pick.get("player_id") for pick in picks if pick.get("player_id") is not None}
    rosters = _rosters_by_team(picks, players_by_id)
    user_roster = rosters.get(user_team_id, Counter())
    current, next_user, intervening = _current_and_next_user_slots(slots, user_team_id)

    current_round = int(current.get("round_id") or 1) if current else 99
    allowed_positions = {1, 2, 3, 4}
    if current_round >= 12 or all(
        user_roster[pos] >= required for pos, required in STARTER_REQUIREMENTS.items()
    ):
        allowed_positions |= {5, 16}

    candidates = [
        player
        for player in all_players
        if player["player_id"] not in taken
        and player.get("active") is not False
        and player.get("default_position_id") in allowed_positions
        and _projection(player, season) is not None
    ]
    reception_points = _reception_points(league)
    ranks = {player["player_id"]: _rank(player, reception_points) for player in candidates}
    projections = {
        player["player_id"]: float(_projection(player, season) or 0.0)
        for player in candidates
    }

    available_by_position: dict[int, list[Mapping[str, Any]]] = {}
    for player in candidates:
        available_by_position.setdefault(player["default_position_id"], []).append(player)
    for position_players in available_by_position.values():
        position_players.sort(key=lambda player: projections[player["player_id"]], reverse=True)

    team_ids = {
        int(slot["team_id"])
        for slot in slots
        if isinstance(slot.get("team_id"), int)
    }
    replacement_points: dict[int, float] = {}
    for position, position_players in available_by_position.items():
        required = STARTER_REQUIREMENTS.get(position, 1)
        league_deficit = sum(
            max(0, required - rosters.get(team_id, Counter())[position])
            for team_id in team_ids
        )
        replacement_index = min(
            max(0, league_deficit - 1), max(0, len(position_players) - 1)
        )
        replacement_points[position] = projections[
            position_players[replacement_index]["player_id"]
        ]

    vorp = {
        player["player_id"]: max(
            0.0,
            projections[player["player_id"]]
            - replacement_points.get(player["default_position_id"], 0.0),
        )
        for player in candidates
    }
    max_vorp = max(vorp.values(), default=1.0) or 1.0

    demand_by_position: dict[int, int] = {}
    for position in allowed_positions:
        expected = sum(
            _need_score(rosters.get(int(slot["team_id"]), Counter()), position) / 100
            for slot in intervening
            if isinstance(slot.get("team_id"), int)
        )
        demand_by_position[position] = round(100 * (1.0 - math.exp(-expected / 3.0)))

    active_picks_before_user = len(intervening)
    scored: list[DraftRecommendation] = []
    for player in candidates:
        player_id = player["player_id"]
        position_id = player["default_position_id"]
        consensus_rank = ranks[player_id]
        value = round(100 * math.exp(-max(0.0, consensus_rank - 1.0) / 50.0))
        need = _need_score(user_roster, position_id)
        scarcity = round(100 * vorp[player_id] / max_vorp)
        demand = demand_by_position.get(position_id, 0)
        adp = player.get("market", {}).get("average_draft_position")
        expected_rank = float(adp) if isinstance(adp, (int, float)) and adp > 0 else consensus_rank
        gone = round(
            100
            / (
                1
                + math.exp(
                    -(
                        active_picks_before_user + 1 - expected_rank
                    )
                    / 4.0
                )
            )
        )
        health = _health(player)
        score = round(
            0.30 * value
            + 0.25 * need
            + 0.16 * scarcity
            + 0.10 * demand
            + 0.12 * gone
            + 0.07 * health
        )
        missing = max(
            0, STARTER_REQUIREMENTS.get(position_id, 0) - user_roster[position_id]
        )
        need_text = (
            f"fills {missing} open {POSITION_NAMES[position_id]} starter slot"
            f"{'s' if missing != 1 else ''}"
            if missing
            else f"adds {POSITION_NAMES[position_id]} depth"
        )
        description = (
            f"{need_text}; consensus rank {consensus_rank:.1f}; "
            f"{active_picks_before_user} opponent picks before your next decision; "
            f"{str(player.get('injury_status') or 'unknown').lower()}"
        )
        scored.append(
            DraftRecommendation(
                player_id=player_id,
                player_name=str(player.get("full_name") or player_id),
                position=POSITION_NAMES.get(position_id, str(position_id)),
                projected_points=round(projections[player_id], 1),
                value=value,
                need=need,
                scarcity=scarcity,
                opponent_demand=demand,
                gone_before_next_pick=gone,
                health=health,
                score=score,
                description=description,
            )
        )

    scored.sort(key=lambda item: (-item.score, -item.value, item.player_name))
    roster_names = tuple(
        str(players_by_id[pick["player_id"]].get("full_name") or pick["player_id"])
        for pick in picks
        if pick.get("team_id") == user_team_id and pick.get("player_id") in players_by_id
    )
    return DraftBoard(
        fetched_at=str(draft.get("fetched_at") or "unknown"),
        current_overall_pick=(
            int(current["overall_pick_number"])
            if current and isinstance(current.get("overall_pick_number"), int)
            else None
        ),
        current_team_id=(
            int(current["team_id"])
            if current and isinstance(current.get("team_id"), int)
            else None
        ),
        next_user_pick=(
            int(next_user["overall_pick_number"])
            if next_user and isinstance(next_user.get("overall_pick_number"), int)
            else None
        ),
        opponent_picks_before_user=active_picks_before_user,
        user_roster=roster_names,
        recommendations=tuple(scored[:limit]),
    )


def render_draft_board(board: DraftBoard) -> str:
    on_clock = (
        board.current_team_id is not None
        and board.current_overall_pick == board.next_user_pick
    )
    state = "ON THE CLOCK" if on_clock else "waiting"
    lines = [
        f"Draft state: {state}; current pick={board.current_overall_pick or 'complete'}; "
        f"your next pick={board.next_user_pick or 'none'}; "
        f"draft snapshot={board.fetched_at}",
        f"Your roster: {', '.join(board.user_roster) if board.user_roster else 'empty'}",
        "",
        "| # | Player | Pos | Proj | Value | Need | Scarcity | Opp demand | Gone next | Health | Score | Why |",
        "|---:|---|:---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for index, item in enumerate(board.recommendations, 1):
        lines.append(
            f"| {index} | {item.player_name} | {item.position} | "
            f"{item.projected_points:.1f} | {item.value} | {item.need} | "
            f"{item.scarcity} | {item.opponent_demand} | "
            f"{item.gone_before_next_pick} | {item.health} | {item.score} | "
            f"{item.description} |"
        )
    return "\n".join(lines)
