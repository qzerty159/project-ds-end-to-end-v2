"""Streamlit interface for the MARICEL BUSINESS lead qualification workflow."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent.llm_agent import generate_consultant_response
from src.tools.data_analysis_tool import analyze_leads_csv

st.set_page_config(page_title="MARICEL BUSINESS — Lead Qualification", page_icon="📈", layout="wide")
st.title("MARICEL BUSINESS · Qualification des leads")
st.caption("Scoring transparent, analyse locale par défaut et recommandations actionnables.")

with st.sidebar:
    st.header("Données et règles")
    uploaded_file = st.file_uploader("Importer un fichier CSV", type=["csv"])
    threshold = st.slider("Seuil high-value", min_value=0, max_value=100, value=70, step=5)
    preserve_existing_score = st.checkbox("Conserver les scores déjà validés", value=False)

    st.divider()
    st.header("Enrichissement facultatif")
    enable_web_enrichment = st.checkbox("Consulter des pages web publiques", value=False)
    enable_llm_enrichment = st.checkbox(
        "Compléter avec un LLM",
        value=False,
        disabled=not enable_web_enrichment,
    )
    enrichment_limit = st.number_input(
        "Nombre maximal de leads enrichis",
        min_value=1,
        max_value=100,
        value=25,
        disabled=not enable_web_enrichment,
        help="L'enrichissement envoie des requêtes à des services tiers et peut engendrer des coûts.",
    )
    if enable_web_enrichment:
        st.warning("N'utilisez cette option que pour des données et des sites que vous êtes autorisé à traiter.")

    st.divider()
    use_llm_response = st.checkbox(
        "Générer une recommandation IA",
        value=False,
        help="Nécessite OPENAI_API_KEY. L'analyse des scores fonctionne sans cette clé.",
    )

user_message = st.text_area(
    "Votre objectif",
    value="Nous voulons identifier les leads prioritaires et les segments à travailler en premier.",
    help="Ce contexte est utilisé pour formuler la recommandation finale.",
)

analyse_clicked = st.button("Analyser les leads", type="primary", disabled=uploaded_file is None)

if uploaded_file is None:
    st.info("Importez un CSV pour commencer. La seule colonne indispensable est `name`; les autres champs améliorent le score.")

if analyse_clicked and uploaded_file is not None:
    try:
        with st.spinner("Analyse du fichier en cours…"):
            result = analyze_leads_csv(
                uploaded_file,
                high_value_threshold=float(threshold),
                preserve_existing_score=preserve_existing_score,
                enrich_with_web=enable_web_enrichment,
                enrich_with_llm=enable_llm_enrichment,
                enrichment_limit=int(enrichment_limit),
            )
        st.session_state["analysis_result"] = result
        st.session_state["analysis_message"] = user_message
    except ValueError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.exception(exc)

result = st.session_state.get("analysis_result")
if result:
    stats = result["stats"]
    metric_1, metric_2, metric_3, metric_4 = st.columns(4)
    metric_1.metric("Leads analysés", f"{stats['total_leads']:,}")
    metric_2.metric("Score moyen", f"{stats['avg_compatibility']:.1f}/100")
    metric_3.metric("High-value", f"{stats['high_value_ratio']:.1%}")
    metric_4.metric("Leads joignables", f"{stats['contactable_ratio']:.1%}")

    dataframe = result["dataframe"]
    industry_df = pd.DataFrame(result["industry_performance"])
    source_df = pd.DataFrame(result["source_performance"])
    top_leads = pd.DataFrame(result["predictions"])

    tab_overview, tab_segments, tab_leads, tab_consultant = st.tabs(
        ["Vue d'ensemble", "Segments", "Leads", "Recommandation"]
    )
    with tab_overview:
        st.subheader("Distribution des scores")
        st.bar_chart(dataframe["compatibility_score"].value_counts(bins=10).sort_index())
        st.caption("Le score est une règle de priorisation explicable, pas une probabilité de conversion.")

    with tab_segments:
        st.subheader("Performance par industrie")
        st.dataframe(industry_df, use_container_width=True, hide_index=True)
        st.subheader("Performance par source")
        st.dataframe(source_df, use_container_width=True, hide_index=True)

    with tab_leads:
        st.subheader("Leads à examiner en premier")
        st.dataframe(top_leads, use_container_width=True, hide_index=True)
        st.download_button(
            "Télécharger le CSV enrichi",
            data=dataframe.to_csv(index=False).encode("utf-8"),
            file_name="leads_analyses.csv",
            mime="text/csv",
        )
        if result["model_kind"] == "constant":
            st.info("Le fichier ne contient qu'une seule classe high-value : la probabilité proxy est donc constante.")

    with tab_consultant:
        response = generate_consultant_response(
            st.session_state.get("analysis_message", user_message),
            result,
            use_llm=use_llm_response,
        )
        st.markdown(response)
