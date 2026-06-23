from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ontology.runtime import OntologyRuntime, RuntimeConfig


class MemoryRelationGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.runtime = OntologyRuntime(RuntimeConfig(db_path=root / "ontology.sqlite"))
        corpus = root / "corpus"
        corpus.mkdir()
        (corpus / "helios.md").write_text(
            "# Helios Platform\n\n"
            "Helios deployment summary covers the rollout pipeline and the release cadence "
            "for the Helios service across staging and production.\n",
            encoding="utf-8",
        )
        self.runtime.ingest_path(corpus, access_scope="internal")
        # Two distinct queries that hit the same evidence chunk produce two
        # candidate tickets with near-identical candidate_text.
        self.runtime.query("Helios deployment summary alpha", allowed_scopes=["internal"])
        self.runtime.query("Helios deployment summary beta", allowed_scopes=["internal"])
        self.tickets = [c["ticket_id"] for c in self.runtime.list_memory_candidates()]

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_two_candidates_created(self) -> None:
        self.assertGreaterEqual(len(self.tickets), 2, "expected at least two candidate tickets")

    def test_dedup_links_near_duplicates(self) -> None:
        report = self.runtime.relate_memory_candidates(threshold=0.5)
        self.assertEqual(report["status"], "ok")
        self.assertGreaterEqual(report["similar_links_created"], 1)
        # Re-running is idempotent: no new links created the second time.
        again = self.runtime.relate_memory_candidates(threshold=0.5)
        self.assertEqual(again["similar_links_created"], 0)

    def test_graph_shows_similar_edge(self) -> None:
        self.runtime.relate_memory_candidates(threshold=0.5)
        graph = self.runtime.memory_graph(self.tickets[0])
        edges = graph["outgoing"] + graph["incoming"]
        self.assertTrue(any(edge["link_type"] == "similar_to" for edge in edges))

    def test_supersede_records_structural_edge(self) -> None:
        old_ticket, new_ticket = self.tickets[0], self.tickets[1]
        result = self.runtime.decide_memory_candidate(
            old_ticket, "supersede", reason="newer fact replaces it", target_ticket=new_ticket
        )
        self.assertEqual(result["status"], "superseded")
        self.assertIn("link", result)
        self.assertEqual(result["link"]["link_type"], "supersedes")
        graph = self.runtime.memory_graph(old_ticket)
        self.assertIn(new_ticket, graph["superseded_by"])

    def test_decide_target_requires_replacement_decision(self) -> None:
        with self.assertRaises(ValueError):
            self.runtime.decide_memory_candidate(
                self.tickets[0], "approve", reason="x", target_ticket=self.tickets[1]
            )

    def test_memory_graph_unknown_ticket_fails_loud(self) -> None:
        with self.assertRaises(KeyError):
            self.runtime.memory_graph("ticket-does-not-exist")

    def test_link_rejects_bad_type_and_self_link(self) -> None:
        with self.assertRaises(ValueError):
            self.runtime.link_memory(self.tickets[0], self.tickets[1], "nonsense", reason="x")
        with self.assertRaises(ValueError):
            self.runtime.link_memory(self.tickets[0], self.tickets[0], "similar_to", reason="x")

    def test_link_unknown_ticket_fails_loud(self) -> None:
        with self.assertRaises(KeyError):
            self.runtime.link_memory(self.tickets[0], "missing-ticket", "contradicts", reason="x")

    def test_verify_counts_include_memory_links(self) -> None:
        self.runtime.relate_memory_candidates(threshold=0.5)
        report = self.runtime.verify()
        self.assertEqual(report["status"], "pass")
        self.assertIn("memory_links", report["counts"])
        self.assertGreaterEqual(report["counts"]["memory_links"], 1)


if __name__ == "__main__":
    unittest.main()
