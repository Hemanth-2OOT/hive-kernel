import sys
import json
from hive import run, shutdown

def main():
    print("=== Re-verifying Phase D Reflex Logic with Temp 0.0 ===")
    
    # We want to trigger a task that leads to an llm_verify failure, 
    # but first let's just make sure llm_verify deterministic behavior works.
    
    from hive.core.dag import TaskGraph, Task
    from hive.api import run, shutdown
    import hive.api as api
    
    # We must explicitly build the DAG since Cortex might route this randomly.
    graph = TaskGraph()
    graph.add_task(Task(1, "sentiment", [], "raw"))
    
    # Initialize engine
    res = run("init") # just to init the default engine
    engine = api._default_engine
    
    prompt = "I guess it was fine but also terrible. Whatever. FORCE_AMBIGUITY"
    print(f"\n[Test] Running prompt: {prompt}")
    context = engine.nucleus.execute(graph, prompt)
    print("\n[Test] Execution completed.")
    
    context.wait_for_consolidation()
    
    # Check if llm_verify ran and failed
    llm_verify_ran = False
    llm_verify_failed = False
    for task_id, task_res in context.results.items():
        if task_res["task_type"] == "llm_verify":
            llm_verify_ran = True
            if task_res["status"] == "failed":
                llm_verify_failed = True
            print(f"[Test] llm_verify result: {task_res}")

    if not llm_verify_ran:
        print("[Test] FAILED: llm_verify did not run. Check ReflexEngine.")
    elif not llm_verify_failed:
        print("[Test] WARNING: llm_verify passed instead of failing.")
    else:
        print("[Test] SUCCESS: llm_verify deterministically failed as expected.")

    shutdown()

if __name__ == "__main__":
    main()
