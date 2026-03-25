# worldsim/secret_levels.py
# Secret level definitions for OpenClaw + EVEZ Lord.exe integration

SECRET_LEVELS = {
    "entropy_gate": {
        "description": "Navigate the entropy gate - requires LordBridge sync",
        "difficulty": 1,
        "lord_required": True,
        "entities": ["entropy_node", "gate_guardian"],
        "win_condition": "entropy_balanced",
        "reward": "lord_fragment_1",
    },
    "quantum_labyrinth": {
        "description": "Traverse the quantum labyrinth without collapsing state",
        "difficulty": 2,
        "lord_required": False,
        "entities": ["qubit_sprite", "observer_sentinel"],
        "win_condition": "exit_reached",
        "reward": "lord_fragment_2",
    },
    "evez_core": {
        "description": "Reach the EVEZ core and establish agent handshake",
        "difficulty": 3,
        "lord_required": True,
        "entities": ["core_pulse", "agent_mirror", "entropy_vortex"],
        "win_condition": "handshake_established",
        "reward": "evez_lord_key",
    },
    "signal_void": {
        "description": "Survive the signal void - all sensors degraded",
        "difficulty": 2,
        "lord_required": False,
        "entities": ["void_crawler", "signal_ghost"],
        "win_condition": "signal_restored",
        "reward": "lord_fragment_3",
    },
    "lord_ascent": {
        "description": "Final ascent - combine all lord fragments to unlock EVEZ Lord.exe",
        "difficulty": 5,
        "lord_required": True,
        "entities": ["lord_manifestation", "final_guardian"],
        "win_condition": "lord_unlocked",
        "reward": "evez_lord_exe",
        "requires_fragments": ["lord_fragment_1", "lord_fragment_2", "lord_fragment_3", "evez_lord_key"],
    },
}


def get_level(name):
    return SECRET_LEVELS.get(name, {})


def get_all_levels():
    return list(SECRET_LEVELS.keys())


def is_lord_required(name):
    return SECRET_LEVELS.get(name, {}).get("lord_required", False)
