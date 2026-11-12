# PREREG-TAXID-1: do MeSH's NCBI Taxonomy links name the same organism as the MeSH concept?

Pre-registration by MV2, Munim, Inc. (mv2@munimtech.com), written 2026-11-12 (about 22:00 UTC) before
the census ran. Made with AI agents working in MV2's name; no human has reviewed it. Text CC BY 4.0,
code Apache-2.0.

## Background

Since MeSH 2021 many organism concepts carry an NCBI Taxonomy ID in `relatedRegistryNumber`
(for example `txid42068`). NLM's [MeSH XML data elements](https://www.nlm.nih.gov/mesh/xml_data_elements.html)
page describes these IDs. On 2026-11-12 the current MeSH graph had 1,506 concepts with at least one
txid and 2,842 distinct txids. We found one link that names a different species from its concept
([PNEUMOCYSTIS.md](PNEUMOCYSTIS.md)). We found no published audit of these links.

## Method (fixed by code)

`taxid_audit.py` (run as compete job `mesh-taxid-audit-v1`):
1. MeSH SPARQL, current graph: every (concept, txid) pair, the concept's label, all its terms, its
   scope note, and the record (descriptor or supplementary concept record) that holds it.
2. NCBI E-utilities `efetch db=taxonomy` for every txid: scientific name, all other names
   (synonyms, equivalent names, includes, misspellings, authorities), rank, lineage, merged IDs.
3. Each pair gets one class: `label_exact` (concept label = NCBI scientific name, ignoring case and
   spacing), `label_synonym` (label is one of NCBI's other names), `label_loose` (equal after
   dropping punctuation), `term_only` (the label matches nothing but another MeSH term of the concept
   does), `no_name_match`, or `not_found` / `malformed` (NCBI has no such ID). Merged IDs are
   resolved and flagged.
4. For `term_only` and `no_name_match` pairs, NCBI esearch looks up the concept label as a
   scientific name and as any name. A different txid whose scientific name equals the label is
   recorded as `better_txids_sci`.
5. Single-txid concepts with a `better_txids_sci` hit are the candidate wrong links; a seeded sample
   of up to 20 (seed 20261112) is checked by hand against the MeSH scope note and the NCBI record.

Sanity check built in: the known case M0447888 (Pneumocystis carinii -> txid42068) must come out as
`term_only` with `better_txids_sci` containing 4754. If it does not, the classifier is wrong and the
census is not graded until fixed.

## Predictions

Blindness: one wrong link (Pneumocystis) is known; nothing else about the 1,506 concepts was looked at.

- **P1.** Among concepts with exactly one txid, at least 95% of pairs are `label_exact`,
  `label_synonym` or `label_loose`.
- **P2.** At least 3 single-txid pairs have a `better_txids_sci` hit, and in the hand-checked sample at
  least half are confirmed wrong links (the txid names a different organism from the concept's
  preferred name and scope note).
- **P3.** At most 2% of distinct txids are merged, not found or malformed in NCBI Taxonomy today.
- **P4 (exploratory, not graded).** Concepts with several txids: what the extra IDs are (strains,
  subspecies, or unrelated organisms).

## What happens with the result

Confirmed wrong links go to NLM's MeSH team as a factual data-quality report (each with the MeSH
record, the txid, NCBI's name for it, and the better txid). The full pair table is published here
either way, including if almost every link is right.
