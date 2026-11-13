#!/usr/bin/env python3
"""
audit_dmarc.py — Audit DMARC d'une liste de domaines.

Usage :
    python3 audit_dmarc.py domaines.txt

domaines.txt : un domaine par ligne (les lignes vides et celles
commençant par # sont ignorées). Les préfixes http(s):// et www.
sont retirés automatiquement.

Sortie :
    - un résumé dans le terminal (aucun DMARC / p=none / quarantine / reject)
    - un fichier resultats_dmarc.csv avec le détail par domaine

Dépendance : dnspython  (pip install dnspython)
"""

import csv
import sys
from collections import Counter

import dns.resolver

CATEGORIES = [
    "aucun DMARC",
    "p=none",
    "p=quarantine",
    "p=reject",
    "invalide",
    "erreur DNS",
]


def normaliser(ligne: str) -> str:
    d = ligne.strip().lower()
    for prefixe in ("https://", "http://"):
        if d.startswith(prefixe):
            d = d[len(prefixe):]
    d = d.split("/")[0]
    if d.startswith("www."):
        d = d[4:]
    return d


def parser_tags(enregistrement: str) -> dict:
    tags = {}
    for morceau in enregistrement.split(";"):
        if "=" in morceau:
            cle, valeur = morceau.split("=", 1)
            tags[cle.strip().lower()] = valeur.strip()
    return tags


def auditer(domaine: str, resolver: dns.resolver.Resolver) -> dict:
    res = {
        "domaine": domaine,
        "categorie": "",
        "p": "",
        "sp": "",
        "pct": "",
        "rua": "",
        "enregistrement": "",
    }
    try:
        reponse = resolver.resolve(f"_dmarc.{domaine}", "TXT")
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        res["categorie"] = "aucun DMARC"
        return res
    except Exception as e:  # timeout, SERVFAIL, etc.
        res["categorie"] = "erreur DNS"
        res["enregistrement"] = type(e).__name__
        return res

    # Un TXT peut être découpé en plusieurs chaînes : on les recolle.
    textes = [b"".join(r.strings).decode("utf-8", "replace") for r in reponse]
    dmarc = [t for t in textes if t.strip().lower().startswith("v=dmarc1")]

    if not dmarc:
        res["categorie"] = "aucun DMARC"
        return res
    if len(dmarc) > 1:
        # La RFC impose un seul enregistrement : plusieurs = DMARC ignoré.
        res["categorie"] = "invalide"
        res["enregistrement"] = " | ".join(dmarc)
        return res

    enr = dmarc[0]
    tags = parser_tags(enr)
    p = tags.get("p", "").lower()
    res.update(
        enregistrement=enr,
        p=p,
        sp=tags.get("sp", ""),
        pct=tags.get("pct", ""),
        rua=tags.get("rua", ""),
    )
    res["categorie"] = f"p={p}" if p in ("none", "quarantine", "reject") else "invalide"
    return res


def main():
    if len(sys.argv) != 2:
        print("Usage : python3 audit_dmarc.py domaines.txt")
        sys.exit(1)

    with open(sys.argv[1], encoding="utf-8") as f:
        domaines = [
            normaliser(l) for l in f
            if l.strip() and not l.strip().startswith("#")
        ]
    domaines = list(dict.fromkeys(domaines))  # dédoublonnage, ordre conservé

    resolver = dns.resolver.Resolver()
    resolver.timeout = 3
    resolver.lifetime = 6

    resultats = []
    for i, d in enumerate(domaines, 1):
        r = auditer(d, resolver)
        resultats.append(r)
        print(f"[{i:>3}/{len(domaines)}] {d:<35} {r['categorie']}")

    with open("resultats_dmarc.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(resultats[0].keys()) if resultats else ["domaine"])
        w.writeheader()
        w.writerows(resultats)

    total = len(resultats)
    compte = Counter(r["categorie"] for r in resultats)
    print("\n===== Résumé =====")
    for c in CATEGORIES:
        n = compte.get(c, 0)
        if n or c in ("aucun DMARC", "p=none", "p=quarantine", "p=reject"):
            pourcent = (100 * n / total) if total else 0
            print(f"{c:<14} {n:>4}  ({pourcent:.0f} %)")
    sans_rua = sum(1 for r in resultats if r["p"] and not r["rua"])
    pct_partiel = sum(1 for r in resultats if r["pct"] and r["pct"] != "100")
    print(f"\nDMARC sans rapports (rua absent) : {sans_rua}")
    print(f"DMARC appliqué partiellement (pct < 100) : {pct_partiel}")
    print("\nDétail : resultats_dmarc.csv")


if __name__ == "__main__":
    main()
