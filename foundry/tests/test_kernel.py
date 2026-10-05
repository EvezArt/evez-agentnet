import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from runtime.kernel import Kernel

def test_boot_and_policy():
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
        assert boot["state"] == "READY"
        assert boot["spine_valid"] is True
        assert kernel.request("SCOUT", "OBSERVE", x=1)["allowed"] is True
        assert kernel.request("SCOUT", "DEPLOY", x=1)["allowed"] is False
        assert kernel.spine.verify() is True
        assert len((root / "evidence" / "spine.jsonl").read_text(encoding="utf-8").splitlines()) == 4
