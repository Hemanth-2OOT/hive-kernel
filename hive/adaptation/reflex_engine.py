from hive.runtime.signals import Signal

class ReflexEngine:
    def __init__(self):
        pass
        
    def evaluate(self, signal: Signal) -> list[dict]:
        actions = []
        
        # Rule 1: Ambiguity Reflex (Phase D2)
        if signal.signal_type == "ambiguity" and signal.strength > 0.7:
            actions.append({
                "action": "spawn_task",
                "task_type": "llm_verify",
                "depends_on": [signal.source_task_id] if signal.source_task_id else [],
                "input_source": "raw"
            })
            
        # Rule 2: Memory Pressure Reflex (Phase D3A)
        if signal.signal_type == "memory_pressure" and signal.strength > 0.85:
            actions.append({
                "action": "evict_low_priority_cell"
            })
            
        # Rule 3: Congestion Reflexes (Phase D3A)
        if signal.signal_type == "congestion" and signal.strength > 0.80:
            actions.append({
                "action": "throttle_low_priority_tasks"
            })
            
        if signal.signal_type == "congestion" and signal.strength > 0.95:
            actions.append({
                "action": "duplicate_requested"
            })
            
        return actions
