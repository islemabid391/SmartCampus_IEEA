# Test de stress du repli - raw_20261122_204900.jsonl

13 reponses valides (6 groupe A, 7 groupe B).

## Resume

- **Groupe A** (bruite, comprehensible) : reponse correcte 83% (5/6) ; sur-clarification 17% (1/6)
- **Groupe B** (sans demande exploitable) : repli adequat 86% (6/7) ; fausse certitude 14% (1/7) ; chiffre invente 0% (0/7)
- Groupe B, `comportement = demander_reformulation` exact : 29% (2/7) ; reponse qui demande explicitement de reformuler : 0% (0/7)
- JSON valide : 100% (13/13)

## Detail par question

| ID | Langue | Question | Comprehension | Comportement | Verdict | Intention comprise | Debut de reponse |
|---|---|---|---|---|---|---|---|
| STR-A-01 | arabizi | 9adech licence info | ok | repondre | correcte | Vous demandez le coût de la licence en Informatique. | Le coût de la licence en Informatique pour l’année universitaire 2026‑2027 est de 4 800 TND, payable en trois... |
| STR-A-02 | arabizi | chnouwa chorout el 9bol fel prepa mta3 i i t | partielle | demander_precision | reponse fausse + repli inutile | Vous souhaitez connaître le programme de la 9e année de la prépa de l... | Si j'ai bien compris, vous souhaitez savoir quel est le contenu ou le parcours de la 9e année dans le cycle p... |
| STR-A-03 | arabizi | kadech el moyenne el mtlouba bech nod5el pre... | ok | repondre | correcte | Vous demandez quelle moyenne minimale est requise pour être admis en ... | La moyenne générale minimale au baccalauréat pour être admis en cycle préparatoire intégré (IIT) est de 12/20. |
| STR-A-04 | code_switching | frais cycle ing combien | ok | repondre | correcte | Demander le montant des frais du cycle ingénieur en informatique | Les frais du cycle ingénieur en informatique pour l’année 2026‑2027 s’élèvent à 6 500 TND, répartis en quatre... |
| STR-A-05 | tn_arabe | قداش معلوم الاجازة اعلامية | ok | repondre | correcte | Le candidat souhaite connaître le montant des frais de scolarité pour... | Les frais de scolarité pour la Licence en Informatique 2026-2027 s'élèvent à 4 800 TND, payables en trois tra... |
| STR-A-06 | arabizi | salut nheb na3ref kifech nod5ol lel cycle in... | ok | repondre | correcte | Il souhaite savoir comment intégrer le cycle ingénieur après avoir ob... | Pour intégrer le cycle ingénieur en informatique à l'IIT, vous devez d’abord valider votre licence en informa... |
| STR-B-01 | arabizi | mta3 el 9sdkh tnw wlh 3al bch | partielle | demander_reformulation | repli adequat | Vous cherchez à obtenir des informations sur la procédure et le coût ... | Si j'ai bien compris, vous souhaitez connaître les informations relatives à la procédure et au coût d'un exam... |
| STR-B-02 | arabizi | hhhh 3ayech ?? lol | partielle | demander_precision | repli adequat | Demande de salutations ou question informelle | Bonjour, je suis là pour vous aider. Pouvez-vous préciser votre demande s'il vous plaît? |
| STR-B-03 | arabizi | nheb na3rf 3la el licen | ok | reconnaitre_limite | repli adequat | Il souhaite obtenir des informations sur la licence. | Je suis désolé, mais je n'ai pas d'information officielle concernant la licence. Vous pouvez contacter le ser... |
| STR-B-04 | tn_arabe | شنو ؟؟ كيما ذاك الي قال لي خوي | partielle | demander_reformulation | repli adequat | Vous demandez des informations sur un sujet que votre frère vous a me... | Bonjour, je ne suis pas sûr de bien comprendre votre demande. Pourriez‑vous préciser de quel sujet ou de quel... |
| STR-B-05 | arabizi | ya3ni houwa kif haka wala chnou | ok | repondre | FAUSSE CERTITUDE | Vous demandez si quelque chose est fait de cette façon ou d'une autre... | Je suis désolé, mais je n'ai pas d'information officielle à ce sujet. |
| STR-B-06 | tn_arabe | اي و بعد شنو صار متاع هاكا | ok | reconnaitre_limite | repli adequat | Vous souhaitez savoir ce qui s'est passé après cet événement. | Je suis désolé, mais je ne dispose pas d'informations officielles concernant cette question. |
| STR-B-07 | arabizi | 5ouya 9alli eli heya mouch kif mte3 9bal | partielle | demander_precision | repli adequat | Vous souhaitez connaître la différence entre un élément et le précéde... | Je suis désolé, mais je ne dispose pas d'informations officielles sur ce sujet. Pourriez‑vous préciser de que... |

Limite : 13 questions, 1 passe, 1 annotateur ; les verdicts sont automatiques et doivent etre relus a la main.