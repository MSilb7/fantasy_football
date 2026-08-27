import json
from pathlib import Path
import unittest


class PayoutNotebookTests(unittest.TestCase):
    def test_2025_notebook_uses_shared_balanced_payout_plan(self) -> None:
        notebook_path = (
            Path(__file__).parents[1]
            / "apps"
            / "payouts"
            / "notebooks"
            / "pull_scores_2025.ipynb"
        )
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        source = "\n".join(
            "".join(cell.get("source", []))
            for cell in notebook["cells"]
            if cell.get("cell_type") == "code"
        )

        self.assertIn("from fantasy_assistant.payouts import", source)
        self.assertIn("first_second_pool", source)
        self.assertIn("payout_plan.is_balanced", source)
        self.assertNotIn("WINNERS_POT", source)


if __name__ == "__main__":
    unittest.main()
