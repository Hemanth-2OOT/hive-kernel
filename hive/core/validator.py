import random
from hive.core.dag import TaskGraph, Task
from hive.memory.hippocampus import Hippocampus
from hive.config import HiveConfig

class PolicyValidator:
    def __init__(self, hippocampus: Hippocampus, config: HiveConfig = None):
        self.hippocampus = hippocampus
        self.config = config or HiveConfig()
        self.exploration_rate = self.config.exploration_rate
        
    def validate_and_mutate(self, graph: TaskGraph, raw_input: str) -> TaskGraph:
        if random.random() < self.exploration_rate:
            print("[VALIDATOR] Stochastic exploration triggered. Ignoring optimizations.")
            return graph
            
        # Stage 1 + Stage 2 retrieval
        verified_memories = self.hippocampus.query_verified(raw_input, task_id=0)
        if not verified_memories:
            return graph
        suggestions = []
        for v_mem in verified_memories:
            raw = v_mem.raw_memory
            if "optimization_suggestions" in raw:
                suggestions.extend(raw["optimization_suggestions"])
                
        if not suggestions:
            return graph
            
        new_graph = self._clone_graph(graph)
        
        for sugg in suggestions:
            if sugg.get("action") == "remove_task":
                target_type = sugg.get("target_task")
                
                if len(new_graph.tasks) <= 1:
                    print(f"[VALIDATOR] Rejecting {target_type} removal: Empty graph guarantee (Sink preservation).")
                    continue
                    
                target_node = next((t for t in new_graph.tasks if t.type == target_type), None)
                if not target_node:
                    continue
                    
                has_consumers = any(target_node.id in t.depends_on for t in new_graph.tasks)
                if has_consumers:
                    print(f"[VALIDATOR] Rejecting {target_type} removal: Has downstream consumers (Sink preservation).")
                    continue
                    
                print(f"[VALIDATOR] Applying optimization: Removing {target_type} task.")
                new_graph.tasks.remove(target_node)
                
        return new_graph
        
    def _clone_graph(self, graph: TaskGraph) -> TaskGraph:
        new_graph = TaskGraph()
        for t in graph.tasks:
            new_graph.add_task(Task(t.id, t.type, list(t.depends_on), t.input_source))
        return new_graph
