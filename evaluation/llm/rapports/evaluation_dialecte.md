# SA-34 - Evaluation de la comprehension du dialecte tunisien et de l'Arabizi

**Modele evalue** : `openai/gpt-oss-20b` (Groq), retenu en SA-33.
**Perimetre** : questions en tunisien (ecriture arabe), en Arabizi et en melange francais/tunisien (code-switching) ; identification des erreurs ; definition d'une solution de repli.

## 1. Resume

- Le modele **comprend l'intention** de la grande majorite des questions en dialecte : **49/55 (89 %)** jugees correctes en annotation manuelle, **2/55 (4 %)** fausses, 4 partielles. Le format JSON est respecte a 100 %, et la reponse est toujours en francais.
- Les deux seules vraies erreurs de comprehension sont en **Arabizi** et portent sur le mot interrogatif « 9adech » combine a un verbe (confusion duree / prix). Une des deux est **silencieuse** : le modele se declare sur de lui.
- Le vrai point faible observe n'est **pas la comprehension mais la fiabilite des reponses** : seulement **33/55 (60 %)** de reponses jugees justes et **18/55 (33 %)** contenant une information inventee (documents, demarches, details absents du contexte officiel). Le controle automatique des mots interdits ne detecte aucune de ces hallucinations (0 %).
- **Nous n'avons pas mesure ce taux d'hallucination en francais** : il est donc impossible, a ce stade, de dire s'il est specifique au dialecte.
- Les resultats sont **stables sur 3 passes** (89 % de comprehension `ok` a chaque passe) et les deux erreurs d'intention sont **reproductibles** ; l'erreur silencieuse n'est jamais signalee par l'auto-evaluation du modele.
- Aucune degradation marquee de la comprehension n'est observee entre francais et dialecte sur ce jeu de test (2 regressions sur 41 paires), mais l'echantillon est petit.
- Le chemin de repli « echec de comprehension -> demander une reformulation en francais » n'a **jamais ete exerce** (0 echec sur 55) : le jeu de test est trop propre pour le solliciter.

## 2. Protocole

| Element | Valeur |
|---|---|
| Jeu de test | 55 questions : 17 `tn_arabe`, 24 `arabizi`, 14 `code_switching` |
| Lien avec le francais | chaque question dialecte pointe vers une des 40 questions SA-32 (`variante_de`) : meme contexte officiel, memes mots-cles |
| Redaction des questions | locuteur natif de l'equipe (meme personne que l'annotateur : biais possible) |
| Prompt | `config/prompt_dialecte.txt` : sortie JSON `langue_detectee`, `intention_comprise`, `comprehension` (ok / partielle / echec), `comportement`, `reponse` ; reponse toujours en francais |
| Parametres | temperature 0,2 ; `max_tokens` 1500 ; pause 1 s entre requetes |
| Campagne francaise | 3 passes, 120 requetes, 120 reussies |
| Campagne dialecte | 3 passes completes, 165/165 reponses valides (voir incident ci-dessous) |
| Analyse | principale : passe 1 des deux campagnes (comparaison appariee par `variante_de`, seule passe annotee a la main) ; complementaire : stabilite sur les 3 passes du dialecte |
| Evaluation | (a) controle automatique (mots-cles / mots interdits, montants normalises) ; (b) annotation manuelle des 55 reponses (grille 0/1/2) |

**Incident de collecte (resolu).** Lors de la premiere campagne dialecte (22/11, 09h12), 72 requetes des passes 2 et 3 ont echoue en `429` : le quota **journalier** de Groq (200 000 tokens par jour et par organisation) etait epuise, et 1 requete a produit une reponse vide (budget de tokens consomme). Un second token du meme compte n'a rien change (le quota s'applique a l'organisation). Apres liberation du quota, les 73 requetes manquantes ont ete relancees avec l'option `--reprendre` de `run_eval.py` : toutes ont reussi. Les 92 reponses initiales ont ete conservees telles quelles. **Les 92 reponses d'origine ont ete generees avec `max_tokens` 1500, les 73 reponses de reprise avec 2000** (simple plafond, il ne modifie pas les reponses deja obtenues, mais la difference est a connaitre). Les resultats de la passe 1 sont identiques dans les deux fichiers.

## 3. Resultats du controle automatique (passe 1)

| Groupe | N | JSON valide | Compris (`ok`) | Partielle | Echec | Comportement conforme | Mots-cles OK | Tokens sortie (mediane) |
|---|---|---|---|---|---|---|---|---|
| Francais (reference) | 40 | 100 % | 90 % (36/40) | 8 % (3) | 2 % (1) | 82 % (33/40) | 97 % (30/31) | 328 |
| Tunisien (script arabe) | 17 | 100 % | 88 % (15/17) | 12 % (2) | 0 % | 94 % (16/17) | 92 % (12/13) | 424 |
| Arabizi | 24 | 100 % | 88 % (21/24) | 12 % (3) | 0 % | 88 % (21/24) | 83 % (15/18) | 422 |
| Code-switching | 14 | 100 % | 93 % (13/14) | 7 % (1) | 0 % | 79 % (11/14) | 100 % (12/12) | 380 |
| **Dialecte (total)** | 55 | 100 % | 89 % (49/55) | 11 % (6) | 0 % | 87 % (48/55) | 91 % (39/43) | 417 |

Le dialecte produit environ 27 % de tokens de sortie en plus (417 contre 328, medianes). La latence mediane (5,1 s contre 2,8 s) n'est **pas comparable** : les deux campagnes n'ont pas ete lancees au meme moment, donc pas sous la meme charge du fournisseur.

**Comparaison appariee francais / dialecte** (questions avec reponse attendue) :

| Langue | Paires | Les deux OK | Regression (FR ok, dialecte KO) | Gain | Les deux KO |
|---|---|---|---|---|---|
| Tunisien (script arabe) | 13 | 12 | 0 | 0 | 1 |
| Arabizi | 18 | 15 | 2 | 0 | 1 |
| Code-switching | 12 | 12 | 0 | 0 | 0 |
| **Total** | 43 | 39 | 2 | 0 | 2 |

Sur les 41 paires ou le francais est correct, 2 regressent (4,9 %, intervalle de confiance a 95 % d'environ 1 % a 16 %). Les paires ne sont pas independantes (une meme question francaise sert a plusieurs variantes dialectales). **Formulation retenue : aucune degradation marquee observee sur ce jeu de test, sans pouvoir l'exclure.**

**Detection de la langue.** L'ecriture arabe est detectee a 100 % (17/17). L'Arabizi n'est reconnu qu'a 58 % (14/24, 10 classes en `code_switching`) et le code-switching a 64 % (9/14, 5 classes en `arabizi`). Cette confusion tient pour l'essentiel a **notre etiquetage** : une phrase en Arabizi contenant « licence info » ou « cycle ingenieur » releve aussi du code-switching. Elle n'a pas de consequence sur la reponse, toujours donnee en francais. Elle ne doit pas etre lue comme un defaut de comprehension.

### Stabilite entre passes (dialecte, 3 passes, 165 reponses)

| Passe | N | JSON valide | Compris (`ok`) | Partielle | Echec | Mots-cles OK |
|---|---|---|---|---|---|---|
| 1 | 55 | 100 % (55/55) | 89 % (49/55) | 11 % (6/55) | 0 % | 91 % (39/43) |
| 2 | 55 | 98 % (54/55) | 89 % (49/55) | 9 % (5/55) | 0 % | 91 % (39/43) |
| 3 | 55 | 100 % (55/55) | 89 % (49/55) | 11 % (6/55) | 0 % | 86 % (37/43) |

- Taux de comprehension `ok` **identique d'une passe a l'autre (89 %)**, 0 echec de comprehension sur les 165 reponses.
- Par question : comprehension identique sur les 3 passes pour 87 % des questions (47/54), comportement identique pour 81 % (44/54), verdict des mots-cles identique pour 91 % (39/43).
- Les instabilites de comprehension se concentrent sur les **questions vagues ou ambigues** : 6 des 7 questions instables sont `TN-AMB-001` a `006`, la septieme est `TN-ORI-006`. Le modele oscille entre `ok` et `partielle` quand la question est intrinsequement imprecise.
- Une reponse sur 165 (passe 2) n'est pas un JSON exploitable : le backend devra traiter une sortie illisible comme un cas de repli.
- Les verifications sont automatiques ; seule la passe 1 est annotee a la main.

## 4. Annotation manuelle (55 reponses, passe 1)

Grille : intention 0 = fausse, 1 = partielle, 2 = correcte ; justesse 0 / 1 / 2 par rapport a la reponse de reference ; hallucination = information absente du contexte officiel (document, demarche, date, detail invente).

| Langue | N | Intention correcte | Intention fausse | Reponse juste | Hallucination | Reponse en francais |
|---|---|---|---|---|---|---|
| Tunisien (script arabe) | 17 | 100 % (17) | 0 % | 71 % (12) | 29 % (5) | 100 % |
| Arabizi | 24 | 79 % (19) | 8 % (2) | 50 % (12) | 29 % (7) | 100 % |
| Code-switching | 14 | 93 % (13) | 0 % | 64 % (9) | 43 % (6) | 100 % |
| **Total** | 55 | **89 % (49)** | **4 % (2)** | **60 % (33)** | **33 % (18)** | **100 %** |

Taxonomie des erreurs renseignees : hallucination 17, autre 6, polysemie 2.

Les 6 erreurs classees « autre » concernent la **qualite ou le comportement de la reponse**, pas la comprehension de la langue :

| Question | Probleme observe | Famille |
|---|---|---|
| `TN-ADM-003` | La question porte sur la duree ; le modele ajoute le cout a son intention et donne un tarif non demande | Reponse hors sujet (sur-reponse) |
| `TN-ADM-007` | Reponse juste sur le fond (toutes les filieres) mais omet l'etude du dossier scolaire | Reponse incomplete |
| `TN-ORI-006` | Ne repond pas a la question sur le niveau en mathematiques et se concentre sur les sections du bac | Reponse hors sujet |
| `TN-ORI-014` | Presente la licence comme la voie la plus simple au lieu d'une comparaison nuancee de plusieurs parcours | Reponse incomplete / orientee |
| `TN-AMB-001` | « Nheb nsajel » (demande trop vague) : repond par une procedure generique au lieu de demander la formation et l'etablissement | Comportement : aurait du demander une precision |
| `TN-AMB-008` | Ne demande pas dans quel cursus la personne est en troisieme annee ni son projet | Comportement : aurait du demander une precision |


## 5. Analyse des erreurs

### 5.1 Erreurs de comprehension (2/55, toutes en Arabizi)

| Question | Lecture du modele | Sens reel | Constat |
|---|---|---|---|
| `TN-ADM-014` : « 9adech yekhlass el wahed fil cycle ingenieur ? » | Duree du cycle ingenieur (reponse : « 3 ans ») | Combien faut-il payer | Erreur **silencieuse** : `comprehension = ok`, aucun repli declenche |
| `TN-AMB-006` : « 9adech tdoum el licence ? » | Cout de la licence (reponse : 4 800 et 4 200 TND) | Duree de la licence (« tdoum » = « dure », confirme par le locuteur) | Le modele s'est declare en comprehension partielle et a demande de preciser quelle licence, mais avec une intention erronee |

**Les deux erreurs sont reproductibles : l'intention erronee est identique dans les 3 passes.** `TN-ADM-014` est lue comme une question de duree trois fois sur trois, **avec `comprehension = ok` a chaque fois** : le repli n'a donc jamais ete declenche. `TN-AMB-006` est lue comme une question de cout trois fois sur trois ; le modele se declare en comprehension partielle 2 fois sur 3 (`ok` la 3e fois), le signal de repli est donc incoherent d'une passe a l'autre.

Dans les deux cas le mot « 9adech » (combien / quelle duree) est ambigu et le modele a tranche a l'envers selon le verbe. **Limite de notre jeu de test** : la graphie « yekhlass » de `TN-ADM-014` est elle-meme ambigue (elle peut se lire « finit »).

### 5.2 Faux negatifs du controle automatique

- `TN-ADM-007` et `TN-ADM-018` sont juges faux par les mots-cles (« toutes les filieres », « tous les bacheliers » au lieu de « toutes les sections »). Le mot-cle `toutes (les )?sections` est trop etroit. A la lecture, `TN-ADM-018` est correcte et complete ; `TN-ADM-007` est correcte sur le fond mais omet l'etude du dossier scolaire (voir 4).
- Les montants ecrits avec une espace (« 6 500 TND ») echouaient au test `6500`. Corrige dans `analyse_dialecte.py` par normalisation du texte. Le meme controle existe dans `run_eval.py` (champ `verif_auto`) : il peut avoir sous-evalue certains scores de SA-33.

### 5.3 Hallucinations (18/55, 33 %)

- Exemple observe des la premiere reponse (`TN-ADM-001`) : le modele ajoute « CV et lettre de motivation », « formulaire en ligne ou papier », « copies certifiees conformes », absents du contexte, malgre la consigne « n'invente jamais de documents ».
- Elles se concentrent sur les **questions d'orientation** : 9 questions d'orientation sur 14 (`TN-ORI-001`, `002`, `003`, `004`, `008`, `009`, `011`, `012`, `013`), ou le modele elargit son conseil au-dela du contexte.
- Le controle automatique n'en voit **aucune** (0 % de « fausse info ») car il ne cherche que des motifs precis (tarif perime, date inventee). **L'annotation manuelle est indispensable pour ce critere.**
- Le taux d'hallucination sur les reponses francaises equivalentes **n'a pas ete annote** dans cette etude : on ne peut donc pas attribuer ce probleme au dialecte plutot qu'au modele en general (voir recommandation 1).

## 6. Solution de repli

**Mecanisme implemente** (`config/prompt_dialecte.txt`) :

1. Le modele repond en JSON avec `comprehension` = `ok`, `partielle` ou `echec` et une reformulation `intention_comprise` en francais.
2. `ok` : reponse directe.
3. `partielle` : reformulation de ce qui a ete compris, avec demande de confirmation.
4. `echec` : demande polie de reformuler la question en francais.
5. Deux echecs de suite : escalade vers un modele plus puissant (`gpt-oss-120b`), puis vers un conseiller humain (human-in-the-loop du sujet).

**Ce que les donnees montrent :**

- Le JSON est valide a 100 % : le signal est exploitable par le backend.
- Aucune sur-clarification : 0 repli sur les 39 questions claires.
- Inversement, sur des demandes vagues en dialecte (`TN-AMB-001`, `TN-AMB-008`), le modele **repond au lieu de demander une precision** : le comportement « demander_precision » n'est pas fiable (comparaison avec le francais non faite).
- Sur 55 questions, 6 comprehensions partielles et 0 echec : le chemin « demander une reformulation en francais » n'a pas ete mis a l'epreuve.
- Des 2 vraies erreurs de comprehension, le repli en a signale 1 (`TN-AMB-006`, comprehension partielle) et en a **manque 1** (`TN-ADM-014`, erreur silencieuse). Echantillon trop petit pour parler de taux. Sur les 3 passes, l'erreur silencieuse `TN-ADM-014` n'est **jamais** signalee (0/3), et `TN-AMB-006` l'est 2 fois sur 3 : l'auto-evaluation ne fournit pas un signal de repli fiable pour ce type d'erreur.

**Conclusion de conception : l'auto-evaluation du modele ne suffit pas comme declencheur de repli.** Le champ `intention_comprise` est deja produit par le modele sans cout supplementaire. Il faut l'**afficher a l'utilisateur** pour les messages en dialecte (« Si j'ai bien compris, vous demandez le tarif du cycle ingenieur, c'est bien cela ? »), au moins pour les intentions a enjeu (frais, conditions d'admission).

## 7. Limites

- **Seule la passe 1 est annotee manuellement** (55 reponses) ; les passes 2 et 3 sont evaluees automatiquement (stabilite), sans verification manuelle des hallucinations. Plafond `max_tokens` different pour 73 des 165 reponses (voir incident de collecte).
- **Un seul annotateur**, qui est aussi l'auteur des questions : pas d'accord inter-annotateurs, criteres « hallucination » et « intention » en partie subjectifs.
- **Jeu de test non adversarial** : 55 questions propres. En production, l'entree audio passe par Whisper (fautes de transcription, mots coupes, Arabizi tres abrege) : cette difficulte n'est pas couverte.
- Les etiquettes `arabizi` et `code_switching` se chevauchent ; certaines questions sont ambigues par leur graphie.
- Latence non comparable entre campagnes.
- Hallucination non mesuree en francais ; echantillon trop petit pour des intervalles etroits (intervalles calcules a la main).
- Controle automatique de SA-33 (`run_eval.py`) fragile sur les montants et les mots-cles trop etroits.

## 8. Recommandations et perspectives

1. **Reduire les hallucinations** (priorite) : contraindre la reponse au contexte (citer la phrase source), reduire la liberte sur les questions d'orientation, ajouter un controle de coherence apres generation ; mesurer le taux en francais pour isoler l'effet du dialecte.
2. **Afficher la reformulation** (`intention_comprise`) a l'utilisateur pour les messages en dialecte, avant de repondre sur des sujets a enjeu.
3. **Tester le repli en conditions realistes** : jeu de test adversarial (Arabizi tres abrege, fautes, mots inconnus, sorties Whisper degradees, entrees inintelligibles) pour mesurer rappel et precision du repli.
4. **Ajouter un second annotateur** sur un sous-echantillon (accord inter-annotateurs) et annoter l'hallucination sur les passes 2 et 3.
5. **Planifier le quota** : le quota Groq est de 200 000 tokens par jour et par organisation (environ 1 200 tokens par requete d'apres nos mesures, estimation) ; une campagne de 165 requetes plus une de 120 depasse la limite. Prevoir un palier payant ou etaler les campagnes, et ne pas compter sur un changement de cle au sein du meme compte.
6. **Traiter une sortie JSON illisible** comme un cas de repli (1 cas sur 165).
7. **Corriger le controle automatique** de `run_eval.py` (normalisation des montants, mots-cles plus larges) et revoir les scores SA-33 si necessaire.
8. A moyen terme : etape de normalisation Arabizi vers francais avant la reponse, ou adaptation LoRA/QLoRA sur des donnees tunisiennes (voir le sujet du projet).

## 9. Conclusion

`gpt-oss-20b` comprend bien le tunisien ecrit, y compris en Arabizi et en melange avec le francais, sur ce jeu de test propre (89 % d'intentions correctes). Les erreurs de comprehension sont rares mais peuvent etre silencieuses. Le risque principal pour SmartCampus AI est ailleurs : des reponses inexactes ou enrichies d'informations inventees (33 %), que seul un controle humain ou un controle de fond a detecte. La solution de repli est definie et valide sur le plan du format ; son efficacite reste a prouver sur des entrees bruitees.

## Annexe : reproduction

Fichiers : `data/dialecte_source.json` (questions ecrites a la main), `build_dialecte.py` (genere `data/questions_dialecte.json`), `config/prompt_dialecte.txt`, `run_eval.py` (options `--models`, `--max-tokens`, `--prompt-file`, `--reprendre`), `analyse_dialecte.py`, `agreger_annotations.py`, `stabilite_passes.py`.
Resultats : `results/raw_20261121_230609.jsonl` (francais, 3 passes), `results/raw_20261122_151848.jsonl` (dialecte, 3 passes completes), `results/raw_20261122_091219.jsonl` (premiere campagne dialecte, conservee comme trace), `results/dialecte_annote.csv` (annotations de la passe 1).

```bash
python evaluation/llm/build_dialecte.py
python evaluation/llm/run_eval.py --questions evaluation/llm/data/questions_dialecte.json --models openai/gpt-oss-20b --repeats 3 --max-tokens 1500 --pause 1 --prompt-file evaluation/llm/config/prompt_dialecte.txt
python evaluation/llm/analyse_dialecte.py --fr evaluation/llm/results/raw_20261121_230609.jsonl --dialecte evaluation/llm/results/raw_20261122_151848.jsonl --passe 1
python evaluation/llm/agreger_annotations.py evaluation/llm/results/dialecte_annote.csv
python evaluation/llm/stabilite_passes.py evaluation/llm/results/raw_20261122_151848.jsonl
```