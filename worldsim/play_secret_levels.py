#!/usr/bin/env python3
"""Autoplay the worldsim game until secret levels awaken entities."""

import json
from pathlib import Path

from worldsim.sim_engine import WorldSim


if __name__ == "__main__":
    sim = WorldSim()
    summary = sim.play_until_secret_levels_awaken()

    output_path = Path("worldsim/secret_levels_state.json")
    output_path.write_text(json.dumps(summary, indent=2))

    print(json.dumps(summary, indent=2))
    print(f"\nSaved: {output_path}")
