"""Main, local-first lead-analysis pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO, TextIO

from src.data_preparation import enrich_leads, load_leads_data
from src.eda_utils import basic_stats, industry_performance, source_performance
from src.models import build_high_value_model, predict_high_value


def analyze_leads_csv(
    file: str | Path | BinaryIO | TextIO,
    *,
    high_value_threshold: float = 70.0,
    preserve_existing_score: bool = False,
    enrich_with_web: bool = False,
    enrich_with_llm: bool = False,
    enrichment_limit: int = 25,
    model_training_limit: int = 20_000,
) -> dict:
    """Analyse a CSV and return UI-friendly results.

    Enrichment is opt-in because it sends requests to third parties, can be slow,
    and may process personal data. The default path is deterministic and offline.
    """
    if enrich_with_llm and not enrich_with_web:
        raise ValueError("L'enrichissement LLM nécessite d'abord l'enrichissement web.")
    if enrichment_limit < 1:
        raise ValueError("La limite d'enrichissement doit être positive.")

    dataframe = load_leads_data(file)
    if enrich_with_web:
        from src.scraping.enrichment_pipeline import enrich_with_scraping

        dataframe = enrich_with_scraping(dataframe, max_rows=enrichment_limit)
    if enrich_with_llm:
        from src.scraping.enrichment_pipeline_llm import enrich_with_llm as enrich_with_llm_pipeline

        dataframe = enrich_with_llm_pipeline(dataframe, max_rows=enrichment_limit)

    enriched = enrich_leads(
        dataframe,
        high_value_threshold=high_value_threshold,
        preserve_existing_score=preserve_existing_score,
    )
    model = build_high_value_model(enriched, max_training_rows=model_training_limit)
    predicted = predict_high_value(model, enriched)
    ranked = predicted.sort_values(["high_value_prob", "compatibility_score"], ascending=False)

    industry = industry_performance(predicted)
    source = source_performance(predicted)
    return {
        "stats": basic_stats(predicted),
        "industry_performance": industry.to_dict(orient="records"),
        "source_performance": source.to_dict(orient="records"),
        "predictions": ranked[["name", "compatibility_score", "high_value_prob", "high_value_flag"]]
        .head(25)
        .to_dict(orient="records"),
        "dataframe": predicted,
        "model_kind": "constant" if model.__class__.__name__ == "ConstantHighValueModel" else "logistic_regression",
        "model_training_rows": min(len(enriched), model_training_limit),
    }
