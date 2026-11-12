# SPDX-License-Identifier: Apache-2.0
# Tests for taxid_audit.py (no network). MV2, Munim, Inc. Made with AI agents.
import unittest

import taxid_audit as t

JIROVECII = {"taxid": "42068", "sci": "Pneumocystis jirovecii",
             "other": [("Includes", "Pneumocystis carinii f. sp. hominis"),
                       ("authority", "Pneumocystis jirovecii Frenkel, 1976"),
                       ("misspelling", "Pneumocystis jiroveci")]}
CARINII_TERMS = ["Pneumocystis carinii", "Pneumocystis carini",
                 "Pneumocystis carinii f. sp. carinii", "Pneumocystis carinii f. sp. ratti",
                 "Pneumocystis carinii f. sp. hominis"]

XML = """<?xml version="1.0" ?>
<!DOCTYPE TaxaSet PUBLIC "-//NLM//DTD Taxon, 14th January 2002//EN" "https://www.ncbi.nlm.nih.gov/entrez/query/DTD/taxon.dtd">
<TaxaSet><Taxon>
 <TaxId>4754</TaxId><ScientificName>Pneumocystis carinii</ScientificName>
 <OtherNames><EquivalentName>Pneumocystis carinii f. sp. ratti</EquivalentName>
  <Name><ClassCDE>authority</ClassCDE><DispName>Pneumocystis carinii P. Delano&#235; &amp; Delano&#235;, 1912</DispName></Name>
 </OtherNames>
 <Rank>species</Rank><Division>Plants and Fungi</Division>
 <LineageEx><Taxon><TaxId>4753</TaxId><ScientificName>Pneumocystis</ScientificName></Taxon></LineageEx>
 <AkaTaxIds><TaxId>99999</TaxId></AkaTaxIds>
</Taxon></TaxaSet>"""


class TestClassify(unittest.TestCase):
    def test_known_mislink_is_term_only(self):
        cls, matched = t.classify("Pneumocystis carinii", CARINII_TERMS, JIROVECII)
        self.assertEqual(cls, "term_only")
        self.assertEqual(matched, ["Pneumocystis carinii f. sp. hominis"])

    def test_exact(self):
        cls, _ = t.classify("pneumocystis  JIROVECII", [], JIROVECII)
        self.assertEqual(cls, "label_exact")

    def test_synonym(self):
        cls, matched = t.classify("Pneumocystis jiroveci", [], JIROVECII)
        self.assertEqual(cls, "label_synonym")
        self.assertEqual(matched, ["Pneumocystis jiroveci"])

    def test_loose(self):
        tx = {"sci": "Hepatitis B virus", "other": []}
        self.assertEqual(t.classify("Hepatitis-B Virus", [], tx)[0], "label_loose")

    def test_no_match(self):
        self.assertEqual(t.classify("Escherichia coli", ["E. coli"], JIROVECII),
                         ("no_name_match", []))


class TestParse(unittest.TestCase):
    def test_parse_top_level_only(self):
        taxa = t.parse_taxa(XML)
        self.assertEqual(list(taxa), ["4754"])
        tx = taxa["4754"]
        self.assertEqual(tx["sci"], "Pneumocystis carinii")
        self.assertEqual(tx["rank"], "species")
        self.assertIn(("EquivalentName", "Pneumocystis carinii f. sp. ratti"), tx["other"])
        self.assertEqual(tx["other"][1][0], "authority")
        self.assertEqual(tx["aka"], ["99999"])

    def test_resolve(self):
        taxa = t.parse_taxa(XML)
        res = t.resolve(["4754", "99999", "1"], taxa)
        self.assertEqual(res["4754"][0], "ok")
        self.assertEqual(res["99999"][0], "merged")
        self.assertEqual(res["99999"][1]["taxid"], "4754")
        self.assertEqual(res["1"], ("not_found", None))


class TestMisc(unittest.TestCase):
    def test_norm_loose(self):
        self.assertEqual(t.norm("  A’b  C "), "a'b c")
        self.assertEqual(t.loose("Hepatitis-B Virus"), "hepatitisbvirus")

    def test_record_rank(self):
        self.assertGreater(t.record_rank({"pref": "1", "ractive": "true"}),
                           t.record_rank({"pref": "1", "ractive": "false"}))
        self.assertGreater(t.record_rank({"pref": "1"}), t.record_rank({"pref": "0", "ractive": "true"}))

    def test_sample(self):
        ks = ["M%d:%d" % (i, i) for i in range(50)]
        s = t.pick_sample(ks)
        self.assertEqual(len(s), 20)
        self.assertEqual(s, t.pick_sample(list(reversed(ks))))
        self.assertEqual(t.pick_sample(["b", "a"]), ["a", "b"])

    def test_queries_mention_txid(self):
        for q in (t.Q_PAIRS, t.Q_TERMS, t.Q_NOTES):
            self.assertIn('STRSTARTS(STR(?rn), "txid")', q)
            self.assertIn("FROM <http://id.nlm.nih.gov/mesh>", q)


if __name__ == "__main__":
    unittest.main()
