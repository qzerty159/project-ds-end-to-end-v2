# Données de leads — MARICEL BUSINESS

Ce dossier contient les exports CSV utilisés pour la démonstration. Ils ne sont pas versionnés afin d'éviter de publier des données de contact et des fichiers volumineux.

## Fichiers

- `contacts - contacts.csv.csv` : export de départ ;
- `contacts-contacts_enriched.csv` : export déjà enrichi fourni avec le projet ;
- `contacts - contacts_enriched.csv.gz` : archive de l'export enrichi.

L'application accepte l'un ou l'autre : elle normalise les en-têtes, gère les champs absents et ne requiert que `name` (ou `company`). Sur l'export fourni, l'analyse lit 107 067 leads non vides.

## Colonnes d'origine

Les données utilisées par le pipeline sont notamment :

- `name`, `website`, `contact_email` ;
- `industry`, `notes`, `source` ;
- `contact_full_name`, `contact_title`, `contact_email_personal`, `contact_linkedin_url`.

Certains exports peuvent aussi contenir `industry_clean`, `has_contact_info` ou un ancien `compatibility_score`. Ils sont acceptés, mais le pipeline ne dépend pas de ces colonnes dérivées.

## Règle appliquée par l'application

Par défaut, `compatibility_score` est recalculé à partir des règles transparentes documentées dans le README principal : secteur, séniorité, moyens de contact, présence web/LinkedIn, complétude et contexte. Les composantes (`industry_score`, `title_score`, etc.) restent dans le CSV téléchargé pour être vérifiables.

L'option « Conserver les scores déjà validés » permet de respecter une note CRM existante, tout en conservant `rule_score` pour comparer les deux sources. Les résultats de versions précédentes ne doivent donc pas être comparés directement à ceux obtenus avec les règles actuelles sans documenter le mode choisi.

## Confidentialité et qualité

Les coordonnées peuvent constituer des données personnelles. Limitez l'accès au dossier, vérifiez la base légale et les durées de conservation, et respectez les obligations applicables (dont le RGPD). Les scores servent à prioriser une revue humaine ; ils ne démontrent ni l'intérêt réel d'un prospect ni sa probabilité de conversion.
