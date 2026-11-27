#!/usr/bin/env python3
"""SA-18 - Collecte (crawl) puis extraction des pages de formations des sites des établissements.

Depuis le dossier backend/ :
    python -m scripts.scrape.scrape crawl                 # télécharge et met en cache les pages
    python -m scripts.scrape.scrape crawl --only IIT --refresh
    python -m scripts.scrape.scrape extract               # produit seed/real/extracted.json

Le crawl est « poli » : robots.txt respecté, délai entre requêtes, cache local (on ne retélécharge pas).
"""
import argparse
import hashlib
import json
import re
import sys
import time
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
import yaml
from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
REAL = HERE.parent.parent / "seed" / "real"
RAW = REAL / "raw"
INDEX = RAW / "index.jsonl"
EXTRACTED = REAL / "extracted.json"

NOISE = re.compile(r"Objectively innovate|Proactively envisioned|Phosfluorescently|Collaboratively administrate|"
                   r"Efficiently unleash|Completely synergize|Holisticly predominate|lorem ipsum", re.I)
STOP_SECTIONS = re.compile(r"satisfactions? des étudiants|réseaux sociaux|nos clubs|collaborateurs|retours? de|"
                           r"méthodologie|contact|newsletter", re.I)
ORGA = re.compile(r"organisation du diplôme|programme|plan d.études|matières|modules|maquette", re.I)
DEBOUCHES = re.compile(r"débouchés|perspectives|carrières|opportunités professionnelles", re.I)
ADMISSION = re.compile(r"conditions? d.admission|admission|prérequis|accès", re.I)


# ----------------------------------------------------------------------------- utilitaires
def slugify(text, maxlen=60):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:maxlen] or "page"


def norm_space(s):
    return re.sub(r"\s+", " ", s.replace("\u00a0", " ").replace("\u202f", " ")).strip()


def load_sources(path=None):
    return yaml.safe_load(Path(path or HERE / "sources.yaml").read_text(encoding="utf-8"))


def read_index():
    if not INDEX.exists():
        return {}
    out = {}
    for line in INDEX.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rec = json.loads(line)
            out[rec["url"]] = rec
    return out


def write_index(index):
    RAW.mkdir(parents=True, exist_ok=True)
    INDEX.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in index.values()), encoding="utf-8")


# ----------------------------------------------------------------------------- crawl
def load_robots(client, base_url, ua):
    rp = RobotFileParser()
    try:
        r = client.get(base_url.rstrip("/") + "/robots.txt")
    except httpx.HTTPError as e:
        sys.exit(f"Impossible de lire robots.txt de {base_url} : {e!r}. Arrêt par précaution.")
    if r.status_code == 200:
        rp.parse(r.text.splitlines())
    else:                                   # pas de robots.txt (404...) : tout est autorisé
        rp.parse([])
    return rp


def crawl_site(code, cfg, g, client, index, refresh, max_pages):
    ua, delay = g["user_agent"], g["delay_s"]
    host = urlparse(cfg["base_url"]).netloc
    rp = load_robots(client, cfg["base_url"], ua)
    inc, exc = cfg.get("include_patterns", []), cfg.get("exclude_patterns", [])
    queue = [(u, 0) for u in cfg.get("start_urls", [])]
    seen, fetched = set(), 0
    while queue and len(seen) < max_pages:
        url, depth = queue.pop(0)
        url = urldefrag(url)[0]
        if url in seen:
            continue
        seen.add(url)
        if not rp.can_fetch(ua, url):
            print(f"  [robots.txt] interdit : {url}")
            continue
        rec = index.get(url)
        html = None
        if rec and rec.get("status") == 200 and not refresh and rec.get("file") and (RAW / rec["file"]).exists():
            print(f"  [cache] {url}")
            if rec["file"].endswith(".html"):
                html = (RAW / rec["file"]).read_text(encoding="utf-8", errors="replace")
        else:
            time.sleep(delay)
            try:
                r = client.get(url)
            except httpx.HTTPError as e:
                print(f"  [erreur] {url} : {e!r}")
                index[url] = {"etab": code, "url": url, "status": None, "erreur": repr(e)[:200],
                              "date": datetime.now(timezone.utc).isoformat()}
                continue
            fetched += 1
            ctype = r.headers.get("content-type", "")
            rec = {"etab": code, "url": url, "final_url": str(r.url), "status": r.status_code,
                   "content_type": ctype, "date": datetime.now(timezone.utc).isoformat()}
            if r.status_code == 200:
                ext = ".pdf" if "pdf" in ctype else ".html" if "html" in ctype else None
                if ext:
                    body = r.content
                    rec["sha256"] = hashlib.sha256(body).hexdigest()
                    name = f"{code}__{slugify(urlparse(str(r.url)).path)}__{rec['sha256'][:8]}{ext}"
                    RAW.mkdir(parents=True, exist_ok=True)
                    (RAW / name).write_bytes(body)
                    rec["file"] = name
                    if ext == ".html":
                        html = body.decode(r.encoding or "utf-8", errors="replace")
            print(f"  [{r.status_code}] {url}")
            index[url] = rec
        if html and depth < g.get("max_depth", 0):
            for a in BeautifulSoup(html, "lxml").find_all("a", href=True):
                link = urldefrag(urljoin(url, a["href"]))[0]
                p = urlparse(link)
                if p.netloc != host or link in seen:
                    continue
                if any(x in link for x in exc) or (inc and not any(x in link for x in inc)):
                    continue
                queue.append((link, depth + 1))
    return fetched


def cmd_crawl(args):
    g = load_sources(args.sources)
    index = read_index()
    headers = {"User-Agent": g["user_agent"], "Accept-Language": "fr,en;q=0.7"}
    with httpx.Client(headers=headers, timeout=g.get("timeout_s", 25), follow_redirects=True) as client:
        for code, cfg in g["etablissements"].items():
            if args.only and code not in args.only.split(","):
                continue
            if not cfg.get("start_urls"):
                print(f"{code} : aucune URL de départ (à compléter dans sources.yaml).")
                continue
            print(f"== {code} ({cfg['base_url']})")
            crawl_site(code, cfg, g, client, index, args.refresh, args.max_pages or g.get("max_pages_per_site", 60))
            write_index(index)
    print(f"Index : {INDEX}")


# ----------------------------------------------------------------------------- extraction
def num(s):
    s = s.replace(" ", "").replace("\u202f", "")
    if re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")
    return float(s.replace(",", "."))


def parse_frais(text):
    tnd = re.search(r"(\d[\d\s.,]*)\s*(?:DT|TND|dinars?)", text, re.I)
    eur = re.search(r"(\d[\d\s.,]*)\s*(?:€|EUR|euros?)", text, re.I)
    return {"brut": text, "tnd": num(tnd.group(1)) if tnd else None, "eur": num(eur.group(1)) if eur else None}


def clean_soup(soup):
    for tag in soup(["head", "script", "style", "noscript", "nav", "footer", "header", "form", "iframe", "svg", "button"]):
        tag.decompose()
    for node in soup.find_all(string=NOISE):             # blocs de témoignages génériques (texte factice)
        container = node.find_parent("section") or node.find_parent("div")
        if container is not None:
            txt = container.get_text(" ")
            if len(txt) < 6000 and not re.search(r"Frais de scolarité|Organisation du diplôme", txt):
                container.decompose()


def page_lines(soup):
    for t in soup.find_all(["b", "strong", "i", "em", "span", "a", "u", "small", "mark", "font"]):
        t.unwrap()                                        # évite de couper « Organisation <b>du diplôme</b> »
    soup.smooth()
    for h in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        h.insert(0, f"\n§§{h.name}§§ ")
        h.append("\n")
    soup.smooth()                                         # fusionne le marqueur avec le texte du titre
    lines = [norm_space(l) for l in soup.get_text("\n").splitlines()]
    return [l for l in lines if l]


def split_sections(lines):
    sections, title, buf = [], "_intro", []
    for l in lines:
        m = re.match(r"^§§h(\d)§§\s*(.*)$", l)
        if m:
            sections.append((title, buf))
            title, buf = norm_space(m.group(2)), []
        else:
            buf.append(l)
    sections.append((title, buf))
    return [(t, b) for t, b in sections if t != "_intro" or b]


def value_after(lines, label_re, n=1):
    for i, l in enumerate(lines):
        if re.match(label_re, l, re.I):
            rest = re.sub(label_re + r"\s*:?\s*", "", l, flags=re.I).strip()
            vals = ([rest] if rest else []) + lines[i + 1:i + 1 + n]
            return [v for v in vals if not v.startswith("§§")][:n] or None
    return None


def is_module(line):
    if line.startswith("§§"):
        return False
    return bool(re.match(r"^[♦•▪●\-–*]\s*", line) or re.match(r"^[A-Z]{1,4}\s?\d+\s*[:\-]", line)
                or (len(line) < 70 and not line.endswith(".")))


def clean_module(line):
    line = re.sub(r"^[♦•▪●\-–*]\s*", "", line)
    return norm_space(re.sub(r"^[A-Z]{1,4}\s?\d+\s*[:\-]\s*", "", line))


def extract_page(rec, html):
    soup = BeautifulSoup(html, "lxml")
    alertes = []
    og = soup.find("meta", property="og:title")
    titre = norm_space(og["content"]) if og and og.get("content") else None
    if not titre:
        h1 = soup.find("h1")
        titre = norm_space(h1.get_text()) if h1 else norm_space((soup.title.string or "").split("|")[0])
    emails = set(re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", soup.get_text(" ")))
    ext_emails = {e for e in emails if not re.search(r"@(iit|nau|isb|isa)\.tn$", e, re.I)}
    if ext_emails:
        alertes.append("adresses e-mail non institutionnelles présentes sur la page (modèle de site ?) : ignorées")
    clean_soup(soup)
    lines = page_lines(soup)
    sections = split_sections(lines)
    flat = [l for l in lines if not l.startswith("§§")]

    duree = None
    for l in flat:
        m = re.search(r"(\d+)\s*ans?\b", l, re.I)
        if m and ("🕙" in l or re.search(r"dur[ée]e", l, re.I) or len(l) < 25):
            duree = int(m.group(1))
            break
    frais_v = value_after(flat, r"frais de scolarité", 1)
    frais = parse_frais(frais_v[0]) if frais_v else None
    if frais and (frais["tnd"] or frais["eur"]):
        alertes.append("frais : période couverte (par an ou pour tout le cycle) non précisée, à vérifier")
    elif frais_v:
        alertes.append(f"frais non interprétables : {frais_v[0]!r}")
        frais = None

    intro = next((l for l in flat if len(l) >= 80 and not NOISE.search(l)), None)
    acces = None
    m = re.search(r"Accessible à partir d[^.]+\.", " ".join(flat))
    if m:
        acces = norm_space(m.group(0))
    for t, b in sections:
        if ADMISSION.search(t) and b and not acces:
            acces = " ".join(b)[:600]
    debouches = next((" ".join(b)[:800] for t, b in sections if DEBOUCHES.search(t) and b), None)

    groupes, started = [], False
    for t, b in sections:
        if ORGA.search(t) and not started:
            started = True
            mods = [clean_module(l) for l in b if is_module(l) and len(l) < 70]
            if mods:
                groupes.append({"nom": t, "modules": mods})
            continue
        if started:
            if STOP_SECTIONS.search(t):
                break
            mods = [clean_module(l) for l in b if is_module(l)]
            if mods:
                groupes.append({"nom": t, "modules": mods})
    if any(re.match(r"^[♦•▪●\-–*]?\s*[A-Z]{1,4}\s?\d+\s*[:\-]", l) for t, b in sections for l in b if is_module(l)):
        alertes.append("préfixes de type « GM 2 : » retirés des intitulés de modules (numérotation source incohérente ?)")
    if len(groupes) > 1 and len({tuple(g["modules"]) for g in groupes}) == 1:
        alertes.append("les listes de modules sont identiques pour tous les groupes (copier-coller probable sur le site)")

    return {
        "url": rec["url"], "url_finale": rec.get("final_url", rec["url"]), "etab": rec["etab"], "titre": titre,
        "date_collecte": rec["date"][:10], "sha256": rec.get("sha256"),
        "type": "formation" if (duree or frais or groupes) else "autre",
        "intro": intro, "duree_annees": duree, "frais": frais, "acces": acces, "debouches": debouches,
        "groupes_modules": groupes, "sections": [t for t, _ in sections if t != "_intro"][:20], "alertes": alertes,
    }


def cmd_extract(args):
    index = read_index()
    out, seen_final = [], set()
    for rec in index.values():
        if rec.get("status") != 200 or not str(rec.get("file", "")).endswith(".html"):
            continue
        final = rec.get("final_url", rec["url"])
        if final in seen_final:                       # deux URLs qui redirigent vers la même page
            continue
        seen_final.add(final)
        html = (RAW / rec["file"]).read_text(encoding="utf-8", errors="replace")
        out.append(extract_page(rec, html))
    REAL.mkdir(parents=True, exist_ok=True)
    EXTRACTED.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    n_f = sum(1 for p in out if p["type"] == "formation")
    print(f"{len(out)} pages analysées, {n_f} ressemblent à des formations -> {EXTRACTED}")
    for p in out:
        flag = "FORMATION" if p["type"] == "formation" else "autre    "
        print(f"  {flag} {p['titre']!r:45} durée={p['duree_annees']} frais={(p['frais'] or {}).get('tnd')} "
              f"groupes={len(p['groupes_modules'])} alertes={len(p['alertes'])}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sources", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("crawl")
    c.add_argument("--only")
    c.add_argument("--refresh", action="store_true")
    c.add_argument("--max-pages", type=int)
    sub.add_parser("extract")
    args = ap.parse_args()
    {"crawl": cmd_crawl, "extract": cmd_extract}[args.cmd](args)


if __name__ == "__main__":
    main()
