#!/usr/bin/env python3
"""
Tests for the knowledge expansion system.
Unit tests for harvester, learner, memory indexer, capabilities, skill synth, cross-pollinator.
Mocks all external APIs.
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestHarvester(unittest.TestCase):
    """Tests for agents.knowledge.harvester."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self._patch_dir = patch("agents.knowledge.harvester.DISCOVERIES_DIR", Path(self.tmpdir) / "discoveries")
        self._patch_dir.start()
        (Path(self.tmpdir) / "discoveries").mkdir()

    def tearDown(self):
        self._patch_dir.stop()

    def test_score_relevance_high(self):
        from agents.knowledge.harvester import _score_relevance
        text = "autonomous agent with multi-agent reinforcement learning for LLM tool use"
        score = _score_relevance(text)
        self.assertGreater(score, 0.5)

    def test_score_relevance_low(self):
        from agents.knowledge.harvester import _score_relevance
        text = "cooking recipes for pasta"
        score = _score_relevance(text)
        self.assertEqual(score, 0.0)

    def test_infer_applicability_agent(self):
        from agents.knowledge.harvester import _infer_applicability
        result = _infer_applicability("Multi-agent coordination", "swarm intelligence")
        self.assertIn("multi-agent", result.lower())

    def test_infer_applicability_quantum(self):
        from agents.knowledge.harvester import _infer_applicability
        result = _infer_applicability("Quantum optimization", "quantum computing speedup")
        self.assertIn("quantum", result.lower())

    def test_save_discovery(self):
        from agents.knowledge.harvester import _save_discovery
        discovery = {
            "id": "test_123",
            "source": "test",
            "title": "Test Discovery",
            "summary": "A test",
            "relevance_score": 0.5,
            "applicability": "Testing",
            "url": "https://example.com",
            "discovered_at": datetime.now(timezone.utc).isoformat(),
        }
        path = _save_discovery(discovery)
        self.assertTrue(Path(path).exists())
        loaded = json.loads(Path(path).read_text())
        self.assertEqual(loaded["id"], "test_123")

    def test_extract_xml(self):
        from agents.knowledge.harvester import _extract_xml
        xml = "<title>Hello World</title>"
        self.assertEqual(_extract_xml(xml, "title"), "Hello World")

    def test_extract_xml_missing(self):
        from agents.knowledge.harvester import _extract_xml
        xml = "<other>stuff</other>"
        self.assertEqual(_extract_xml(xml, "title"), "")

    @patch("agents.knowledge.harvester.scan_arxiv", return_value=[])
    @patch("agents.knowledge.harvester.scan_github_trending", return_value=[])
    @patch("agents.knowledge.harvester.scan_huggingface", return_value=[])
    @patch("agents.knowledge.harvester.scan_ai_news", return_value=[])
    def test_run_empty(self, *mocks):
        from agents.knowledge.harvester import run
        results = run()
        self.assertEqual(len(results), 0)

    @patch("agents.knowledge.harvester.scan_arxiv")
    @patch("agents.knowledge.harvester.scan_github_trending", return_value=[])
    @patch("agents.knowledge.harvester.scan_huggingface", return_value=[])
    @patch("agents.knowledge.harvester.scan_ai_news", return_value=[])
    def test_run_with_discoveries(self, _news, _hf, _gh, mock_arxiv):
        from agents.knowledge.harvester import run
        mock_arxiv.return_value = [{
            "id": "d_001",
            "source": "arxiv",
            "title": "Test Paper",
            "summary": "A test paper",
            "relevance_score": 0.8,
            "applicability": "Testing",
            "url": "https://arxiv.org/abs/test",
            "discovered_at": datetime.now(timezone.utc).isoformat(),
        }]
        results = run()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["source"], "arxiv")


class TestLearner(unittest.TestCase):
    """Tests for agents.knowledge.learner."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self._patches = [
            patch("agents.knowledge.learner.DISCOVERIES_DIR", Path(self.tmpdir) / "discoveries"),
            patch("agents.knowledge.learner.RESEARCH_DIR", Path(self.tmpdir) / "research"),
            patch("agents.knowledge.learner.GRAPH_PATH", Path(self.tmpdir) / "graph.json"),
        ]
        for p in self._patches:
            p.start()
        (Path(self.tmpdir) / "discoveries").mkdir()
        (Path(self.tmpdir) / "research").mkdir()

    def tearDown(self):
        for p in self._patches:
            p.stop()

    def test_classify_high_relevance_github(self):
        from agents.knowledge.learner import _classify_discovery
        d = {"source": "github", "relevance_score": 0.7, "title": "agent tool"}
        self.assertEqual(_classify_discovery(d), "can_apply_now")

    def test_classify_low_relevance(self):
        from agents.knowledge.learner import _classify_discovery
        d = {"source": "news", "relevance_score": 0.1, "title": "generic news"}
        self.assertEqual(_classify_discovery(d), "future_potential")

    def test_classify_arxiv_research(self):
        from agents.knowledge.learner import _classify_discovery
        d = {"source": "arxiv", "relevance_score": 0.5, "title": "research paper"}
        self.assertEqual(_classify_discovery(d), "requires_research")

    def test_match_repos_agent(self):
        from agents.knowledge.learner import _match_repos
        d = {"title": "multi-agent coordination", "summary": "agent orchestration"}
        repos = _match_repos(d)
        self.assertIn("evez-agentnet", repos)

    def test_match_repos_default(self):
        from agents.knowledge.learner import _match_repos
        d = {"title": "unrelated thing", "summary": "nothing matches"}
        repos = _match_repos(d)
        self.assertEqual(repos, ["evez-agentnet"])

    def test_run_creates_research_notes(self):
        from agents.knowledge.learner import run
        discoveries = [{
            "id": "test_research_1",
            "source": "arxiv",
            "title": "Deep research paper",
            "summary": "Needs investigation",
            "relevance_score": 0.45,
            "applicability": "Future research",
            "url": "https://arxiv.org/test",
        }]
        stats = run(discoveries)
        self.assertEqual(stats["requires_research"], 1)

    def test_run_updates_graph(self):
        from agents.knowledge.learner import run
        discoveries = [{
            "id": "test_graph_1",
            "source": "github",
            "title": "Agent Framework Update",
            "summary": "New agent framework",
            "relevance_score": 0.8,
            "applicability": "Direct application",
            "url": "https://github.com/test",
        }]
        run(discoveries)
        graph_path = Path(self.tmpdir) / "graph.json"
        self.assertTrue(graph_path.exists())
        graph = json.loads(graph_path.read_text())
        self.assertGreater(len(graph["concepts"]), 0)


class TestMemoryIndex(unittest.TestCase):
    """Tests for agents.knowledge.memory_index."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self._patches = [
            patch("agents.knowledge.memory_index.INDEX_PATH", Path(self.tmpdir) / "index.json"),
            patch("agents.knowledge.memory_index.DISCOVERIES_DIR", Path(self.tmpdir) / "discoveries"),
        ]
        for p in self._patches:
            p.start()
        (Path(self.tmpdir) / "discoveries").mkdir()

    def tearDown(self):
        for p in self._patches:
            p.stop()

    def test_extract_keywords(self):
        from agents.knowledge.memory_index import _extract_keywords
        keywords = _extract_keywords("autonomous agent with reinforcement learning capabilities")
        self.assertIn("autonomous", keywords)
        self.assertIn("agent", keywords)
        self.assertNotIn("with", keywords)

    def test_search_basic(self):
        from agents.knowledge.memory_index import search
        index = {
            "entries": [
                {"title": "Agent orchestration", "keywords": ["agent", "orchestration"], "source": "test"},
                {"title": "Cooking recipes", "keywords": ["cooking", "recipes"], "source": "test"},
            ]
        }
        results = search("agent coordination", index)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Agent orchestration")

    def test_apply_decay_fresh(self):
        from agents.knowledge.memory_index import _apply_decay
        entries = [{
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "title": "Fresh entry",
        }]
        result = _apply_decay(entries)
        self.assertEqual(result[0]["decay_score"], 0.0)
        self.assertFalse(result[0]["stale"])

    def test_index_discoveries(self):
        from agents.knowledge.memory_index import index_discoveries
        # Write a test discovery
        d = {
            "id": "test_idx_1",
            "source": "test",
            "title": "Test Discovery",
            "summary": "For testing",
            "relevance_score": 0.5,
            "discovered_at": datetime.now(timezone.utc).isoformat(),
        }
        (Path(self.tmpdir) / "discoveries" / "test.json").write_text(json.dumps(d))
        entries = index_discoveries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["source"], "knowledge_discovery")

    @patch("agents.knowledge.memory_index.index_git_history", return_value=[])
    @patch("agents.knowledge.memory_index.index_decisions", return_value=[])
    def test_run_builds_index(self, *mocks):
        from agents.knowledge.memory_index import run
        # Add a discovery to index
        d = {
            "id": "run_test_1",
            "source": "test",
            "title": "Run Test",
            "summary": "Testing run",
            "relevance_score": 0.5,
            "discovered_at": datetime.now(timezone.utc).isoformat(),
        }
        (Path(self.tmpdir) / "discoveries" / "run_test.json").write_text(json.dumps(d))
        stats = run()
        self.assertGreater(stats["total_entries"], 0)
        index_path = Path(self.tmpdir) / "index.json"
        self.assertTrue(index_path.exists())


class TestCapabilities(unittest.TestCase):
    """Tests for agents.knowledge.capabilities."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self._patch = patch("agents.knowledge.capabilities.CAPABILITIES_PATH", Path(self.tmpdir) / "capabilities.json")
        self._patch.start()

    def tearDown(self):
        self._patch.stop()

    def test_scan_local_repo(self):
        from agents.knowledge.capabilities import scan_local_repo
        caps = scan_local_repo(".")
        self.assertGreater(len(caps), 0)
        # Should find at least the harvester
        names = [c["name"] for c in caps]
        self.assertIn("harvester", names)

    def test_scan_skills(self):
        from agents.knowledge.capabilities import scan_skills
        caps = scan_skills()
        # Should find claude skills
        self.assertGreater(len(caps), 0)

    def test_identify_gaps(self):
        from agents.knowledge.capabilities import _identify_gaps
        # With no capabilities, should find all gaps
        gaps = _identify_gaps([])
        self.assertGreater(len(gaps), 0)

    def test_identify_gaps_reduced(self):
        from agents.knowledge.capabilities import _identify_gaps
        # With some capabilities, fewer gaps
        caps = [
            {"name": "self_repair", "type": "agent", "description": "Self repair system"},
            {"name": "income_generation", "type": "agent", "description": "Income generation loop"},
        ]
        gaps_full = _identify_gaps([])
        gaps_partial = _identify_gaps(caps)
        self.assertLess(len(gaps_partial), len(gaps_full))


class TestSkillSynth(unittest.TestCase):
    """Tests for agents.knowledge.skill_synth."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self._patches = [
            patch("agents.knowledge.skill_synth.DISCOVERIES_DIR", Path(self.tmpdir) / "discoveries"),
            patch("agents.knowledge.skill_synth.GRAPH_PATH", Path(self.tmpdir) / "graph.json"),
            patch("agents.knowledge.skill_synth.SKILLS_DIR", Path(self.tmpdir) / "skills"),
        ]
        for p in self._patches:
            p.start()
        (Path(self.tmpdir) / "discoveries").mkdir()
        (Path(self.tmpdir) / "skills").mkdir()

    def tearDown(self):
        for p in self._patches:
            p.stop()

    def test_generate_skill_manifest(self):
        from agents.knowledge.skill_synth import _generate_skill_manifest
        manifest = _generate_skill_manifest("test_skill", "A test skill", ["trigger1"])
        self.assertIn("test_skill", manifest)
        self.assertIn("A test skill", manifest)
        self.assertIn("trigger1", manifest)

    def test_find_skill_opportunities(self):
        from agents.knowledge.skill_synth import _find_skill_opportunities
        discoveries = [{
            "title": "Enhanced Agent Tool",
            "applicability": "Could enhance agent tool-use capabilities",
            "relevance_score": 0.8,
        }]
        graph = {"concepts": {}}
        opps = _find_skill_opportunities(discoveries, graph)
        self.assertGreater(len(opps), 0)

    def test_save_skill(self):
        from agents.knowledge.skill_synth import _save_skill
        path = _save_skill("test_skill", "# Test\nManifest", "print('hello')")
        skill_dir = Path(path)
        self.assertTrue((skill_dir / "SKILL.md").exists())
        self.assertTrue((skill_dir / "test_skill.py").exists())
        self.assertTrue((skill_dir / "meta.json").exists())


class TestCrossPollinate(unittest.TestCase):
    """Tests for agents.knowledge.cross_pollinate."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self._patches = [
            patch("agents.knowledge.cross_pollinate.PATTERNS_PATH", Path(self.tmpdir) / "patterns.json"),
            patch("agents.knowledge.cross_pollinate.CAPABILITIES_PATH", Path(self.tmpdir) / "capabilities.json"),
            patch("agents.knowledge.cross_pollinate.GRAPH_PATH", Path(self.tmpdir) / "graph.json"),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()

    def test_extract_local_patterns(self):
        from agents.knowledge.cross_pollinate import extract_local_patterns
        patterns = extract_local_patterns()
        # Should find patterns in this codebase
        self.assertGreater(len(patterns), 0)
        names = [p["name"] for p in patterns]
        # The codebase uses env vars with fallback
        self.assertIn("env_graceful_fallback", names)

    def test_evaluate_discoveries_empty_graph(self):
        from agents.knowledge.cross_pollinate import evaluate_discoveries_across_repos
        # Write empty graph
        (Path(self.tmpdir) / "graph.json").write_text(json.dumps({"concepts": {}}))
        recs = evaluate_discoveries_across_repos()
        self.assertEqual(len(recs), 0)


class TestKnowledgeGraphIntegrity(unittest.TestCase):
    """Integration test: verify knowledge graph structure after full pipeline."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_graph_structure(self):
        """Verify graph.json has valid structure after learner processes discoveries."""
        from agents.knowledge.learner import run as learner_run
        graph_path = Path(self.tmpdir) / "graph.json"

        with patch("agents.knowledge.learner.DISCOVERIES_DIR", Path(self.tmpdir) / "discoveries"), \
             patch("agents.knowledge.learner.RESEARCH_DIR", Path(self.tmpdir) / "research"), \
             patch("agents.knowledge.learner.GRAPH_PATH", graph_path):

            (Path(self.tmpdir) / "discoveries").mkdir()
            (Path(self.tmpdir) / "research").mkdir()

            discoveries = [
                {
                    "id": "integ_1",
                    "source": "github",
                    "title": "Advanced Agent Orchestration Framework",
                    "summary": "Multi-agent system for autonomous tasks",
                    "relevance_score": 0.9,
                    "applicability": "Direct application to agentnet",
                    "url": "https://github.com/test/repo",
                },
                {
                    "id": "integ_2",
                    "source": "arxiv",
                    "title": "Quantum-Inspired Optimization for Neural Networks",
                    "summary": "Novel quantum techniques for optimization",
                    "relevance_score": 0.6,
                    "applicability": "Research potential",
                    "url": "https://arxiv.org/abs/test",
                },
            ]

            learner_run(discoveries)

            self.assertTrue(graph_path.exists())
            graph = json.loads(graph_path.read_text())

            # Verify structure
            self.assertIn("concepts", graph)
            self.assertIn("updated_at", graph)
            self.assertIsInstance(graph["concepts"], dict)

            # Verify concepts have required fields
            for concept, data in graph["concepts"].items():
                self.assertIn("repos", data)
                self.assertIn("discoveries", data)
                self.assertIn("first_seen", data)
                self.assertIsInstance(data["repos"], list)
                self.assertIsInstance(data["discoveries"], list)


if __name__ == "__main__":
    unittest.main()
