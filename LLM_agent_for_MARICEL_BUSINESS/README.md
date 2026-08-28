# MARICEL BUSINESS — Lead Qualification Agent

Application de data science pour qualifier, analyser et prioriser des leads B2B. Elle transforme un export CSV en un score de compatibilité explicable, des segments à cibler et une liste de leads à examiner en premier.

## Démarrer

Depuis ce dossier :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run src/app/streamlit_app.py
```

La fonctionnalité de recommandation IA est facultative. Pour l'activer, copiez `.env.example` vers `.env`, puis renseignez `OPENAI_API_KEY`. Ne versionnez jamais ce fichier.

```powershell
Copy-Item .env.example .env
```

## CSV attendu

La seule colonne obligatoire est `name` (l'alias `company` est accepté). Les colonnes suivantes enrichissent l'analyse :

| Colonne | Usage |
| --- | --- |
| `industry` | Pertinence du secteur |
| `contact_title` | Identification des décideurs |
| `contact_email`, `contact_email_personal` | Joignabilité professionnelle |
| `website`, `contact_linkedin_url` | Présence numérique |
| `notes` | Contexte du lead (`note` est accepté) |
| `source` | Comparaison des canaux d'acquisition |

Les en-têtes sont normalisés, les champs manquants sont créés vides et les exportations partielles restent donc analysables.

## Méthode

Le score déterministe est calculé sur 100, avec des composantes conservées dans le CSV exporté :

| Élément | Points maximum |
| --- | ---: |
| Pertinence du secteur | 25 |
| Séniorité du contact | 20 |
| E-mail professionnel | 15 |
| Profil LinkedIn | 10 |
| Site web | 10 |
| Complétude du lead | 10 |
| Contexte dans les notes | 10 |

Le seuil « high-value » est réglable dans l'interface (70/100 par défaut). Un modèle de régression logistique produit ensuite une **probabilité proxy de priorisation** à partir des attributs bruts. Il n'utilise volontairement jamais `compatibility_score` pour prédire `high_value_flag`, afin d'éviter la fuite de cible. Cette probabilité n'est pas une prédiction de conversion : elle doit être confrontée aux résultats réels de vos campagnes.

Pour les gros fichiers, le modèle est entraîné sur un échantillon stratifié de 20 000 lignes au maximum, puis appliqué à toutes les lignes. Cela garde l'application réactive sans écarter de lead du classement final.

## Interface

L'application Streamlit permet de :

- importer un CSV et choisir le seuil de priorité ;
- comparer les industries et les sources ;
- visualiser les scores et les leads prioritaires ;
- télécharger le CSV enrichi ;
- obtenir un diagnostic local, avec une reformulation IA facultative.

## Enrichissement externe

L'analyse de base est locale et ne nécessite aucun appel réseau. L'enrichissement web et LLM est explicitement activé dans la barre latérale, limité à 25 leads par défaut et doit être utilisé uniquement avec l'autorisation appropriée.

Les requêtes web n'acceptent que des URL HTTP(S) publiques, ne suivent pas les redirections et ne tentent ni connexion ni contournement de contrôle d'accès. L'enrichissement LLM ne remplit que les champs vides et demande au modèle de ne pas inventer de coordonnées. Vérifiez toujours les données produites avant utilisation commerciale et respectez le RGPD ainsi que les conditions d'utilisation des sites consultés.

## Tests

```powershell
$env:PYTHONPATH = (Resolve-Path '.').Path
python -m unittest discover -s tests -v
```

Les tests couvrent la normalisation des exports, le scoring, l'analyse locale, le repli sur classe unique et les diagnostics vides.

## Structure

```text
LLM_agent_for_MARICEL_BUSINESS/
├── src/
│   ├── app/                 # Interface Streamlit
│   ├── agent/               # Diagnostic local et réponse IA optionnelle
│   ├── scoring/             # Règles auditées et scoring LLM facultatif
│   ├── scraping/            # Enrichissement public opt-in
│   ├── data_preparation.py  # Validation, normalisation, enrichissement
│   ├── eda_utils.py         # Statistiques et analyses par segment
│   └── models.py            # Modèle de priorisation sans fuite de cible
├── tests/
├── .env.example
└── requirements.txt
```
