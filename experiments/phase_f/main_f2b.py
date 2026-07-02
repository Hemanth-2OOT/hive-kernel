import os
from cortex import CortexRouter
from reservoir import Reservoir
from nucleus_executor import NucleusExecutor
from task_graph import TaskGraph, Task

def build_heavy_dag():
    graph = TaskGraph()
    # Task 1: Generate (LLM)
    graph.add_task(Task(1, "generate", [], "raw"))
    # Task 2: Embed - Unused output initially
    graph.add_task(Task(2, "embed", [], "raw"))
    return graph

def main():
    print("=== Hive Phase F2B: Swarm-Native Semantic Learning ===")
    
    # Ensure clean slate for test
    if os.path.exists("data/episodic.jsonl"): os.remove("data/episodic.jsonl")
    if os.path.exists("data/semantic.npy"): os.remove("data/semantic.npy")
    if os.path.exists("data/semantic_meta.json"): os.remove("data/semantic_meta.json")
    
    res = Reservoir(max_ram_mb=4000, idle_ttl_sec=300) 
    cortex = CortexRouter()
    nucleus = NucleusExecutor(res)
    # Ensure no stochastic exploration blocks our exact test
    nucleus.policy_validator.exploration_rate = 0.0
    
    prompt_a = "Can you describe the rainy weather?"
    
    print(f"\n--- RUN 1: Initial Experience (Creating Memory) ---")
    print(f"[USER] {prompt_a}")
    graph = build_heavy_dag()
    nucleus.execute(graph, prompt_a)
    
    print(f"\n--- RUN 2: Reinforcement (Retrieving & Applying Optimization) ---")
    print(f"[USER] {prompt_a}")
    graph = build_heavy_dag()
    nucleus.execute(graph, prompt_a)
    
    print(f"\n--- RUN 3: Poison Test (Applying Optimization causes crash) ---")
    print("[TEST] Restricting RAM to force a fatal crash and trigger memory penalization...")
    res.max_ram_mb = 100
    try:
        graph = build_heavy_dag()
        nucleus.execute(graph, prompt_a)
    except Exception as e:
        print(f"Exception caught in test harness: {e}")
        
    print(f"\n--- RUN 4: Verification (Checking Decay Factor) ---")
    print("[TEST] Memory should be heavily penalized now.")
    res.max_ram_mb = 4000
    
    # Assert Apoptosis actually worked by checking memory metadata
    # We inspect the raw metadata because a heavily decayed memory (e.g. 0.10) 
    # will be suppressed below the recall_from_text > 0.5 threshold!
    decayed = False
    print("\n[DEBUG] Dump of raw Hippocampus metadata in Run 4:")
    for i, meta in enumerate(nucleus.hippocampus.metadata):
        print(f"Memory {i}: Decay Factor = {meta.get('_decay_factor', 1.0)}")
        print(f"  Suggestions = {meta.get('optimization_suggestions', [])}")
        if "optimization_suggestions" in meta:
            if meta.get("_decay_factor", 1.0) < 1.0:
                decayed = True
                print(f"[TEST SUCCESS] Verified decay factor dropped to: {meta['_decay_factor']:.2f}")
                
    assert decayed, "Apoptosis decay mechanism failed to trigger!"
    
    graph = build_heavy_dag()
    nucleus.execute(graph, prompt_a)
    
    res.shutdown()

if __name__ == "__main__":
    main()
