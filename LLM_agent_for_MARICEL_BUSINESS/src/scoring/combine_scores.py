def combine_scores(rule_score: float, llm_score: float) -> float:
    """
    Final compatibility score = weighted average of rule-based and LLM scores.
    """
    final_score = 0.5 * rule_score + 0.5 * llm_score
    return round(final_score, 2)
