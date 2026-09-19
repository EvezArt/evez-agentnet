from tools.causal_governance_benchmark import run_benchmark


def test_deterministic_benchmark():
    report = run_benchmark()
    assert report["passed"] == report["total"]
    assert report["total"] == 6
