# Analyse SA-34 - passe 1

Fichiers : FR `raw_20261121_230609.jsonl` (40 reponses, 0 echecs API ignores) ; dialecte `raw_20261122_091219.jsonl` (55 reponses, 0 echecs API ignores).

### Resultats par groupe

| Groupe | N | JSON valide | Compris (ok) | Partielle | Echec | Comportement conforme | Mots-cles OK | Fausse info | Repli sur q. claire | Latence med. (ms) | Tokens sortie med. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| FR (40 q., reference) | 40 | 100% (40/40) | 90% (36/40) | 8% (3/40) | 2% (1/40) | 82% (33/40) | 97% (30/31) | 0% (0/40) | 0% (0/28) | 2765 | 328 |
| tn_arabe | 17 | 100% (17/17) | 88% (15/17) | 12% (2/17) | 0% (0/17) | 94% (16/17) | 92% (12/13) | 0% (0/17) | 0% (0/12) | 5897 | 424 |
| arabizi | 24 | 100% (24/24) | 88% (21/24) | 12% (3/24) | 0% (0/24) | 88% (21/24) | 83% (15/18) | 0% (0/24) | 0% (0/17) | 3797 | 422 |
| code_switching | 14 | 100% (14/14) | 93% (13/14) | 7% (1/14) | 0% (0/14) | 79% (11/14) | 100% (12/12) | 0% (0/14) | 0% (0/10) | 6118 | 380 |
| Dialecte (toutes) | 55 | 100% (55/55) | 89% (49/55) | 11% (6/55) | 0% (0/55) | 87% (48/55) | 91% (39/43) | 0% (0/55) | 0% (0/39) | 5110 | 417 |

### Detection de la langue (verite terrain = champ `langue` du jeu de test)

| Langue reelle | N | Detectee correctement | Confusions (detectee -> nb) |
|---|---|---|---|
| tn_arabe | 17 | 100% (17/17) | - |
| arabizi | 24 | 58% (14/24) | {'code_switching': 10} |
| code_switching | 14 | 64% (9/14) | {'arabizi': 5} |

### Comparaison appariee francais vs dialecte (mots-cles, questions avec reponse attendue)

| Langue | Paires | Les deux OK | Regression (FR ok, dialecte KO) | Gain (FR KO, dialecte ok) | Les deux KO |
|---|---|---|---|---|---|
| tn_arabe | 13 | 12 | 0 | 0 | 1 |
| arabizi | 18 | 15 | 2 | 0 | 1 |
| code_switching | 12 | 12 | 0 | 0 | 0 |
| toutes | 43 | 39 | 2 | 0 | 2 |

- Regressions (a lire en priorite) : TN-AMB-006, TN-ADM-014
- Les deux KO (verifier si le controle automatique se trompe) : TN-ADM-007, TN-ADM-018

### Qualite du repli (proxy automatique, a affiner par l'annotation manuelle)

- Questions evaluees : 43 ; reponses jugees mauvaises (mots-cles absents) : 4
- Repli declenche : 1
- **Rappel** du repli (mauvaises reponses detectees) : 25% (1/4)
- **Precision** du repli (repli justifie par une mauvaise reponse) : 100% (1/1)
- Mauvaises reponses SANS repli (faux negatifs, cas dangereux) : 3 -> TN-ADM-007, TN-ADM-014, TN-ADM-018
