"""Regression tests for the RSI engine fixes in evez-agentnet/orchestrator.py.

Run:  cd /root/evez-agentnet && python3 test_rsi_engine.py

Covers three defects found in production logs:
  1. H1 emitted "recover via streak" to a perfect (1.0) agent forever.
  2. H3 emitted "expand compassion_layer" when fire_total == 0 (backwards).
  3. Hypotheses were generated, stored, and never consumed (decorative).
"""
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import orchestrator as O


def fresh_state():
    return {
        "round": 10,
        "total_earned_usd": 0.0,
        "agents": {
            "scanner":   {"reputation": 1.0, "tasks_completed": 5, "streak": 244},
            "predictor": {"reputation": 1.0, "tasks_completed": 5, "streak": 244},
            "generator": {"reputation": 1.0, "tasks_completed": 5, "streak": 244},
            "shipper":   {"reputation": 1.0, "tasks_completed": 5, "streak": 244},
            "maes":      {"reputation": 1.0, "tasks_completed": 5, "streak": 243},
        },
        "maes": {"player_count": 0, "agent_count": 0, "fire_events_total": 0},
        "rsi":  {"hypotheses": []},
    }


def by_id(hs, hid):
    return next(h for h in hs if h["id"] == hid)


def test_all_perfect_does_not_advise_recovery():
    """Defect 1: saturated agents must not be told to recover."""
    s = fresh_state()
    h = by_id(O.generate_rsi_hypotheses(s), "H1")
    assert h["action"] != "recover_reputation", \
        f"H1 still prescribes recovery at rep=1.0: {h}"
    assert "recover" not in h["text"].lower()
    print("  ok  H1 holds at full reputation instead of prescribing recovery")


def test_saturated_idle_agent_triggers_yield():
    """A perfect agent doing nothing should widen the net, not chase reputation."""
    s = fresh_state()
    s["agents"]["generator"]["tasks_completed"] = 0
    h = by_id(O.generate_rsi_hypotheses(s), "H1")
    assert h["action"] == "raise_scan_yield", f"expected raise_scan_yield, got {h}"
    assert h["agent"] == "generator"
    print("  ok  saturated+idle agent triggers raise_scan_yield")


def test_genuinely_weak_agent_still_recovers():
    """The fix must not disable legitimate recovery."""
    s = fresh_state()
    s["agents"]["shipper"]["reputation"] = 0.40
    h = by_id(O.generate_rsi_hypotheses(s), "H1")
    assert h["action"] == "recover_reputation", f"expected recover_reputation, got {h}"
    assert h["agent"] == "shipper"
    print("  ok  genuinely weak agent still gets recover_reputation")


def test_zero_fire_holds_compassion():
    """Defect 2: zero signal must hold, not expand."""
    s = fresh_state()
    h = by_id(O.generate_rsi_hypotheses(s), "H3")
    assert h["action"] == "hold", f"expected hold at fire_total=0, got {h}"
    assert "expand compassion" not in h["text"].lower()
    print("  ok  H3 holds compassion_layer at zero FIRE events")


def test_nonzero_fire_expands():
    s = fresh_state()
    s["maes"]["fire_events_total"] = 17
    h = by_id(O.generate_rsi_hypotheses(s), "H3")
    assert h["action"] == "expand_compassion"
    assert "17" in h["text"]
    print("  ok  H3 expands when FIRE events exist")


def test_hypotheses_have_actions():
    """No bare strings — every hypothesis must be machine-actionable."""
    hs = O.generate_rsi_hypotheses(fresh_state())
    assert len(hs) == 3, f"expected 3 hypotheses, got {len(hs)}"
    for h in hs:
        assert isinstance(h, dict), f"hypothesis is not a dict: {h!r}"
        for k in ("id", "action", "text"):
            assert k in h, f"hypothesis missing {k}: {h}"
        assert h["action"] != "", "empty action key"
    print("  ok  all 3 hypotheses carry structured id/action/text")


def test_directives_actually_change_state():
    """Defect 3: applying a directive must mutate state."""
    s = fresh_state()
    before = json.dumps(s, sort_keys=True)

    O.apply_rsi_directives(s, [{"id": "H1", "action": "raise_scan_yield", "agent": "scanner", "text": ""}])
    assert s["scan"]["yield_multiplier"] == 1.25, \
        f"raise_scan_yield did not apply: {s.get('scan')}"
    assert json.dumps(s, sort_keys=True) != before

    O.apply_rsi_directives(s, [{"id": "H3", "action": "expand_compassion", "agent": None, "text": ""}])
    assert s["maes"]["compassion_expansion"] == 1

    s["maes"]["player_count"] = 12
    O.apply_rsi_directives(s, [{"id": "H2", "action": "spawn_npcs", "agent": None, "text": ""}])
    assert s["maes"]["pending_npc_spawn"] == 6, \
        f"expected 6 pending spawns (12//2), got {s['maes'].get('pending_npc_spawn')}"

    s["agents"]["shipper"]["streak"] = 99
    O.apply_rsi_directives(s, [{"id": "H1", "action": "recover_reputation", "agent": "shipper", "text": ""}])
    assert s["agents"]["shipper"]["streak"] == 0
    print("  ok  every directive mutates state (yield, compassion, spawn, streak)")


def test_yield_multiplier_caps():
    s = fresh_state()
    for _ in range(40):
        O.apply_rsi_directives(s, [{"id": "H1", "action": "raise_scan_yield", "agent": "scanner", "text": ""}])
    assert s["scan"]["yield_multiplier"] == 3.0, \
        f"yield_multiplier should cap at 3.0, got {s['scan']['yield_multiplier']}"
    print("  ok  yield_multiplier caps at 3.0")


def test_apply_tolerates_legacy_string_hypotheses():
    """Old spine/state may contain bare strings; must not crash."""
    s = fresh_state()
    applied = O.apply_rsi_directives(s, ["Evolve scanner agent: reputation=1.00 -> inject synthetic"])
    assert applied == [], f"legacy string should apply nothing, got {applied}"
    print("  ok  legacy string hypotheses tolerated without crashing")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            failed += 1
            print(f"  FAIL {t.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
