# Rapport de comparaison multi-LLM — SmartCampus AI (SA-33)

## 1. Objectif et contexte
Ce rapport présente l'évaluation comparative de trois modèles de langage (LLM) open-weight destinés à l'assistant d'orientation universitaire **SmartCampus AI** (groupement NAU : **IIT**, **ISA**, **ISB**), dans le cadre de la tâche **SA-33**. L'objectif est de sélectionner le modèle le plus fiable, réactif et économique pour répondre en français aux questions d'orientation, d'admission, de reformulation et de gestion de cas ambigus ou hors périmètre.

## 2. Protocole d'évaluation
- **Jeu de test (`SA-32`)** : **40 questions** en français couvrant les catégories *admission*, *orientation*, *reformulation* et *ambigu* (incluant des questions sans contexte officiel, des demandes trop vagues et des pièges sur des tarifs périmés).
- **Campagne d'exécution** : **3 passes** par question et par modèle (`360` requêtes au total), avec `temperature = 0.2`, `max_tokens = 500` et `timeout_secondes = 60` (fichier `results/raw_20261120_013426.jsonl`).
- **Modèles évalués** :
  1. **GPT-OSS 20B (`openai/gpt-oss-20b`)** via l'API **Groq** (`open_source` cloud).
  2. **GPT-OSS 120B (`openai/gpt-oss-120b`)** via l'API **Groq** (`open_source` cloud).
  3. **Mistral 7B (`mistral`)** via **Ollama** en local (`open_source_local`, `http://localhost:11434/v1`).
- **Évaluation humaine et score global** : notation des réponses (`justesse`, `pertinence`, `qualite_francais` sur l'échelle `0`, `1`, `2`) croisée avec les métriques automatiques (mots-clés, fausses informations, cohérence sur les reformulations, latence médiane et p95, coût estimé pour 1 000 requêtes et taux d'erreurs). Le score global (`/100`) pondère la qualité (`50%`), la latence (`20%`), le coût (`20%`) et les erreurs (`10%`).

## 3. Résultats comparatifs

| Modèle | Note humaine (/2) | Mots-clés (%) | Fausses infos | Cohérence reform. (%) | Latence méd. (ms) | Latence p95 (ms) | Coût / 1000 req ($) | Erreurs (%) | Score global (/100) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **GPT-OSS 20B (Groq - Petit)** (`openai/gpt-oss-20b`) | 1.73 | 75.0% | 0 | 66.7% | 1504.0 | 5751.8 | $0.1142 | 24.2% | **81.1** |
| **GPT-OSS 120B (Groq - Grand)** (`openai/gpt-oss-120b`) | 1.86 | 72.1% | 0 | 100.0% | 1216.0 | 6009.8 | $0.2303 | 23.3% | **76.3** |
| **Mistral 7B (Ollama Local)** (`mistral`) | 1.73 | 90.8% | 0 | 100.0% | 17203.3 | 103634.7 | $0.0000 | 6.7% | **75.9** |

## 4. Analyse détaillée par modèle

### GPT-OSS 20B (`openai/gpt-oss-20b` — Groq) : meilleur score global (`81.1 / 100`)
- **Points forts** : obtient le meilleur score global grâce à un compromis très efficace entre qualité perçue (`1.73/2`), réactivité (`1 504.0 ms` en médiane, `5 751.8 ms` au p95) et coût réduit (`$0.1142` / 1 000 requêtes). Aucune fausse information détectée (`0`).
- **Limites** : cohérence sur les reformulations plus faible (`66.7%`) que les deux autres modèles et taux d'erreurs brut de `24.2%` (réponses incomplètes/tronquées ou incidents d'exécution).

### GPT-OSS 120B (`openai/gpt-oss-120b` — Groq) : meilleure note humaine (`76.3 / 100`)
- **Points forts** : affiche la meilleure note humaine (`1.86/2`), la latence médiane la plus basse (`1 216.0 ms`), une cohérence parfaite sur les reformulations (`100.0%`) et `0` fausse information.
- **Limites** : coût par 1 000 requêtes environ deux fois plus élevé (`$0.2303` vs `$0.1142`) que `GPT-OSS 20B`, latence p95 légèrement supérieure (`6 009.8 ms`) et taux d'erreurs brut de `23.3%`.

### Mistral 7B (`mistral` — Ollama Local) : zéro coût API mais forte latence locale (`75.9 / 100`)
- **Points forts** : coût API nul (`$0.0000`), `100.0%` de cohérence sur les reformulations, `90.8%` de couverture des mots-clés, `0` fausse information et le taux d'erreurs brut le plus bas (`6.7%`). Permet également de garder les données localement.
- **Limites** : latence très élevée sur poste local (`17 203.3 ms` de médiane, soit ~17,2 s, et `103 634.7 ms` au p95, soit ~103,6 s, avec un pic de timeout observé en fin de campagne), ce qui dégrade l'expérience utilisateur interactive.

## 5. Recommandation et pistes d'amélioration
- **Modèle retenu en priorité** : **`openai/gpt-oss-20b` (Groq)** pour son **score global de 81.1 / 100**, sa rapidité d'exécution (~1,5 s en médiane) et son coût deux fois inférieur à celui de `openai/gpt-oss-120b`.
- **Alternative haute précision / secours** : **`openai/gpt-oss-120b` (Groq)** reste pertinent pour les cas d'orientation complexes ou lorsque la cohérence de reformulation (`100.0%`) et la note humaine maximale (`1.86/2`) priment sur le coût, tandis que **`mistral` (Ollama local)** est à privilégier uniquement pour des tests hors ligne ou des traitements différés sans contrainte de temps réel.
- **Pistes d'amélioration** : augmenter légèrement `max_tokens` (au-delà de `500`) pour éviter les réponses tronquées contenant des tableaux comparatifs, et renforcer le cadrage du prompt système sur les questions ambiguës ou hors contexte.