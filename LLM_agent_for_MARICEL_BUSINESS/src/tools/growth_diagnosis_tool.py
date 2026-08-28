"""Translate analysis aggregates into concise, defensive recommendations."""


def diagnose_growth(stats: dict, perf: list[dict]) -> str:
    """Generate a deterministic diagnosis that also works for an empty grouping."""
    if not stats.get("total_leads"):
        return "Aucun lead exploitable n'a été trouvé dans le fichier."

    messages = [
        f"{stats['total_leads']} leads analysés.",
        f"Score de compatibilité moyen : {stats['avg_compatibility']:.1f}/100.",
        f"Part de leads prioritaires : {stats['high_value_ratio']:.1%}.",
        f"Leads joignables : {stats.get('contactable_ratio', 0):.1%}.",
    ]

    if perf:
        best = max(perf, key=lambda item: (item["avg_score"], item["leads"]))
        messages.append(
            f"Segment à prioriser : {best['industry']} "
            f"({best['avg_score']:.1f}/100 sur {best['leads']} leads)."
        )

    if stats["avg_compatibility"] < 50:
        messages.append("Action recommandée : resserrer l'ICP et compléter les coordonnées avant de lancer des séquences d'outreach.")
    else:
        messages.append("Action recommandée : traiter d'abord les leads au score élevé, puis mesurer les réponses par segment pour ajuster l'ICP.")
    return "\n".join(messages)
