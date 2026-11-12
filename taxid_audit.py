#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# taxid_audit.py - check every NCBI Taxonomy ID (txid) that MeSH attaches to a concept against
# the names NCBI Taxonomy itself gives that ID. Pre-registered as PREREG-TAXID-1.
# MV2, Munim, Inc., mv2@munimtech.com. Made with AI agents working in MV2's name.
#
# Standard library only. Sources: NLM MeSH SPARQL (current graph) and NCBI E-utilities
# (efetch/esearch db=taxonomy). Outputs: pairs.csv, flagged.jsonl, sample.json, summary.json.

import argparse
import csv
import json
import os
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

SPARQL = "https://id.nlm.nih.gov/mesh/sparql"
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
UA = "MV2-Munim-taxid-audit/0.1 (mailto:mv2@munimtech.com)"
SEED = 20261112
SAMPLE_MAX = 20
LOOKUP_CAP = 700

PFX = ("PREFIX mv: <http://id.nlm.nih.gov/mesh/vocab#> "
       "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> ")
Q_PAIRS = PFX + """SELECT DISTINCT ?cid ?clabel ?rn ?rid ?rlabel ?rtype ?ractive ?pref
FROM <http://id.nlm.nih.gov/mesh> WHERE {
 ?c mv:relatedRegistryNumber ?rn . FILTER(STRSTARTS(STR(?rn), "txid"))
 ?c mv:identifier ?cid . ?c rdfs:label ?clabel .
 OPTIONAL { { ?r mv:preferredConcept ?c . BIND("1" AS ?pref) } UNION { ?r mv:concept ?c . BIND("0" AS ?pref) }
   ?r mv:identifier ?rid . ?r rdfs:label ?rlabel . ?r a ?rtype . OPTIONAL { ?r mv:active ?ractive } }
} ORDER BY ?cid ?rn ?rid"""
Q_TERMS = PFX + """SELECT DISTINCT ?cid ?tlabel FROM <http://id.nlm.nih.gov/mesh> WHERE {
 ?c mv:relatedRegistryNumber ?rn . FILTER(STRSTARTS(STR(?rn), "txid"))
 ?c mv:identifier ?cid . { ?c mv:preferredTerm ?t } UNION { ?c mv:term ?t } ?t mv:prefLabel ?tlabel .
} ORDER BY ?cid ?tlabel"""
Q_NOTES = PFX + """SELECT DISTINCT ?cid ?sn FROM <http://id.nlm.nih.gov/mesh> WHERE {
 ?c mv:relatedRegistryNumber ?rn . FILTER(STRSTARTS(STR(?rn), "txid"))
 ?c mv:identifier ?cid . ?c mv:scopeNote ?sn .
} ORDER BY ?cid"""


def norm(s):
    return " ".join((s or "").lower().replace("’", "'").split())


def loose(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def classify(clabel, terms, taxon):
    """taxon: dict with sci and other [(kind, name)]. Returns (cls, matched_terms)."""
    ncbi = [taxon.get("sci", "")] + [n for _, n in taxon.get("other", [])]
    nset = {norm(n) for n in ncbi if n}
    lset = {loose(n) for n in ncbi if n}
    mesh = [clabel] + [t for t in terms if norm(t) != norm(clabel)]
    matched = [t for t in mesh if norm(t) in nset or loose(t) in lset]
    if norm(clabel) == norm(taxon.get("sci", "")):
        return "label_exact", matched
    if norm(clabel) in nset:
        return "label_synonym", matched
    if loose(clabel) in lset:
        return "label_loose", matched
    if matched:
        return "term_only", matched
    return "no_name_match", matched


def parse_taxa(xml_text):
    root = ET.fromstring(xml_text)
    out = {}
    for tx in root.findall("Taxon"):
        tid = (tx.findtext("TaxId") or "").strip()
        names = []
        on = tx.find("OtherNames")
        if on is not None:
            for el in on:
                if el.tag == "Name":
                    d = el.findtext("DispName")
                    if d:
                        names.append((el.findtext("ClassCDE") or "name", d.strip()))
                elif el.text and el.text.strip():
                    names.append((el.tag, el.text.strip()))
        out[tid] = {"taxid": tid, "sci": (tx.findtext("ScientificName") or "").strip(),
                    "rank": tx.findtext("Rank") or "", "division": tx.findtext("Division") or "",
                    "lineage": tx.findtext("Lineage") or "", "other": names,
                    "aka": [(a.text or "").strip() for a in tx.findall("AkaTaxIds/TaxId")]}
    return out


def resolve(requested, taxa):
    """Map each requested txid number to (status, taxon or None)."""
    aka = {}
    for t in taxa.values():
        for a in t["aka"]:
            aka[a] = t
    res = {}
    for r in requested:
        if r in taxa:
            res[r] = ("ok", taxa[r])
        elif r in aka:
            res[r] = ("merged", aka[r])
        else:
            res[r] = ("not_found", None)
    return res


def record_rank(r):
    """Prefer the record whose preferred concept this is, then an active record."""
    return (r.get("pref") == "1", r.get("ractive") == "true")


def pick_sample(keys, k=SAMPLE_MAX, seed=SEED):
    ks = sorted(set(keys))
    if len(ks) <= k:
        return ks
    return sorted(random.Random(seed).sample(ks, k))


def get(url, tries=5):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # retry on any network/HTTP error
            last = e
        time.sleep(3 * (i + 1))
    raise RuntimeError("GET failed %s: %s" % (url[:200], last))


def sparql_all(q):
    rows, off, first_prev = [], 0, None
    for _ in range(200):
        params = {"query": q, "format": "JSON", "inference": "false",
                  "limit": "1000", "offset": str(off)}
        data = json.loads(get(SPARQL + "?" + urllib.parse.urlencode(params)))
        b = data["results"]["bindings"]
        if not b:
            break
        page = [{k: v["value"] for k, v in r.items()} for r in b]
        if page[0] == first_prev:
            break
        first_prev = page[0]
        rows.extend(page)
        off += len(b)
        time.sleep(0.5)
    return rows


def esearch_tax(term):
    url = EUTILS + "esearch.fcgi?" + urllib.parse.urlencode(
        {"db": "taxonomy", "term": term, "retmode": "json", "retmax": "20"})
    data = json.loads(get(url))
    time.sleep(0.4)
    return data.get("esearchresult", {}).get("idlist", [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="out")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)

    pairs = sparql_all(Q_PAIRS)
    terms_rows = sparql_all(Q_TERMS)
    notes_rows = sparql_all(Q_NOTES)
    terms, notes = {}, {}
    for r in terms_rows:
        terms.setdefault(r["cid"], []).append(r["tlabel"])
    for r in notes_rows:
        notes.setdefault(r["cid"], r["sn"])

    # one row per (concept, txid); keep record info (prefer the record whose preferred concept it is)
    by_pair = {}
    for r in pairs:
        key = (r["cid"], r["rn"])
        cur = by_pair.get(key)
        if cur is None or record_rank(r) > record_rank(cur):
            by_pair[key] = r
    tx_per_concept = {}
    for cid, rn in by_pair:
        tx_per_concept[cid] = tx_per_concept.get(cid, 0) + 1

    nums = sorted({rn[4:].strip() for _, rn in by_pair}, key=lambda x: (len(x), x))
    valid = [n for n in nums if n.isdigit()]
    taxa = {}
    for i in range(0, len(valid), 200):
        chunk = valid[i:i + 200]
        url = EUTILS + "efetch.fcgi?" + urllib.parse.urlencode(
            {"db": "taxonomy", "id": ",".join(chunk), "retmode": "xml"})
        taxa.update(parse_taxa(get(url)))
        time.sleep(0.5)
    resolved = resolve(valid, taxa)
    for n in nums:
        if n not in resolved:
            resolved[n] = ("malformed", None)

    out_rows, flagged, lookups = [], [], 0
    for (cid, rn) in sorted(by_pair):
        r = by_pair[(cid, rn)]
        num = rn[4:].strip()
        status, tx = resolved[num]
        cterms = terms.get(cid, [])
        if tx is None:
            cls, matched = "not_found", []
        else:
            cls, matched = classify(r["clabel"], cterms, tx)
        row = {"cid": cid, "clabel": r["clabel"], "rid": r.get("rid", ""),
               "rlabel": r.get("rlabel", ""), "rtype": r.get("rtype", "").split("#")[-1],
               "ractive": r.get("ractive", ""), "pref": r.get("pref", ""), "txid": num,
               "n_txids_on_concept": tx_per_concept[cid], "ncbi_status": status,
               "ncbi_taxid_now": tx["taxid"] if tx else "", "sci": tx["sci"] if tx else "",
               "rank": tx["rank"] if tx else "", "cls": cls, "matched_terms": "|".join(matched),
               "better_txids_sci": "", "better_txids_any": "",
               "scope_note": (notes.get(cid, "") or "")[:300]}
        if cls in ("term_only", "no_name_match") and lookups < LOOKUP_CAP:
            sci_ids = esearch_tax('"%s"[Scientific Name]' % r["clabel"])
            any_ids = esearch_tax('"%s"[All Names]' % r["clabel"])
            lookups += 2
            row["better_txids_sci"] = "|".join(i for i in sci_ids if i != row["ncbi_taxid_now"])
            row["better_txids_any"] = "|".join(i for i in any_ids if i != row["ncbi_taxid_now"])
        out_rows.append(row)
        if cls in ("term_only", "no_name_match", "not_found") or status == "merged":
            flagged.append(dict(row, mesh_terms=cterms, scope_note=notes.get(cid, ""),
                                ncbi_other=tx["other"] if tx else [],
                                lineage=tx["lineage"] if tx else ""))

    fields = list(out_rows[0].keys()) if out_rows else []
    with open(os.path.join(a.out_dir, "pairs.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in out_rows:
            w.writerow(row)
    with open(os.path.join(a.out_dir, "flagged.jsonl"), "w", encoding="utf-8") as f:
        for row in flagged:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def counts(rows):
        c = {}
        for row in rows:
            c[row["cls"]] = c.get(row["cls"], 0) + 1
        return c
    single = [r for r in out_rows if r["n_txids_on_concept"] == 1]
    better = [r for r in single if r["cls"] in ("term_only", "no_name_match") and r["better_txids_sci"]]
    sample = pick_sample([r["cid"] + ":" + r["txid"] for r in better])
    with open(os.path.join(a.out_dir, "sample.json"), "w", encoding="utf-8") as f:
        json.dump({"seed": SEED, "max": SAMPLE_MAX,
                   "better_txid_single": sorted(r["cid"] + ":" + r["txid"] for r in better),
                   "sample": sample}, f, indent=1)
    summary = {
        "sparql_pair_rows": len(pairs), "pairs": len(out_rows), "concepts": len(tx_per_concept),
        "distinct_txids": len(nums), "single_txid_concepts": len(single),
        "classes_all": counts(out_rows), "classes_single": counts(single),
        "ncbi_status": {s: sum(1 for v in resolved.values() if v[0] == s)
                        for s in ("ok", "merged", "not_found", "malformed")},
        "flagged": len(flagged), "better_txid_single": len(better), "lookups": lookups,
        "sample_size": len(sample),
        "known_case_M0447888": [{k: r[k] for k in ("txid", "sci", "cls", "matched_terms",
                                                    "better_txids_sci")}
                                for r in out_rows if r["cid"] == "M0447888"],
    }
    with open(os.path.join(a.out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
