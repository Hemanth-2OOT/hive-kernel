import time

class Signal:
    def __init__(self, source_task_id, signal_type: str, strength: float, metadata: dict = None):
        self.source_task_id = source_task_id
        self.signal_type = signal_type
        self.strength = float(strength)
        self.metadata = metadata or {}
        self.created_at = time.time()

    def to_dict(self):
        return {
            "source_task_id": self.source_task_id,
            "signal_type": self.signal_type,
            "strength": self.strength,
            "metadata": self.metadata,
            "created_at": self.created_at
        }
