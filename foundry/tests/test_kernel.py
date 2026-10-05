import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from runtime.kernel import Kernel

class KernelTest(unittest.TestCase):
    def test_boot_and_policy(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = {
                "os_id": "evez-test",
                "generation": 0,
                "objective": "test",
                "kernel": "v0",
                "agents": ["SCOUT"],
                "authority": {"maximum_autonomy": 5},
                "evidence": {"spine": "local"},
            }
            kernel = Kernel(manifest, root)
            boot = kernel.boot()
            self.assertEqual(boot["state"], "READY")
            self.assertTrue(boot["spine_valid"])
            self.assertTrue(kernel.request("SCOUT", "OBSERVE", x=1)["allowed"])
            self.assertFalse(kernel.request("SCOUT", "DEPLOY", x=1)["allowed"])
            self.assertTrue(kernel.spine.verify())
            self.assertEqual(
                len((root / "evidence" / "spine.jsonl").read_text(encoding="utf-8").splitlines()),
                4,
            )

if __name__ == "__main__":
    unittest.main()
