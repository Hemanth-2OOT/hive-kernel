import time
import queue
import concurrent.futures
from hive.core.dag import TaskGraph, Task
from hive.core.context import ExecutionContext
from hive.runtime.reservoir import Reservoir
from hive.runtime.signals import Signal
from hive.adaptation.reflex_engine import ReflexEngine
from hive.memory.hippocampus import Hippocampus
from hive.memory.consolidator import Consolidator
from hive.adaptation.oracle import Oracle
from hive.core.validator import PolicyValidator

# Semantic intent to physical Cell routing table
TASK_TO_CELL = {
    "generate": "llm",
    "summarize": "llm",
    "classify": "sentiment",
    "sentiment": "sentiment",
    "embed": "embedding",
    "llm_verify": "llm"
}

class Nucleus:
    def __init__(self, reservoir: Reservoir):
        self.reservoir = reservoir
        self.reflex_engine = ReflexEngine()
        self.hippocampus = Hippocampus(self.reservoir)
        self.consolidator = Consolidator()
        self.oracle = Oracle()
        self.policy_validator = PolicyValidator(self.hippocampus, exploration_rate=0.1)
        
    def execute(self, graph: TaskGraph, raw_input: str) -> ExecutionContext:
        context = ExecutionContext(raw_input)
        
        # 0. Hippocampus Recall
        print("[NUCLEUS] Recalling relevant memories from Hippocampus...")
        memories = self.hippocampus.recall_from_text(raw_input, top_k=2)
        if memories:
            for i, mem in enumerate(memories, 1):
                lesson_text = mem['memory'].get('lesson', '').replace('\n', ' ')
                decay = mem['memory'].get('_decay_factor', 1.0)
                print(f"  [MEMORY {i}] {lesson_text} (Score: {mem['score']:.2f}, Decay: {decay:.2f})")
        else:
            print("  [MEMORY] No relevant past experiences found.")
            
        # 0.5 Policy Validator Interception
        print("[NUCLEUS] PolicyValidator intercepting DAG...")
        try:
            graph = self.policy_validator.validate_and_mutate(graph, raw_input)
        except Exception as e:
            print(f"[NUCLEUS] Validator failed to process DAG: {e}")
        
        # Initialize Task States
        states = {}
        for t in graph.tasks:
            if not t.depends_on:
                states[t.id] = "READY"
            else:
                states[t.id] = "WAITING"
                
        tasks_by_id = {t.id: t for t in graph.tasks}
        
        completion_queue = queue.Queue()
        active_tasks = 0
        
        def worker_task(task: Task, payload: str):
            # Pure worker: no DAG mutation, no state mutation.
            cell_type = TASK_TO_CELL.get(task.type)
            try:
                if task.type == "summarize":
                    formatted_payload = f"Summarize the following text in exactly 5 words:\n{payload}"
                elif task.type == "generate":
                    formatted_payload = f"Write exactly one short sentence responding to this:\n{payload}"
                elif task.type == "llm_verify":
                    formatted_payload = f"A smaller sentiment model was highly confused by this text. Please carefully analyze its true sentiment and explain why:\n{payload}"
                else:
                    formatted_payload = payload
                    
                resp = self.reservoir.infer(cell_type, task.id, formatted_payload)
                if resp["status"] == "error":
                    completion_queue.put(("ERROR", task.id, Exception(resp.get('error'))))
                else:
                    completion_queue.put(("DONE", task.id, resp))
            except Exception as e:
                completion_queue.put(("ERROR", task.id, e))
                
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as thread_pool:
                while True:
                    # 1. Submit all READY tasks to worker pool
                    ready_tasks = [t_id for t_id, s in states.items() if s == "READY"]
                    for t_id in ready_tasks:
                        states[t_id] = "RUNNING"
                        task = tasks_by_id[t_id]
                        print(f"[NUCLEUS] Submitting Task {task.id} ({task.type}) to ThreadPool")
                        payload = context.resolve_payload(task)
                        active_tasks += 1
                        thread_pool.submit(worker_task, task, payload)
                        
                    # 2. Check completion
                    if active_tasks == 0 and all(s in ["DONE", "FAILED"] for s in states.values()):
                        break
                        
                    if active_tasks == 0:
                        raise RuntimeError(f"Dependency deadlock: states={states}")
                        
                    # WARNING: ARCHITECTURAL INVARIANT
                    # Do NOT move state mutation or DAG readiness checks out of this single-threaded loop!
                    # The safety of Phase C multi-dependency resolution completely relies on `self.completion_queue`
                    # serializing all thread completions. If multiple threads were allowed to mutate `states` concurrently,
                    # torn reads could occur where a downstream task fires prematurely.
                    
                    # 3. Event-driven wait
                    event_type, task_id, result = completion_queue.get()
                    
                    if event_type == "ERROR":
                        task = tasks_by_id[task_id]
                        if task.source == "reflex" or "Cannot free enough RAM" in str(result):
                            print(f"[NUCLEUS] Task {task.id} ({task.type}) failed: {result}. Gracefully degrading.")
                            states[task.id] = "FAILED"
                            context.add_failed_task(task.id, task.type, str(result))
                            active_tasks -= 1
                            
                            # Mark all downstream tasks as FAILED
                            changed = True
                            while changed:
                                changed = False
                                for t in graph.tasks:
                                    if states[t.id] == "WAITING":
                                        if any(states.get(dep) == "FAILED" for dep in t.depends_on):
                                            states[t.id] = "FAILED"
                                            context.add_failed_task(t.id, t.type, "Dependency failed")
                                            changed = True
                                            
                            # Unlock any remaining WAITING tasks whose dependencies are fully DONE
                            for t in graph.tasks:
                                if states[t.id] == "WAITING":
                                    if all(states.get(dep) == "DONE" for dep in t.depends_on):
                                        states[t.id] = "READY"
                            continue
                        else:
                            raise result
                        
                    elif event_type == "DONE":
                        active_tasks -= 1
                        resp = result
                        task = tasks_by_id[task_id]
                        
                        # Process metrics
                        telemetry = resp.get("telemetry", {})
                        context.update_metrics(
                            cold_started=telemetry.get("cold_start", False),
                            current_ram=self.reservoir.get_total_rss()
                        )
                        
                        system_signals = telemetry.get("system_signals", [])
                        worker_signals = telemetry.get("signals", [])
                        all_signals = worker_signals + system_signals
                        
                        for sig_data in all_signals:
                            is_system = sig_data.get("signal_type") in ["memory_pressure", "congestion", "latency_spike", "thrashing"]
                            source = None if is_system else task_id
                            
                            sig = Signal(
                                source_task_id=source,
                                signal_type=sig_data.get("signal_type"),
                                strength=sig_data.get("strength"),
                                metadata=sig_data.get("metadata", {})
                            )
                            context.add_signal(sig)
                            
                            # Scheduler Thread ONLY mutates DAG
                            mutations = self.reflex_engine.evaluate(sig)
                            for mut in mutations:
                                if mut["action"] == "spawn_task":
                                    new_task = Task(
                                        task_id=graph.get_next_task_id(),
                                        task_type=mut["task_type"],
                                        depends_on=mut["depends_on"],
                                        input_source=mut.get("input_source", "dependency"),
                                        source="reflex"
                                    )
                                    print(f"[NUCLEUS] REFLEX ACTION: Spawning Task {new_task.id} ({new_task.type})")
                                    graph.add_task(new_task)
                                    tasks_by_id[new_task.id] = new_task
                                    states[new_task.id] = "WAITING"
                                elif mut["action"] == "evict_low_priority_cell":
                                    try:
                                        victim = self.reservoir.select_victim()
                                        if victim:
                                            self.reservoir.evict_cell(victim)
                                            context.increment_evictions()
                                    except Exception:
                                        pass
                                elif mut["action"] == "throttle_low_priority_tasks":
                                    pass
                                    
                        context.add_result(task.id, task.type, resp["result"])
                        states[task.id] = "DONE"
                        print(f"[NUCLEUS] Completed Task {task.id} ({task.type})")
                        
                        # Unlock downstream
                        for t in graph.tasks:
                            if states[t.id] == "WAITING":
                                if all(states[dep] == "DONE" for dep in t.depends_on):
                                    states[t.id] = "READY"
                                    
            print("[NUCLEUS] Graph execution complete.")
            
            print("[NUCLEUS] Consulting Oracle for Meta-Cognition...")
            trace = context.serialize_trace()
            recommendations = self.oracle.analyze(trace, graph)
            if recommendations:
                trace["oracle_recommendations"] = recommendations
                for rec in recommendations:
                    print(f"  [ORACLE] {rec.get('description', str(rec))}")
                    
            print("[NUCLEUS] Consolidating Trace into Hippocampus...")
            lesson = self.consolidator.consolidate(trace)
            
            self.hippocampus.append_episode(trace)
            self.hippocampus.store_semantic(raw_input, lesson)
            
            return context
            
        except Exception as e:
            print(f"[NUCLEUS] Execution Failed: {e}")
            print(f"[NUCLEUS] Triggering Hippocampus Apoptosis (Decay)...")
            self.hippocampus.penalize_memory(raw_input, penalty=0.1)
            raise e
        finally:
            self.hippocampus.clear_cycle()
