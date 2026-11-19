# Évaluation des LLM — SmartCampus AI (SA-32 / SA-33 / SA-34)

Ce dossier regroupe les jeux de données, scripts et rapports d'évaluation permettant de sélectionner le modèle de langage (LLM) principal de la plateforme.

## Structure
- `data/questions_fr.json` : Jeu de 40 questions de référence en français (SA-32), aligné sur les données officielles du catalogue (SA-18).
- `data/questions_dialecte.json` : Jeu de test en tunisien, Arabizi et code-switching FR/TN (SA-34).
- `config/models.yaml` : Liste des modèles candidats et paramètres d'inférence (SA-33).
- `run_eval.py` : Script d'exécution des benchmarks (SA-33).
- `results/` : Résultats bruts et métriques calculées.
- `rapports/` : Analyses comparatives et justifications.

## Répartition du jeu de données `questions_fr.json` (SA-32)
- **Admission (12 questions)** : Conditions d'accès, tarifs actuels (avec contrôle de non-régression sur l'ancien tarif périmé de 3900 TND), durées, passerelles, et 3 questions hors périmètre/non publiées pour tester l'absence d'hallucination.
- **Orientation (10 questions)** : Adéquation profil/filière, comparaisons de parcours, débouchés.
- **Reformulations (9 questions)** : 3 intentions déclinées en 3 formulations chacune (formelle, standard, familière).
- **Cas ambigus (9 questions)** : Demandes incomplètes nécessitant une demande de précision.

## Schéma d'une entrée JSON
- `id` : Identifiant unique de la question.
- `categorie` : `admission`, `orientation`, `reformulation` ou `ambigu`.
- `groupe` : Identifiant commun reliant les reformulations d'une même intention (ou `null`).
- `question` : Requête utilisateur envoyée au modèle.
- `contexte` : Extrait des données officielles fourni dans le prompt (ou `null` pour tester la reconnaissance des limites).
- `reponse_attendue` : Éléments factuels attendus dans la réponse.
- `comportement_attendu` : `repondre`, `demander_precision`, `reconnaitre_limite` ou `repondre_et_preciser`.
- `mots_cles` : Expressions régulières devant apparaître dans une réponse valide.
- `mots_interdits` : Expressions régulières ne devant pas apparaître (ex. tarifs périmés, informations inventées).