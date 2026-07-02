from hive.core.dag import Task, TaskGraph

class CortexRouter:
    def __init__(self):
        # Known intents supported by the system
        self.known_intents = ["sentiment", "summarize", "embed", "generate", "classify"]
        
        # Dependency resolution rules (DAG mapping)
        # What a task inherently depends on IF the upstream task is also present
        self.rules = {
            "sentiment": ["summarize"],
            "classify": ["summarize"],
            "embed": ["summarize", "generate"],
            "summarize": ["generate"],
            "generate": []
        }
        
        # Topological ordering weights to assign IDs sequentially from source to sink
        self.order_map = {
            "generate": 0,
            "summarize": 1,
            "sentiment": 2,
            "classify": 2,
            "embed": 3
        }

    def route(self, raw_input: str) -> TaskGraph:
        raw_lower = raw_input.lower()
        
        # 1. Identify intents
        found_intents = []
        for intent in self.known_intents:
            if intent in raw_lower:
                found_intents.append(intent)
                
        # 2. Sort topologically so dependencies are assigned IDs first
        found_intents.sort(key=lambda x: self.order_map.get(x, 99))
        
        # 3. Build graph
        graph = TaskGraph()
        intent_to_id = {}
        next_id = 1
        
        for intent in found_intents:
            depends_on = []
            
            # Resolve data dependencies based on our DAG rules
            for required_intent in self.rules.get(intent, []):
                if required_intent in intent_to_id:
                    depends_on.append(intent_to_id[required_intent])
            
            # Explicitly mark input source
            input_source = "dependency" if len(depends_on) > 0 else "raw"
            
            task = Task(
                task_id=next_id,
                task_type=intent,
                depends_on=depends_on,
                input_source=input_source
            )
            
            graph.add_task(task)
            intent_to_id[intent] = next_id
            next_id += 1
            
        return graph
