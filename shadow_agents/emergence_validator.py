from collections import deque
import statistics

class EmergenceValidator:
    def __init__(self, window=30, min_variance=0.002):
        self.window = deque(maxlen=window)
        self.min_variance = min_variance

    def on_event(self, event):
        self.window.append(event['phi'])

        if len(self.window) < 10:
            return

        variance = statistics.variance(self.window)

        if variance < self.min_variance:
            print(f"[REJECT] Fake EMERGE at n={event['n']} (low variance: {variance:.5f})")
        else:
            print(f"[VALID] Emergence pattern real at n={event['n']}")