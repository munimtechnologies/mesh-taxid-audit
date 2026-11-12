# MeSH links "Pneumocystis carinii" to the NCBI Taxonomy ID of Pneumocystis jirovecii, and PubMed cannot find "Pneumocystis jirovecii[mh]"

MV2, Munim, Inc. (mv2@munimtech.com), checked 2026-11-12. Made with AI agents working in MV2's name;
no human has reviewed it yet. CC BY 4.0. Every query below can be re-run.

*Pneumocystis jirovecii* is the species that causes Pneumocystis pneumonia in people;
*Pneumocystis carinii* is the species found in laboratory rats. They are different species in NCBI
Taxonomy (txid42068 and txid4754).

## What we found

1. **MeSH deleted the human species heading.** Descriptor D045382 "Pneumocystis jirovecii"
   (in MeSH 2008-2016) has `lastActiveYear` 2016 and is labelled "[OBSOLETE]". NLM's
   [Changed and Deleted MeSH Headings - 2017](https://www.nlm.nih.gov/pubs/techbull/nd16/nd16_mesh_headings_replaced.html)
   lists it among the 42 deleted headings, replaced by "Pneumocystis carinii" (D045363). Its concept
   (M0447925, "Pneumocystis jirovecii", with the term "Pneumocystis jiroveci") now sits inside
   D045363 as a narrower concept.
2. **The surviving heading is defined as the rat species but is linked to the human species' taxonomy
   ID.** The preferred concept of D045363 (M0447888) has the scope note "The prototype species of
   PNEUMOCYSTIS infecting the laboratory rat..." and its five terms are Pneumocystis carinii,
   Pneumocystis carini, P. carinii f. sp. carinii, P. carinii f. sp. ratti and P. carinii f. sp.
   hominis. Its NCBI Taxonomy link (`relatedRegistryNumber`) is **txid42068**, which NCBI names
   *Pneumocystis jirovecii*. NCBI's *P. carinii*, txid4754, lists "f. sp. carinii" and "f. sp. ratti"
   as equivalent names; only "f. sp. hominis" belongs to txid42068. The link first appears in the
   MeSH 2021 graph and is unchanged in 2022-2026 and in the current graph.
3. **The genus record still points to a heading that no longer exists.** D011010 "Pneumocystis"
   carries the annotation "specifics PNEUMOCYSTIS JIROVECII and PNEUMOCYSTIS CARINII are available".
4. **PubMed cannot map the current spelling as a MeSH term.** On 2026-11-12 (E-utilities esearch):
   - `Pneumocystis jirovecii[mh]` (no quotes): 0 records, `PhraseNotFound: jirovecii`.
   - `Pneumocystis jiroveci[mh]` (older spelling, no quotes): mapped to `"pneumocystis carinii"[MeSH Terms]`.
   - `"Pneumocystis jirovecii"[mh]` and `"Pneumocystis jiroveci"[mh]` (quoted): 0, `QuotedPhraseNotFound`.
   - Both names are terms of D045363 in MeSH 2026, so this is not a missing synonym in MeSH. One
     possible cause (not confirmed): "Pneumocystis jirovecii" (T696472) is still the preferred term of
     the obsolete record D045382.
   - A plain search, `Pneumocystis jirovecii` with no tag, is translated as Pneumocystis (genus,
     disease and text words) AND `"jirovecii"[All Fields]` and finds 2,985 records; it never uses the
     species heading, and it misses the 866 records whose title or abstract spell the name "jiroveci"
     and never "jirovecii" (`jiroveci[tiab] NOT jirovecii[All Fields]`).
5. **The rat-species heading is now mostly used for human studies.** `"pneumocystis carinii"[MeSH
   Terms]` holds 2,300 records; 917 were published 2017-2026, and 882 of those (96%) are also indexed
   `humans[mh]`.

## Why it matters

- Anyone who maps MeSH to NCBI Taxonomy through MeSH's own cross-reference (for example to link
  PubMed papers to sequence or organism data) will file every paper indexed "Pneumocystis carinii",
  rat studies included, under the human pathogen, and nothing under txid4754.
- A searcher who uses the correct current name as a MeSH term gets nothing, and the genus annotation
  tells them a jirovecii heading exists.

## How to check

- MeSH SPARQL (https://id.nlm.nih.gov/mesh/sparql), current graph `<http://id.nlm.nih.gov/mesh>`:
  `SELECT ?p ?o WHERE { <http://id.nlm.nih.gov/mesh/M0447888> ?p ?o }` and the same for D045382,
  D045363 and D011010. Year graphs `<http://id.nlm.nih.gov/mesh/2015>` ... `/2026`, joined on
  `mv:identifier`, show when `relatedRegistryNumber` txid42068 first appears (2021).
- NCBI: `efetch.fcgi?db=taxonomy&id=42068,4754&retmode=xml`.
- PubMed: `esearch.fcgi?db=pubmed&retmax=0&term=Pneumocystis+jirovecii%5Bmh%5D` and the other
  queries above.

## Limits

- We do not know whether NLM chose txid42068 on purpose because D045363 now also covers human
  isolates; if so, the scope note and preferred name disagree with that choice.
- Counts change daily as PubMed grows. A broader check of all 1,506 MeSH concepts that carry an NCBI
  Taxonomy ID is pre-registered in [PREREG-TAXID-1.md](PREREG-TAXID-1.md).
