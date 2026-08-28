# Plan de présentation — MARICEL BUSINESS Lead Qualification Agent

Durée cible : 15 à 20 minutes.

## 1. Contexte et problème (2 min)

- MARICEL BUSINESS doit prioriser un portefeuille de prospects B2B hétérogène.
- Un export CRM brut ne permet pas immédiatement de comparer les segments ni de préparer les actions commerciales.
- Question : comment transformer ce fichier en une liste de priorités explicable et exploitable ?

## 2. Données et préparation (3 min)

- Présenter les champs : entreprise, secteur, notes, source, contact, site et LinkedIn.
- Montrer la normalisation des colonnes et la prise en charge des valeurs manquantes.
- Expliquer que l'analyse locale ne fait aucun appel externe par défaut.
- Mentionner la confidentialité des coordonnées et la nécessité d'une validation humaine.

## 3. Score de compatibilité transparent (3 min)

- Décrire les sept composantes : secteur, séniorité, e-mail, LinkedIn, site, complétude, notes.
- Afficher un exemple de ligne et la décomposition de son score.
- Justifier le seuil high-value choisi (70/100 par défaut, réglable).
- Insister : c'est une aide à la priorisation, pas une vérité métier ni une prédiction de conversion.

## 4. EDA et enseignements (3 min)

- Distribution des scores.
- Score moyen et ratio high-value par industrie.
- Score moyen et ratio high-value par source.
- Identifier un segment à tester en priorité et une donnée à améliorer (par exemple les coordonnées manquantes).

## 5. Modèle de priorisation (2 min)

- Régression logistique sur les attributs bruts, texte des notes inclus.
- Expliquer la prévention de la fuite de cible : `compatibility_score` n'est pas utilisé pour prédire `high_value_flag`.
- Présenter `high_value_prob` comme un signal de classement proxy.
- Pour les gros exports : entraînement échantillonné, prédiction sur tous les leads.

## 6. Démonstration Streamlit (3 min)

- Importer un CSV, fixer le seuil, lancer l'analyse.
- Montrer les métriques, les onglets Segments et Leads, puis le téléchargement du CSV enrichi.
- Montrer le diagnostic local et, si une clé est configurée, la recommandation IA facultative.

## 7. Limites et prochaines étapes (2 min)

- La qualité du résultat dépend de la qualité du CRM et des règles choisies.
- Valider les priorités par des résultats de campagne réels (réponse, rendez-vous, conversion).
- Ajouter un retour CRM pour entraîner un modèle sur des conversions observées.
- Définir une politique explicite avant tout enrichissement web/LLM : consentement, conformité, coût et contrôle qualité.
