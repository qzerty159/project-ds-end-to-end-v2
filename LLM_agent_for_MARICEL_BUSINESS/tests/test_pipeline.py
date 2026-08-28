from __future__ import annotations

from io import StringIO
import unittest

import pandas as pd

from src.data_preparation import enrich_leads, normalize_leads_schema
from src.tools.data_analysis_tool import analyze_leads_csv
from src.tools.growth_diagnosis_tool import diagnose_growth


CSV = """company,industry,notes,contact_title,contact_email,website,linkedin,source
Alpha Conseil,Software and consulting,Long B2B consulting context for a qualified growth project.,CEO,ceo@alpha-consulting.fr,https://alpha-consulting.fr,https://www.linkedin.com/in/alpha,Event
Beta Retail,Retail,,, ,,,Cold list
Gamma Digital,Marketing,SEO and digital acquisition support for B2B companies.,Fondateur,founder@gamma.fr,https://gamma.fr,https://www.linkedin.com/in/gamma,Referral
"""


class PipelineTests(unittest.TestCase):
    def test_schema_aliases_and_scoring_are_robust(self) -> None:
        raw = pd.DataFrame({"company": ["Alpha"], "note": ["A useful note"], "industry": [None]})
        enriched = enrich_leads(raw)

        self.assertIn("notes", enriched.columns)
        self.assertEqual(enriched.loc[0, "name"], "Alpha")
        self.assertGreaterEqual(enriched.loc[0, "compatibility_score"], 0)
        self.assertLessEqual(enriched.loc[0, "compatibility_score"], 100)
        self.assertIn("rule_score", enriched.columns)

    def test_full_local_analysis_returns_ranked_leads(self) -> None:
        result = analyze_leads_csv(StringIO(CSV))

        self.assertEqual(result["stats"]["total_leads"], 3)
        self.assertEqual(len(result["dataframe"]), 3)
        self.assertIn(result["model_kind"], {"logistic_regression", "constant"})
        self.assertIn("high_value_prob", result["dataframe"].columns)
        self.assertEqual(result["predictions"][0]["name"], "Alpha Conseil")

    def test_single_class_dataset_uses_safe_model_fallback(self) -> None:
        result = analyze_leads_csv(StringIO(CSV), high_value_threshold=0)

        self.assertEqual(result["model_kind"], "constant")
        self.assertTrue((result["dataframe"]["high_value_prob"] == 1).all())

    def test_empty_diagnosis_is_safe(self) -> None:
        diagnosis = diagnose_growth(
            {"total_leads": 0, "avg_compatibility": 0, "high_value_ratio": 0}, []
        )
        self.assertIn("Aucun lead", diagnosis)

    def test_name_is_required(self) -> None:
        with self.assertRaisesRegex(ValueError, "name"):
            normalize_leads_schema(pd.DataFrame({"industry": ["Software"]}))


if __name__ == "__main__":
    unittest.main()
