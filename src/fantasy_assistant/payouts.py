"""Pure, auditable payout calculations shared by payout presentations."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


ZERO = Decimal("0")
ONE = Decimal("1")


@dataclass(frozen=True)
class PayoutRules:
    """Financial inputs ESPN does not own."""

    buy_in: Decimal
    weekly_highs_share: Decimal
    first_place_share: Decimal
    second_place_share: Decimal
    third_place_payout: Decimal


@dataclass(frozen=True)
class PayoutPlan:
    """A complete allocation of one league's buy-in pot."""

    total_pot: Decimal
    weekly_highs_pot: Decimal
    first_second_pool: Decimal
    first_place_payout: Decimal
    second_place_payout: Decimal
    third_place_payout: Decimal
    weekly_payout_per_win: Decimal

    @property
    def total_distributed(self) -> Decimal:
        return (
            self.weekly_highs_pot
            + self.first_place_payout
            + self.second_place_payout
            + self.third_place_payout
        )

    @property
    def is_balanced(self) -> bool:
        return self.total_distributed == self.total_pot


def _validate_rules(rules: PayoutRules) -> None:
    if rules.buy_in < ZERO:
        raise ValueError("Buy-in cannot be negative.")
    if rules.third_place_payout < ZERO:
        raise ValueError("Third-place payout cannot be negative.")
    if not ZERO <= rules.weekly_highs_share <= ONE:
        raise ValueError("Weekly-highs share must be between 0 and 1.")
    if not ZERO <= rules.first_place_share <= ONE:
        raise ValueError("First-place share must be between 0 and 1.")
    if not ZERO <= rules.second_place_share <= ONE:
        raise ValueError("Second-place share must be between 0 and 1.")
    if rules.first_place_share + rules.second_place_share != ONE:
        raise ValueError("First- and second-place shares must sum to 1.")


def calculate_payout_plan(
    *,
    num_teams: int,
    regular_season_weeks: int,
    rules: PayoutRules,
) -> PayoutPlan:
    """Allocate the total pot across weekly, first, second, and third payouts.

    The fixed third-place payout is removed before first and second split their
    pool, ensuring that every payout is funded by total team buy-ins.
    """

    if num_teams <= 0:
        raise ValueError("Number of teams must be positive.")
    if regular_season_weeks <= 0:
        raise ValueError("Regular-season weeks must be positive.")
    _validate_rules(rules)

    total_pot = rules.buy_in * num_teams
    weekly_highs_pot = total_pot * rules.weekly_highs_share
    available_for_placements = total_pot - weekly_highs_pot
    if rules.third_place_payout > available_for_placements:
        raise ValueError("Weekly highs and third-place payout exceed the total pot.")

    first_second_pool = available_for_placements - rules.third_place_payout
    plan = PayoutPlan(
        total_pot=total_pot,
        weekly_highs_pot=weekly_highs_pot,
        first_second_pool=first_second_pool,
        first_place_payout=first_second_pool * rules.first_place_share,
        second_place_payout=first_second_pool * rules.second_place_share,
        third_place_payout=rules.third_place_payout,
        weekly_payout_per_win=weekly_highs_pot / regular_season_weeks,
    )
    if not plan.is_balanced:
        raise ValueError("Payout plan does not reconcile to the total pot.")
    return plan
