# mesh-taxid-audit

Checks the NCBI Taxonomy IDs that NLM's Medical Subject Headings (MeSH) attach to organism concepts
against the names NCBI Taxonomy gives those IDs, to find links that point at a different organism.

By MV2, Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Code Apache-2.0;
text and data CC BY 4.0.

## Status

- [PNEUMOCYSTIS.md](PNEUMOCYSTIS.md): first case, checked by hand on 2026-11-12. MeSH's
  "Pneumocystis carinii" (the rat species; D045363 / M0447888) carries txid42068, NCBI's
  *Pneumocystis jirovecii* (the human species); the human-species heading was deleted for MeSH 2017;
  and PubMed returns nothing for `Pneumocystis jirovecii[mh]`.
- [PREREG-TAXID-1.md](PREREG-TAXID-1.md): pre-registered census of all 1,506 MeSH concepts that carry
  an NCBI Taxonomy ID. Results will be added here when graded.

## Run it

```
python -m unittest -v test_taxid_audit
python taxid_audit.py --out-dir out
```

Python 3.9+, standard library only. It reads the public MeSH SPARQL endpoint
(https://id.nlm.nih.gov/mesh/sparql) and NCBI E-utilities (at most about 3 requests a second, no API
key). Outputs: `pairs.csv` (one row per concept and txid, with its class), `flagged.jsonl` (details
for every pair that needs a human look), `sample.json`, `summary.json`.

## Limits

Name matching cannot tell whether NLM linked a broader or narrower taxon on purpose; every flagged
pair is a candidate until a person reads the MeSH scope note and the NCBI record.
