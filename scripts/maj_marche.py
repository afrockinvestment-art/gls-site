"""Met à jour data/marche.json (cours BRVM) et data/devises.json (taux BCEAO).

Lancé chaque soir de séance par .github/workflows/marche.yml.
En local : pip install requests beautifulsoup4 && python scripts/maj_marche.py

Si une source change de présentation ou ne répond pas, le script garde
le fichier précédent et s'arrête sans rien casser.
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

RACINE = Path(__file__).resolve().parent.parent
DATA = RACINE / "data"
UA = {"User-Agent": "Mozilla/5.0 (GLS market snapshot)"}

URL_ACTIONS = "https://www.brvm.org/fr/cours-actions/0"
URL_INDICES = "https://www.brvm.org/fr/indices"
URL_BCEAO = "https://www.bceao.int/fr/cours/cours-de-reference-des-principales-devises-contre-Franc-CFA"


def nombre(txt):
    """'12 260' -> 12260.0 ; '-3,85 %' -> -3.85 ; '' -> None"""
    t = re.sub(r"[^\d,.\-+]", "", (txt or "").replace("\xa0", "").replace(" ", ""))
    if not t or t in "-+":
        return None
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def tables(url):
    r = requests.get(url, headers=UA, timeout=30)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser").find_all("table")


def colonnes(table):
    entete = table.find("tr")
    return [c.get_text(" ", strip=True).lower() for c in entete.find_all(["th", "td"])]


def lignes(table):
    for tr in table.find_all("tr")[1:]:
        cells = [c.get_text(" ", strip=True) for c in tr.find_all("td")]
        if cells:
            yield cells


def index_de(cols, *mots):
    for i, c in enumerate(cols):
        if all(m in c for m in mots):
            return i
    return None


def actions():
    for t in tables(URL_ACTIONS):
        cols = colonnes(t)
        i_s, i_n = index_de(cols, "symbole"), index_de(cols, "nom")
        i_c, i_v = index_de(cols, "cl"), index_de(cols, "variation")
        if None in (i_s, i_n, i_c, i_v):
            continue
        out = []
        for c in lignes(t):
            if len(c) <= max(i_s, i_n, i_c, i_v):
                continue
            prix = nombre(c[i_c])
            if prix is None:
                continue
            out.append({"s": c[i_s], "n": c[i_n].title(), "c": prix, "v": nombre(c[i_v])})
        if len(out) > 20:
            return out
    raise RuntimeError("tableau des actions introuvable sur brvm.org")


def indices():
    voulus = {"brvm composite": "BRVM Composite", "brvm 30": "BRVM 30",
              "brvm prestige": "BRVM Prestige", "brvm principal": "BRVM Principal"}
    out = []
    for t in tables(URL_INDICES):
        for c in lignes(t):
            nom = c[0].lower().replace("-", " ").strip()
            if nom in voulus and len(c) >= 3:
                valeurs = [nombre(x) for x in c[1:]]
                valeurs = [x for x in valeurs if x is not None]
                if len(valeurs) >= 2:
                    out.append({"n": voulus[nom], "c": valeurs[-2], "v": valeurs[-1]})
    return out


def devises():
    codes = {"euro": ("EUR", "Euro"), "dollar us": ("USD", "Dollar US"), "yen japonais": ("JPY", "Yen japonais"),
             "yuan chinois": ("CNY", "Yuan chinois"), "livre sterling": ("GBP", "Livre sterling"),
             "franc suisse": ("CHF", "Franc suisse")}
    taux = []
    for t in tables(URL_BCEAO):
        for c in lignes(t):
            cle = c[0].lower().strip()
            if cle in codes and len(c) > 1:
                code, nom = codes[cle]
                taux.append({"code": code, "n": nom, "fcfa": nombre(c[1])})
    if len(taux) < 4:
        raise RuntimeError("cours BCEAO introuvables")
    taux.append({"code": "RUB", "n": "Rouble russe", "fcfa": None})
    return taux


def main():
    aujourd_hui = datetime.now(timezone.utc).date().isoformat()
    ok = True

    fichier = DATA / "marche.json"
    ancien = json.loads(fichier.read_text(encoding="utf-8"))
    try:
        nouv = dict(ancien)
        nouv["actions"] = actions()
        idx = indices()
        if idx:
            nouv["indices"] = idx
        nouv.update({"seance": aujourd_hui, "statut": "clôture", "source": "BRVM (brvm.org)"})
        fichier.write_text(json.dumps(nouv, ensure_ascii=False, indent=1), encoding="utf-8")
        print("marche.json :", len(nouv["actions"]), "actions")
    except Exception as e:  # on garde l'ancien fichier
        ok = False
        print("BRVM non mise à jour :", e, file=sys.stderr)

    try:
        d = {"date": aujourd_hui, "source": "BCEAO, cours de référence", "taux": devises()}
        (DATA / "devises.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        print("devises.json :", len(d["taux"]), "devises")
    except Exception as e:
        ok = False
        print("Devises non mises à jour :", e, file=sys.stderr)

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
