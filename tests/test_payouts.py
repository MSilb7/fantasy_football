from decimal import Decimal
import json
from pathlib import Path
import unittest

from fantasy_assistant.payouts import PayoutRules, calculate_payout_plan


class PayoutPlanTests(unittest.TestCase):
    def test_every_payout_is_funded_by_the_total_buy_in_pot(self) -> None:
        fixture_path = Path(__file__).parent / "fixtures" / "payout_plan.json"
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        inputs = fixture["inputs"]
        expected = fixture["expected"]

        plan = calculate_payout_plan(
            num_teams=inputs["num_teams"],
            regular_season_weeks=inputs["regular_season_weeks"],
            rules=PayoutRules(
                buy_in=Decimal(inputs["buy_in"]),
                weekly_highs_share=Decimal(inputs["weekly_highs_share"]),
                first_place_share=Decimal(inputs["first_place_share"]),
                second_place_share=Decimal(inputs["second_place_share"]),
                third_place_payout=Decimal(inputs["third_place_payout"]),
            ),
        )

        for field, value in expected.items():
            self.assertEqual(getattr(plan, field), Decimal(value), field)
        self.assertEqual(plan.total_distributed, plan.total_pot)

    def test_rejects_a_distribution_larger_than_the_total_pot(self) -> None:
        with self.assertRaisesRegex(ValueError, "exceed the total pot"):
            calculate_payout_plan(
                num_teams=1,
                regular_season_weeks=14,
                rules=PayoutRules(
                    buy_in=Decimal("50"),
                    weekly_highs_share=Decimal("0.20"),
                    first_place_share=Decimal("0.75"),
                    second_place_share=Decimal("0.25"),
                    third_place_payout=Decimal("50"),
                ),
            )


if __name__ == "__main__":
    unittest.main()
