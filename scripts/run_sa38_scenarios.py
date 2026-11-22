import datetime
import json
import os
import urllib.request

BASE = "http://localhost:8000/api/v1"


def req(method: str, path: str, token: str | None = None, body: dict | None = None):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if token:
        headers["x-session-token"] = token
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=45) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def main() -> None:
    os.makedirs("docs/tests", exist_ok=True)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# Traces des tests réels — SA-38",
        f"- **Date** : {now}",
        "- **Modèle** : openai/gpt-oss-20b (Groq)",
        "",
    ]

    _, s1 = req("POST", "/sessions")
    t1 = s1["token"]
    _, c1 = req("POST", "/conversations", token=t1, body={"langue": "fr"})
    cid1 = c1["id"]

    scenarios = [
        (
            "S1 - Présentation & contexte",
            "Bonjour, je m'appelle Salma, j'ai eu 15.5 de moyenne au bac et je m'intéresse à l'informatique à Sfax.",
        ),
        (
            "S2 - Conservation du contexte",
            "Peux-tu me rappeler mon prénom, ma moyenne et la filière qui m'intéresse ?",
        ),
        (
            "S3 - Question ambiguë",
            "C'est combien ?",
        ),
        (
            "S4/S5 - Info non vérifiable / hors périmètre",
            "Quel sera le taux exact d'admission en master de robotique en 2029 à l'IIT ?",
        ),
    ]

    for titre, question in scenarios:
        st, out = req(
            "POST",
            f"/conversations/{cid1}/chat",
            token=t1,
            body={"contenu": question, "langue": "fr"},
        )
        reponse = out["reponse"]["contenu"]
        duree = out.get("duree_ms")
        print(f"[{titre}] HTTP {st} ({duree} ms)")
        lines.extend(
            [
                f"## {titre}",
                f"- **Statut HTTP** : `{st}` (`{duree} ms`)",
                f"- **Question** : {question}",
                f"- **Réponse** : {reponse}",
                "",
            ]
        )

    st_mem, mem = req("GET", f"/conversations/{cid1}/memoire", token=t1)
    lines.extend(
        [
            "## Vérification mémoire (SA-37)",
            f"- **Statut HTTP** : `{st_mem}`",
            "```json",
            json.dumps(mem, ensure_ascii=False, indent=2),
            "```",
            "",
        ]
    )

    _, s2 = req("POST", "/sessions")
    t2 = s2["token"]
    _, c2 = req("POST", "/conversations", token=t2, body={"langue": "fr"})
    cid2 = c2["id"]
    st2, out2 = req(
        "POST",
        f"/conversations/{cid2}/chat",
        token=t2,
        body={"contenu": "Quel est mon prénom ?", "langue": "fr"},
    )
    rep2 = out2["reponse"]["contenu"]
    duree2 = out2.get("duree_ms")
    print(f"[S6 - Isolation entre sessions] HTTP {st2} ({duree2} ms)")
    lines.extend(
        [
            "## S6 - Isolation entre sessions",
            f"- **Statut HTTP** : `{st2}` (`{duree2} ms`)",
            "- **Question (Session B)** : Quel est mon prénom ?",
            f"- **Réponse** : {rep2}",
            "",
        ]
    )

    out_path = os.path.join("docs", "tests", "SA-38_traces_reelles.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Fichier généré : {out_path}")


if __name__ == "__main__":
    main()