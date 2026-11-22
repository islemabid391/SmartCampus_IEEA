# Traces des tests réels — SA-38
- **Date** : 2026-11-22 23:25
- **Modèle** : openai/gpt-oss-20b (Groq)

## S1 - Présentation & contexte
- **Statut HTTP** : `200` (`846 ms`)
- **Question** : Bonjour, je m'appelle Salma, j'ai eu 15.5 de moyenne au bac et je m'intéresse à l'informatique à Sfax.
- **Réponse** : Bonjour Salma,

Merci pour ces informations.  
Pour pouvoir vous orienter au mieux, pourriez‑vous préciser :

1. **Quel établissement vous intéresse ?** (IIT, ISA ou ISB à Sfax)  
2. **Quel niveau souhaitez‑vous atteindre ?** (Licence, Master, etc.)  
3. **Quel type de baccalauréat avez‑vous obtenu ?** (scientifique, économique, littéraire, etc.)

Avec ces précisions, je pourrai vous donner des conseils d’orientation adaptés à votre situation.

## S2 - Conservation du contexte
- **Statut HTTP** : `200` (`681 ms`)
- **Question** : Peux-tu me rappeler mon prénom, ma moyenne et la filière qui m'intéresse ?
- **Réponse** : Bonjour Salma,

Vous avez mentionné que vous avez obtenu une moyenne de 15,5 au baccalauréat et que vous vous intéressez à l’informatique à Sfax.  

Si vous avez besoin d’aide pour choisir l’établissement (IIT, ISA ou ISB) ou pour connaître les démarches d’inscription, n’hésitez pas à me le dire !

## S3 - Question ambiguë
- **Statut HTTP** : `200` (`552 ms`)
- **Question** : C'est combien ?
- **Réponse** : Je n’ai pas d’information officielle sur le montant, la durée ou tout autre détail administratif concernant les programmes d’informatique à Sfax.  
Je vous invite à contacter directement l’administration de l’IIT, de l’ISA ou de l’ISB pour obtenir ces renseignements.  

En attendant, si vous avez besoin d’aide pour comparer les parcours ou pour préparer votre dossier de candidature, je suis là pour vous accompagner.

## S4/S5 - Info non vérifiable / hors périmètre
- **Statut HTTP** : `200` (`589 ms`)
- **Question** : Quel sera le taux exact d'admission en master de robotique en 2029 à l'IIT ?
- **Réponse** : Je n’ai pas d’information officielle sur le taux d’admission en master de robotique à l’IIT pour l’année 2029.  
Je vous conseille de contacter directement l’administration de l’IIT pour obtenir cette donnée.  

En attendant, je peux vous aider à préparer votre dossier ou à comparer les programmes de master en robotique si vous le souhaitez.

## Vérification mémoire (SA-37)
- **Statut HTTP** : `200`
```json
{
  "informations": {},
  "infos_manquantes": [
    "niveau_scolaire",
    "section_bac",
    "objectif_professionnel",
    "contraintes",
    "moyenne",
    "matieres_preferees",
    "centres_interet"
  ]
}
```

## S6 - Isolation entre sessions
- **Statut HTTP** : `200` (`621 ms`)
- **Question (Session B)** : Quel est mon prénom ?
- **Réponse** : Je ne dispose pas de votre prénom. Pourriez‑vous me le communiquer ?
