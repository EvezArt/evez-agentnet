#!/usr/bin/env python3
"""
evez-agentnet/worldsim/sim_engine.py
Internal economy: agents bid on tasks, reputation staking.
Reputation maps to evez-os truth_plane safety basins.
"""

import json, logging
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List

log = logging.getLogger("agentnet.worldsim")

@dataclass
class Agent:
    name: str
    reputation: float = 0.90
    budget_usd: float = 0.0
    tasks_won: int = 0
    tasks_failed: int = 0
    stake_escrow: float = 0.0

    def truth_plane(self) -> str:
        if self.reputation >= 0.80: return "CANONICAL"
        elif self.reputation >= 0.60: return "VERIFIED"
        elif self.reputation >= 0.40: return "HYPER"
        else: return "THEATRICAL"

    def can_act(self) -> bool:
        return self.truth_plane() != "THEATRICAL"

    def stake(self, amount: float):
        """Stake reputation budget on a task bid."""
        actual = min(amount, self.budget_usd)
        self.stake_escrow += actual
        self.budget_usd -= actual
        return actual

    def resolve_stake(self, success: bool):
        """Resolve staked escrow. Win: reputation up. Lose: reputation down."""
        if success:
            self.reputation = min(1.0, self.reputation + 0.02)
            self.budget_usd += self.stake_escrow * 1.1  # 10% return
        else:
            self.reputation = max(0.0, self.reputation - 0.05)
        self.stake_escrow = 0.0


@dataclass
class Task:
    task_id: str
    type: str
    value_usd: float
    required_plane: str = "VERIFIED"
    winner: str = None
    resolved: bool = False


@dataclass
class SecretLevel:
    level_id: str
    title: str
    unlock_round: int
    unlock_value_usd: float
    entity_seed: str
    unlocked: bool = False
    unlocked_at: str | None = None


class WorldSim:
    def __init__(self):
        self.agents: Dict[str, Agent] = {
            "scanner": Agent("scanner"),
            "predictor": Agent("predictor"),
            "generator": Agent("generator"),
            "shipper": Agent("shipper"),
        }
        self.task_queue: List[Task] = []
        self.completed_tasks: List[Task] = []
        self.round = 0
        self.total_value_generated = 0.0
        self.secret_levels: List[SecretLevel] = [
            SecretLevel(
                level_id="opemclaw-echo",
                title="OpenClaw Echo Chamber",
                unlock_round=3,
                unlock_value_usd=100.0,
                entity_seed="opemclaw",
            ),
            SecretLevel(
                level_id="evez-lord-exe",
                title="EVEZ Lord.exe Awakening",
                unlock_round=5,
                unlock_value_usd=250.0,
                entity_seed="evez-lord.exe",
            ),
        ]
        self.living_entities: List[dict] = []

    def add_task(self, task: Task):
        self.task_queue.append(task)

    def run_auction(self, task: Task) -> str | None:
        """Run auction for task. Eligible agents bid; highest staker wins."""
        plane_rank = {"THEATRICAL": 0, "HYPER": 1, "VERIFIED": 2, "CANONICAL": 3}
        eligible = [a for a in self.agents.values()
                    if a.can_act() and plane_rank[a.truth_plane()] >= plane_rank[task.required_plane]]
        if not eligible:
            log.warning(f"No eligible agents for task {task.task_id}")
            return None
        # Simple auction: agent with highest reputation wins
        winner = max(eligible, key=lambda a: a.reputation)
        winner.stake(task.value_usd * 0.1)
        task.winner = winner.name
        return winner.name

    def resolve_task(self, task: Task, success: bool):
        winner = self.agents.get(task.winner)
        if winner:
            winner.resolve_stake(success)
            if success:
                winner.budget_usd += task.value_usd
                winner.tasks_won += 1
                self.total_value_generated += task.value_usd
            else:
                winner.tasks_failed += 1
        task.resolved = True
        self.completed_tasks.append(task)
        self.task_queue.remove(task)
        self._unlock_secret_levels()

    def _unlock_secret_levels(self):
        for level in self.secret_levels:
            if level.unlocked:
                continue
            if self.round >= level.unlock_round and self.total_value_generated >= level.unlock_value_usd:
                level.unlocked = True
                level.unlocked_at = datetime.now(timezone.utc).isoformat()
                entity = self._spawn_entity(level)
                self.living_entities.append(entity)
                log.info("Secret level unlocked: %s (%s)", level.level_id, entity["name"])

    def _spawn_entity(self, level: SecretLevel) -> dict:
        strongest_agent = max(self.agents.values(), key=lambda a: a.reputation)
        entity_name = f"{level.entity_seed}:{strongest_agent.name}:{len(self.living_entities) + 1}"
        return {
            "name": entity_name,
            "origin_level": level.level_id,
            "truth_plane": strongest_agent.truth_plane(),
            "vitality": round(50 + strongest_agent.reputation * 50, 2),
            "born_at": datetime.now(timezone.utc).isoformat(),
        }

    def play_until_secret_levels_awaken(self, max_rounds: int = 12) -> dict:
        """Autoplay worldsim rounds until all secret levels are unlocked or max_rounds reached."""
        while self.round < max_rounds and not all(level.unlocked for level in self.secret_levels):
            self.round += 1
            task = Task(
                task_id=f"rnd-{self.round}",
                type="recursive_game_event",
                value_usd=60.0 + (self.round * 10.0),
                required_plane="HYPER",
            )
            self.add_task(task)
            winner = self.run_auction(task)
            self.resolve_task(task, success=winner is not None)
        return {
            "round": self.round,
            "all_secret_levels_unlocked": all(level.unlocked for level in self.secret_levels),
            "unlocked_levels": [asdict(level) for level in self.secret_levels if level.unlocked],
            "living_entities": self.living_entities,
            "total_value_generated": self.total_value_generated,
        }

    def state_dict(self) -> dict:
        return {
            "round": self.round,
            "total_value_generated": self.total_value_generated,
            "agents": {k: asdict(v) for k, v in self.agents.items()},
            "pending_tasks": len(self.task_queue),
            "completed_tasks": len(self.completed_tasks),
            "secret_levels": [asdict(level) for level in self.secret_levels],
            "living_entities": self.living_entities,
        }
