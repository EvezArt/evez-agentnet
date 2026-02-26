"""
AUTONOMOUS AGENT LOOP
The core cognitive engine. Not a scheduler. Not a cron job.

A genuine agent loop:
  Perceive -> Orient -> Decide -> Act -> Observe -> Learn -> Repeat

The key distinction from a simple orchestrator:
  - It reads its own memory before deciding what to run
  - It prioritizes based on learned performance, not static schedules
  - It detects when something urgent has changed and interrupts its plan
  - It evaluates the quality of its own outputs
  - It writes what it learned back to memory
  - Over time it runs better generators more often and worse ones less

This is the loop that makes the system rise beyond static tooling.
"""
import sys, os, json, time, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from pathlib import Path
import logging

from core.agent_memory import AgentMemory
from core.meta_learner import MetaLearner

try:
    from core.g2_protocol_rate import ProtocolRateMonitor, UtilizationSpikeMonitor
    from core.g3_funding_pipeline import FundingPipelineCrawler
    from core.g4_dao_treasury import DAOTreasuryScanner
    from core.g5_mev_surface import MEVSurfaceDetector
    from core.g7_incentive_tracker import IncentiveProgramTracker
    from core.g8_architecture import ArchitectureCombinator
except ImportError:
    # Generators not yet implemented — loop still boots
    ProtocolRateMonitor = UtilizationSpikeMonitor = None
    FundingPipelineCrawler = DAOTreasuryScanner = None
    MEVSurfaceDetector = IncentiveProgramTracker = ArchitectureCombinator = None

try:
    from config.settings import MASTER_DOC_PATH, CANDIDATES_DB, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
except ImportError:
    MASTER_DOC_PATH = "outputs/master_doc.md"
    CANDIDATES_DB = "outputs/candidates.json"
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [AGENT] %(levelname)s: %(message)s")
log = logging.getLogger("AgentLoop")

Path("memory").mkdir(exist_ok=True)
Path("outputs").mkdir(exist_ok=True)

# Generator Registry
GENERATORS = {}
if ProtocolRateMonitor:
    GENERATORS["g2_rates"] = {"cls": ProtocolRateMonitor, "base_interval_h": 4, "section": "yield"}
    GENERATORS["g2_util"] = {"cls": UtilizationSpikeMonitor, "base_interval_h": 0.5, "section": "signals"}
if FundingPipelineCrawler:
    GENERATORS["g3_funding"] = {"cls": FundingPipelineCrawler, "base_interval_h": 168, "section": "funding"}
if DAOTreasuryScanner:
    GENERATORS["g4_dao"] = {"cls": DAOTreasuryScanner, "base_interval_h": 168, "section": "dao"}
if MEVSurfaceDetector:
    GENERATORS["g5_mev"] = {"cls": MEVSurfaceDetector, "base_interval_h": 168, "section": "mev"}
if IncentiveProgramTracker:
    GENERATORS["g7_incentive"] = {"cls": IncentiveProgramTracker, "base_interval_h": 168, "section": "yield"}
if ArchitectureCombinator:
    GENERATORS["g8_arch"] = {"cls": ArchitectureCombinator, "base_interval_h": 720, "section": "architecture"}

LAST_RUN_PATH = Path("memory/last_run.json")


class AgentLoop:
    def __init__(self):
        self.memory = AgentMemory()
        self.learner = MetaLearner(self.memory)
        self.last_runs: dict = self._load_last_runs()

    def perceive(self) -> dict:
        perception = {
            "timestamp": datetime.utcnow().isoformat(),
            "live_signals": self.memory.working.flush_signals(),
            "memory_snapshot": self.memory.snapshot(),
            "urgent": [],
            "due_generators": self._get_due_generators(),
        }
        for sig in perception["live_signals"]:
            if sig.get("borrow_apy", 0) > 30:
                perception["urgent"].append({
                    "type": "utilization_spike",
                    "protocol": sig.get("protocol"),
                    "apy": sig.get("borrow_apy"),
                    "action": "run_liquidation_scan_immediately",
                })
        semantic_deadlines = self.memory.semantic.search("deadline")
        for key, val in semantic_deadlines.items():
            deadline = val.get("value", {}).get("deadline") if isinstance(val, dict) else None
            if deadline:
                try:
                    dt = datetime.fromisoformat(str(deadline))
                    if dt - datetime.utcnow() < timedelta(days=7):
                        perception["urgent"].append({
                            "type": "funding_deadline",
                            "program": key,
                            "days_left": (dt - datetime.utcnow()).days,
                            "action": "alert_immediately",
                        })
                except Exception:
                    pass
        return perception

    def orient(self, perception: dict) -> dict:
        plan = {"immediate": [], "scheduled": [], "deferred": [], "meta_cycle": False}
        for urgency in perception.get("urgent", []):
            if urgency["action"] == "run_liquidation_scan_immediately":
                plan["immediate"].extend(["g5_mev", "g2_util"])
            elif urgency["action"] == "alert_immediately":
                plan["immediate"].append("_alert")
        best_generators = set(self.memory.meta.get_best_generators(top_n=3))
        profiles = self.memory.meta._meta.get("generators", {})
        for gen_id in perception.get("due_generators", []):
            if gen_id in plan["immediate"]:
                continue
            actionable_rate = profiles.get(gen_id, {}).get("actionable_rate", 0.1)
            priority = self.memory.meta._meta.get("generator_profiles", {}).get(gen_id, {}).get("priority", 5)
            if gen_id in best_generators or priority >= 7:
                plan["scheduled"].append(gen_id)
            elif actionable_rate < 0.03 and priority < 3:
                plan["deferred"].append(gen_id)
            else:
                plan["scheduled"].append(gen_id)
        last_meta = self.memory.semantic.get("last_meta_learning_cycle")
        if last_meta:
            try:
                last_dt = datetime.fromisoformat(last_meta)
                if datetime.utcnow() - last_dt > timedelta(days=7):
                    plan["meta_cycle"] = True
            except Exception:
                plan["meta_cycle"] = True
        else:
            plan["meta_cycle"] = True
        return plan

    def decide(self, plan: dict) -> list:
        actions = []
        for gen_id in plan["immediate"]:
            if gen_id == "_alert":
                actions.append(("alert", "funding_deadline"))
            else:
                actions.append(("run_generator", gen_id))
        for gen_id in plan["scheduled"]:
            actions.append(("run_generator", gen_id))
        if plan["meta_cycle"]:
            actions.append(("meta_learning", "full_cycle"))
        actions.append(("compile", "master_doc"))
        return actions

    def act(self, actions: list) -> dict:
        results = {"actions_taken": [], "candidates_total": 0, "high_score_total": 0}
        for action_type, target in actions:
            self.memory.episodic.record(
                event_type=f"action:{action_type}",
                data={"target": target, "started": datetime.utcnow().isoformat()}
            )
            if action_type == "run_generator":
                result = self._run_generator(target)
                results["candidates_total"] += result.get("candidates", 0)
                results["high_score_total"] += result.get("high_score", 0)
                results["actions_taken"].append(f"ran {target}: {result.get('candidates', 0)} candidates")
                self.memory.meta.record_generator_run(
                    generator=target,
                    candidates=result.get("candidates", 0),
                    high_score=result.get("high_score", 0),
                    runtime_s=result.get("runtime_s", 0),
                )
                self._update_last_run(target)
            elif action_type == "meta_learning":
                report = self.learner.run_full_learning_cycle()
                self.memory.semantic.set("last_meta_learning_cycle", datetime.utcnow().isoformat())
                results["actions_taken"].append(f"meta_learning: {len(report.get('weight_adjustments', []))} weight adjustments")
                log.info(f"Meta-learning cycle complete: {json.dumps(report, indent=2, default=str)}")
            elif action_type == "compile":
                self._compile_to_master_doc()
                results["actions_taken"].append("compiled master doc")
            elif action_type == "alert":
                self._send_alert(target)
                results["actions_taken"].append(f"alert sent: {target}")
        return results

    def observe(self, results: dict) -> None:
        self.memory.episodic.record(
            event_type="cycle_complete",
            data={
                "candidates_total": results["candidates_total"],
                "high_score_total": results["high_score_total"],
                "actions_taken": results["actions_taken"],
            }
        )
        self.memory.semantic.set("last_cycle_stats", {
            "candidates": results["candidates_total"],
            "high_score": results["high_score_total"],
            "cycle_time": datetime.utcnow().isoformat(),
        })
        log.info(f"Cycle complete. Candidates: {results['candidates_total']}, High-score: {results['high_score_total']}")
        log.info(f"Memory state: {json.dumps(self.memory.snapshot(), indent=2, default=str)}")

    def run_cycle(self) -> dict:
        """One full OODA loop iteration."""
        log.info("=== AGENT CYCLE START ===")
        perception = self.perceive()
        plan = self.orient(perception)
        actions = self.decide(plan)
        results = self.act(actions)
        self.observe(results)
        log.info("=== AGENT CYCLE END ===")
        return results

    def run_daemon(self, cycle_interval_s: int = 1800) -> None:
        """Run the agent loop continuously. Default: every 30 minutes."""
        log.info(f"Agent daemon starting. Cycle interval: {cycle_interval_s}s")
        while True:
            try:
                self.run_cycle()
            except Exception as e:
                log.error(f"Cycle failed: {e}", exc_info=True)
            log.info(f"Sleeping {cycle_interval_s}s until next cycle...")
            time.sleep(cycle_interval_s)

    def _run_generator(self, gen_id: str) -> dict:
        if gen_id not in GENERATORS:
            return {}
        t0 = time.time()
        gen_cls = GENERATORS[gen_id]["cls"]
        gen = gen_cls()
        candidates = gen.run()
        runtime = round(time.time() - t0, 2)
        high_score = len([c for c in candidates if c.get("_score", 0) >= 70])
        return {"candidates": len(candidates), "high_score": high_score, "runtime_s": runtime}

    def _get_due_generators(self) -> list:
        due = []
        now = datetime.utcnow()
        for gen_id, config in GENERATORS.items():
            last = self.last_runs.get(gen_id)
            if last is None:
                due.append(gen_id)
                continue
            last_dt = datetime.fromisoformat(last)
            interval = timedelta(hours=config["base_interval_h"])
            if now - last_dt >= interval:
                due.append(gen_id)
        return due

    def _update_last_run(self, gen_id: str) -> None:
        self.last_runs[gen_id] = datetime.utcnow().isoformat()
        with open(LAST_RUN_PATH, "w") as f:
            json.dump(self.last_runs, f, indent=2)

    def _load_last_runs(self) -> dict:
        if not LAST_RUN_PATH.exists():
            return {}
        with open(LAST_RUN_PATH) as f:
            return json.load(f)

    def _compile_to_master_doc(self) -> None:
        db_path = Path(CANDIDATES_DB)
        if not db_path.exists():
            return
        with open(db_path) as f:
            all_candidates = json.load(f)
        high = [c for c in all_candidates if c.get("_score", 0) >= 70]
        if not high:
            return
        doc_path = Path(MASTER_DOC_PATH)
        doc_path.parent.mkdir(exist_ok=True)
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        lines = [f"\n---\n## AUTO-ADDITIONS — {ts}\n"]
        for c in sorted(high, key=lambda x: x["_score"], reverse=True)[:15]:
            name = c.get("name") or c.get("protocol") or c.get("id", "?")
            score = c["_score"]
            gen = c.get("_generator", "?")
            apy = c.get("apy") or c.get("net_yield_apy", "")
            apy_s = f" — {apy}% APY" if apy else ""
            lines.append(f"- **{name}**{apy_s} _(gen: {gen}, score: {score:.0f})_")
        with open(doc_path, "a") as f:
            f.write("\n".join(lines))

    def _send_alert(self, alert_type: str) -> None:
        import requests
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            log.warning("Telegram not configured — alert suppressed")
            return
        msg = f"* evez-os ALERT*\nType: {alert_type}\nTime: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"},
                timeout=10
            )
        except Exception as e:
            log.warning(f"Alert send failed: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="evez-agentnet Autonomous Agent Loop")
    parser.add_argument("--cycle", action="store_true", help="Run one full OODA cycle")
    parser.add_argument("--daemon", action="store_true", help="Run continuous daemon")
    parser.add_argument("--interval", type=int, default=1800, help="Daemon cycle interval (seconds)")
    args = parser.parse_args()

    agent = AgentLoop()
    if args.cycle:
        results = agent.run_cycle()
        print(json.dumps(results, indent=2, default=str))
    elif args.daemon:
        agent.run_daemon(cycle_interval_s=args.interval)
    else:
        parser.print_help()
