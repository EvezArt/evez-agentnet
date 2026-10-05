import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from runtime.memory import MemoryStore

class MemoryStoreTest(unittest.TestCase):
    def test_provenance_and_search(self):
        with tempfile.TemporaryDirectory() as td:
            store = MemoryStore(Path(td) / "memory.jsonl")
            user = store.add("USER_STATEMENT", "the system should preserve continuity", source="USER")
            store.add("INFERENCE", "continuity requires provenance", source="MODEL")
            hits = store.search("continuity")
            self.assertEqual(len(hits), 2)
            self.assertEqual(user["kind"], "USER_STATEMENT")
            with self.assertRaises(ValueError):
                store.add("FACT", "invented category")

if __name__ == "__main__":
    unittest.main()
