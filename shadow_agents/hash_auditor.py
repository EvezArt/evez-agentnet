class HashAuditor:
    def __init__(self):
        self.seen_hashes = set()

    def on_event(self, event):
        h = event['hash_id']

        if h in self.seen_hashes:
            print(f"[WARNING] Duplicate hash detected: {h}")
        else:
            self.seen_hashes.add(h)

        if not h.startswith('sha256'):
            print(f"[ERROR] Invalid hash format at n={event['n']}")