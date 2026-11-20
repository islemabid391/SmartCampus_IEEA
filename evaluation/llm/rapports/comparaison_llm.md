# Rapport de comparaison multi-LLM — SmartCampus AI (SA-33)

## 1. Objectif et contexte
Ce rapport présente l'évaluation comparative de trois modèles de langage (LLM) open-weight destinés à l'assistant d'orientation universitaire **SmartCampus AI** (groupement NAU : **IIT**, **ISA**, **ISB**), dans le cadre de la tâche **SA-33**. L'objectif est d'exécuter les mêmes requêtes avec les mêmes paramètres afin de mesurer la qualité, la latence, le coût et les erreurs de chaque modèle, et de justifier le choix du modèle retenu.

## 2. Protocole et équité de la comparaison
- **Jeu de test (`SA-32`)** : **40 questions** en français réparties sur les catégories *admission*, *orientation*, *reformulation* et *ambigu* (incluant des questions sans contexte officiel, des demandes trop vagues et des cas pièges sur des tarifs périmés).
- **Paramètres identiques** : **3 passes** par question et par modèle (`360` requêtes au total dans `results/raw_20261120_013426.jsonl`), avec `temperature = 0.2`, `max_tokens = 500`, `timeout_secondes = 60` et le même prompt système officiel.
- **Modèles évalués** :
  1. **GPT-OSS 20B (`openai/gpt-oss-20b`)** via l'API **Groq** (`open_source` cloud, tarifs configurés au `2026-11-20` : `$0.075` / 1M tokens entrée, `$0.30` / 1M tokens sortie).
  2. **GPT-OSS 120B (`openai/gpt-oss-120b`)** via l'API **Groq** (`open_source` cloud, tarifs configurés au `2026-11-20` : `$0.15` / 1M tokens entrée, `$0.60` / 1M tokens sortie).
  3. **Mistral 7B (`mistral`)** via **Ollama** en local (`open_source_local`, `http://localhost:11434/v1`, coût API `$0.0000`, mis en place suite au blocage de l'API Mistral distante au niveau de l'organisation).
- **Méthode de notation** : notation humaine des 120 réponses uniques (`justesse`, `pertinence`, `qualite_francais` sur l'échelle `0`, `1`, `2`) croisée avec les vérifications automatiques et les métriques techniques. Le score global (`/100`) pondère la qualité (`50%`), la latence (`20%`), le coût (`20%`) et les erreurs (`10%`).

## 3. Résultats comparatifs

### 3.1 Synthèse des performances
| Modèle | Note humaine (/2) | Mots-clés (%) | Valeurs interdites | Cohérence reform. (%) | Latence méd. (ms) | Latence p95 (ms) | Coût / 1000 req ($) | Erreurs (%) | Score global (/100) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **GPT-OSS 20B (Groq - Petit)** (`openai/gpt-oss-20b`) | 1.73 | 75.0% | 0 | 66.7% | 1504.0 | 5751.8 | $0.1142 | 24.2% | **81.1** |
| **GPT-OSS 120B (Groq - Grand)** (`openai/gpt-oss-120b`) | 1.86 | 72.1% | 0 | 100.0% | 1216.0 | 6009.8 | $0.2303 | 23.3% | **76.3** |
| **Mistral 7B (Ollama Local)** (`mistral`) | 1.73 | 90.8% | 0 | 100.0% | 17203.3 | 103634.7 | $0.0000 | 6.7% | **75.9** |

### 3.2 Diagnostic exact des erreurs par modèle (sur 120 requêtes par modèle)
L'analyse directe des logs bruts (`erreur_type` et `finish_reason` dans `results/raw_20261120_013426.jsonl`) démontre la nature exacte des erreurs comptabilisées :

| Modèle | Succès (`stop`) | `reponse_tronquee` (`length`) | `reponse_vide` (`length`) | `timeout` (`None`) | Total erreurs |
|---|---:|---:|---:|---:|---:|
| **`openai/gpt-oss-20b`** | 91 | 25 | 4 | 0 | **29 / 120 (24.2 %)** |
| **`openai/gpt-oss-120b`** | 92 | 28 | 0 | 0 | **28 / 120 (23.3 %)** |
| **`mistral` (Ollama local)** | 112 | 0 | 0 | 8 | **8 / 120 (6.7 %)** |

- **Sur Groq (`gpt-oss-20b` et `gpt-oss-120b`)** : il ne s'agit pas d'erreurs HTTP ou de quota (`0` erreur réseau), mais de **réponses coupées par la limite `max_tokens = 500`** (`finish_reason = "length"`), notamment lorsque le modèle génère des tableaux Markdown détaillés, ainsi que **4 réponses vides** sur `gpt-oss-20b` (consommation du budget de tokens par le raisonnement interne avant la production du texte).
- **Sur Ollama local (`mistral`)** : `0` troncature, mais **8 timeouts** (`6.7 %`) lors de pics de charge CPU/RAM sur le poste local en fin de campagne.

## 4. Analyse comparative et limites

### Points clés de l'analyse
- **Fiabilité factuelle** : aucune valeur interdite (tarif périmé de 3 900 TND ou date inventée) n'a été détectée sur les questions pièges ciblées (`0` sur les trois modèles). La notation humaine de `justesse` confirme une bonne fidélité globale au contexte officiel, malgré quelques imprécisions isolées (ex. invention d'une URL externe sur une question sans contexte ou confusion ponctuelle sur un sigle).
- **Qualité vs vitesse vs coût** :
  - **`openai/gpt-oss-20b`** obtient le **meilleur score global (`81.1 / 100`)** grâce au meilleur équilibre entre rapidité (`1 504.0 ms` en médiane), coût réduit (`$0.1142` / 1 000 requêtes, soit ~2× moins cher que le `120B`) et qualité humaine (`1.73 / 2`).
  - **`openai/gpt-oss-120b`** obtient la **meilleure note humaine (`1.86 / 2`)**, une latence médiane très rapide (`1 216.0 ms`) et une cohérence parfaite sur les reformulations (`100.0 %`), mais coûte deux fois plus cher (`$0.2303` / 1 000 requêtes), ce qui le place deuxième au score pondéré (`76.3 / 100`).
  - **`mistral` (Ollama local)** présente un coût API nul (`$0.0000`) et le taux d'erreurs brut le plus bas (`6.7 %`), mais sa latence en local (`17.2 s` en médiane et `103.6 s` au p95) le rend inadapté au dialogue interactif en temps réel.

### Limites méthodologiques
- **Taille de l'échantillon et évaluation** : jeu de 40 questions évalué par un seul annotateur (la cohérence sur les reformulations porte sur 3 groupes de questions, soit `66.7 %` = 2/3 pour `20B` et `100 %` = 3/3 pour `120B` et `Mistral`).
- **Impact de `max_tokens = 500`** : le plafond de 500 tokens pénalise artificiellement le taux d'erreurs des modèles Groq qui structurent leurs réponses en tableaux comparatifs, et les métriques de mots-clés sont calculées sur les réponses non vides.
- **Conditions d'exécution** : les latences cloud dépendent de la charge des serveurs Groq au moment du test (`2026-11-20`), tandis que les performances d'Ollama dépendent du matériel local et n'intègrent pas le coût d'infrastructure.

## 5. Décision : modèle retenu
- **Modèle retenu : `openai/gpt-oss-20b` (Groq)** comme modèle principal par défaut, parce qu'il obtient le **meilleur score global (`81.1 / 100`)** en combinant une faible latence médiane (`~1.5 s`), un coût deux fois inférieur à celui du modèle 120B (`$0.1142` / 1 000 requêtes) et l'absence de valeurs interdites détectées.
- **Recommandation d'usage et paramètre critique** :
  - Utiliser **`openai/gpt-oss-120b` (Groq)** en alternative haute précision si l'équipe privilégie la note humaine maximale (`1.86 / 2`) et la cohérence des reformulations (`100 %`), l'écart de coût restant faible à petite échelle (`+$0.12` / 1 000 requêtes).
  - Augmenter impérativement **`max_tokens` à `1500`** (et privilégier des réponses concises sans tableaux lourds) lors de l'intégration applicative afin d'éliminer les troncatures (`finish_reason = "length"`).
  - Réserver **`mistral` (Ollama local)** aux tests hors ligne ou traitements sans contrainte temps réel.