#!/usr/bin/env python3
import json, os, hashlib, subprocess, sys

ROOT = '/root/evez-agentnet'
FORGE = os.path.join(ROOT, 'forge_output')
EVIDENCE = os.path.join(ROOT, 'evidence')
STATE_DIR = os.path.join(ROOT, 'status')
STATE_FILE = os.path.join(STATE_DIR, '.stamp_anchor_state.json')
WITNESS_FILE = os.path.join(EVIDENCE, 'anchor_witness.jsonl')
ANCHOR_METHODS = ['digicert', 'git_note', 'witness_receipt']
FAILURE_THRESHOLD = 8

