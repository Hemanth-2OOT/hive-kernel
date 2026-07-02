import os
from reservoir import Reservoir
from nucleus_executor import NucleusExecutor
from task_graph import TaskGraph, Task

def build_cascade_dag():
    graph = TaskGraph()
    # Task 1: A task marked as "reflex" that will fail with a non-OOM error.
    t1 = Task(1, "llm", [], "raw")
    t1.source = "reflex"
    graph.add_task(t1)
    
    # Task 2: A dependent task to test the cascade
    t2 = Task(2, "summarize", [1], "raw")
    graph.add_task(t2)
    
    return graph

def main():
    print("=== Phase D Audit: Verification 1 & 2 (Non-OOM Reflex Failure & Cascade) ===")
    
    if os.path.exists("data/episodic.jsonl"): os.remove("data/episodic.jsonl")
    if os.path.exists("data/semantic.npy"): os.remove("data/semantic.npy")
    if os.path.exists("data/semantic_meta.json"): os.remove("data/semantic_meta.json")
    
    # Large budget so no OOM occurs
    res = Reservoir(max_ram_mb=4000, idle_ttl_sec=300)
    nucleus = NucleusExecutor(res)
    
    prompt = "This is a test prompt. CRASH_LLM"
    
    print("\n--- PRE-SEED: Storing unrelated memory ---")
    nucleus.hippocampus.store_semantic(prompt, {"lesson": "A pristine memory."})
    
    graph = build_cascade_dag()
    
    try:
        context = nucleus.execute(graph, prompt)
    except Exception as e:
        print(f"Exception caught in harness: {e}")
        context = None
        
    print("\n--- RUN 2: Verification ---")
    unrelated_decay = nucleus.hippocampus.metadata[0].get("_decay_factor", 1.0)
    print(f"\nUnrelated Memory Decay: {unrelated_decay}")
    
    assert unrelated_decay == 1.0, f"BUG CONFIRMED: Misdirected Apoptosis! Decay dropped to {unrelated_decay}"
    assert context is not None, "Execution completely aborted instead of gracefully degrading!"
    
    # Check if Task 1 was FAILED
    t1_failed = False
    t2_failed = False
    for task_id, task_res in context.results.items():
        if task_id == 1 and task_res["status"] == "failed":
            t1_failed = True
        if task_id == 2 and task_res["status"] == "failed":
            t2_failed = True
            
    assert t1_failed, "Task 1 (reflex source) did not gracefully fail!"
    assert t2_failed, "Task 2 (dependent) did not cascade fail!"
    
    print("[TEST SUCCESS] Non-OOM reflex failure caught by source tracking, and dependent task gracefully cascaded!")
    
    res.shutdown()

if __name__ == "__main__":
    main()
