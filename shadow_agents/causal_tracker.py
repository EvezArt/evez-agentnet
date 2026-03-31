from collections import deque, defaultdict
import uuid

class CausalTracker:
    def __init__(self, window=10):
        self.window = deque(maxlen=window)
        self.event_graph = defaultdict(list)  # event_id -> list of caused_event_ids

    def on_event(self, event):
        # Assign unique ID
        event_id = str(uuid.uuid4())
        event['event_id'] = event_id

        # Track recent events for causal inference
        for prev_event in self.window:
            if event['phi'] > prev_event['phi']:
                self.event_graph[prev_event['event_id']].append(event_id)
                print(f"[CAUSAL] {prev_event['n']} → {event['n']}")

        self.window.append(event)

    def recent_causes(self, event_id):
        return [k for k,v in self.event_graph.items() if event_id in v]

    def print_graph(self):
        print("[CAUSAL GRAPH]")
        for k,v in self.event_graph.items():
            print(f"{k} -> {v}")