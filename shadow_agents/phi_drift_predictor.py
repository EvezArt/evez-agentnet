from collections import deque

class PhiDriftPredictor:
    def __init__(self, window=20, threshold=1.1):
        self.window = deque(maxlen=window)
        self.threshold = threshold

    def on_event(self, event):
        phi = event['phi']
        self.window.append(phi)

        if len(self.window) < 5:
            return

        phi_prev = self.window[-2]
        phi_curr = self.window[-1]

        predicted = 0.84 * phi_curr + 0.06 * (phi_curr - phi_prev)

        if predicted > self.threshold:
            print(f"[PREDICT] φ breach incoming → {predicted:.3f} at n={event['n']}")