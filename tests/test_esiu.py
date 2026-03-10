from pathlib import Path

from esiu.core import ESIU, Event


def make_esiu(tmp_path: Path) -> ESIU:
    events = tmp_path / "events.jsonl"
    cases = tmp_path / "cases.jsonl"
    return ESIU(store_path=str(events), case_log_path=str(cases))


def test_low_severity_observes(tmp_path: Path):
    esiu = make_esiu(tmp_path)
    event = Event("auth.failure", "192.168.1.1", "user_a", "login", 20)
    inv = esiu.investigate(event)
    assert inv.verdict == "OBSERVE"


def test_high_severity_requires_human(tmp_path: Path):
    esiu = make_esiu(tmp_path)
    event = Event("data.exfil", "10.0.0.1", "bot_x", "database", 90)
    inv = esiu.investigate(event)
    assert inv.action_taken == "QUEUED_FOR_HUMAN"


def test_repeat_actor_escalates(tmp_path: Path):
    esiu = make_esiu(tmp_path)
    for _ in range(5):
        esiu.investigate(Event("auth.failure", "1.2.3.4", "bad_actor", "api", 45))
    inv = esiu.investigate(Event("auth.failure", "1.2.3.4", "bad_actor", "api", 45))
    assert inv.verdict in ("QUARANTINE", "FREEZE", "RESTRICT")


def test_backtrace_finds_prior_events(tmp_path: Path):
    esiu = make_esiu(tmp_path)
    esiu.investigate(Event("scan.port", "5.5.5.5", "scanner", "host", 30))
    inv = esiu.investigate(Event("auth.attempt", "5.5.5.5", "scanner", "ssh", 60))
    assert len(inv.backtrace) >= 1
