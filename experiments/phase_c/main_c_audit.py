import os
import threading
from reservoir import Reservoir
from nucleus_executor import NucleusExecutor
from task_graph import TaskGraph, Task

def test_race_condition(iteration: int) -> bool:
    print(f"\n=== Iteration {iteration} / 15 ===")
    res = Reservoir(max_ram_mb=4000, idle_ttl_sec=300)
    
    # Force both worker threads (for Task 1 and Task 2) to block and return simultaneously
    # This guarantees maximum contention on the completion_queue and readiness logic!
    barrier = threading.Barrier(2)
    res.debug_barrier = barrier
    res.debug_barrier_tasks = [1, 2]
    
    nucleus = NucleusExecutor(res)
    
    # Turn off Reflex logic for this test to avoid noise
    nucleus.reflex_engine.evaluate = lambda x: []
    nucleus.hippocampus.recall_from_text = lambda x, top_k: []
    nucleus.oracle.analyze = lambda x, y: []
    nucleus.consolidator.consolidate = lambda x: {"lesson": "Test"}
    
    graph = TaskGraph()
    t1 = Task(1, "generate", [], "raw")
    t2 = Task(2, "embed", [], "raw")
    t3 = Task(3, "summarize", [1, 2], "dependency")
    graph.add_task(t1)
    graph.add_task(t2)
    graph.add_task(t3)
    
    try:
        context = nucleus.execute(graph, "TESTING_RACE")
    except Exception as e:
        print(f"[FAIL] Execution crashed: {e}")
        res.shutdown()
        return False
        
    t1_done = context.results.get(1, {}).get("status") == "done"
    t2_done = context.results.get(2, {}).get("status") == "done"
    t3_done = context.results.get(3, {}).get("status") == "done"
    
    res.shutdown()
    
    if not (t1_done and t2_done and t3_done):
        print(f"[FAIL] Not all tasks completed! T1:{t1_done} T2:{t2_done} T3:{t3_done}")
        return False
        
    t3_output = context.results.get(3, {}).get("output", {}).get("text", "")
    print(f"[SUCCESS] Task 3 output: {t3_output}")
    return True

def main():
    print("=== Phase C Audit: Multi-Dependency Race Condition (Forced Contention) ===")
    
    successes = 0
    total = 15
    for i in range(1, total + 1):
        passed = test_race_condition(i)
        if passed:
            successes += 1
        else:
            print(f"!!! FAILED on iteration {i} !!!")
            break
            
    print(f"\n=== TEST RUN COMPLETE ===")
    print(f"Passed {successes} / {total} iterations under forced contention.")
    
    if successes == total:
        print("[AUDIT SUCCESS] Phase C Dependency Resolution is ROCK SOLID against race conditions.")
        print("Because the ThreadPoolExecutor queues completions into a single-threaded queue.Queue(),")
        print("all DAG mutations and readiness checks are perfectly serialized.")
    else:
        print("[AUDIT FAILED] Race condition detected!")

if __name__ == "__main__":
    main()
