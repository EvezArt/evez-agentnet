# EVEZ Access Layer (Non-Mutative Extensions)
# Provides read-only, composable interfaces into AGI Proof Surface

import time
from typing import Callable, List, Dict

class FireEvent:
    def __init__(self, n:int, phi:float, depth:int, hash_id:str):
        self.n = n
        self.phi = phi
        self.depth = depth
        self.hash_id = hash_id
        self.ts = time.time()

class AccessLayer:
    def __init__(self):
        self.subscribers: List[Callable[[FireEvent], None]] = []
        self.buffer: List[FireEvent] = []

    def emit(self, event: FireEvent):
        self.buffer.append(event)
        if len(self.buffer) > 1000:
            self.buffer = self.buffer[-1000:]
        for sub in self.subscribers:
            try:
                sub(event)
            except Exception:
                pass

    def subscribe(self, fn: Callable[[FireEvent], None]):
        self.subscribers.append(fn)

    def snapshot(self) -> List[Dict]:
        return [e.__dict__ for e in self.buffer]

# Example hook
access_layer = AccessLayer()

def hook_proof_surface(n, phi, depth, hash_id):
    event = FireEvent(n, phi, depth, hash_id)
    access_layer.emit(event)

# Consumers can import access_layer + subscribe without touching core logic
