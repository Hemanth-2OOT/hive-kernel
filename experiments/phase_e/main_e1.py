import os
from cortex import CortexRouter
from reservoir import Reservoir
from nucleus_executor import NucleusExecutor

def main():
    print("=== Hive Phase E1: Hippocampus Memory System ===")
    
    # Ensure clean slate for test
    if os.path.exists("data/episodic.jsonl"):
        os.remove("data/episodic.jsonl")
    if os.path.exists("data/semantic.npy"):
        os.remove("data/semantic.npy")
    if os.path.exists("data/semantic_meta.json"):
        os.remove("data/semantic_meta.json")
    
    res = Reservoir(max_ram_mb=4096, idle_ttl_sec=300) 
    cortex = CortexRouter()
    nucleus = NucleusExecutor(res)
    
    prompts = [
        "Classify this: I feel sad when it rains.",
        "Classify this: Rain makes me depressed.",
        "Classify this: The rainy weather ruins my mood."
    ]
    
    print("\n--- Phase 1: Experiencing & Consolidating ---")
    for i, p in enumerate(prompts, 1):
        print(f"\n[RUN {i}] Input: {p}")
        graph = cortex.route(p)
        nucleus.execute(graph, p)
        
    print("\n--- Phase 2: Testing Semantic Recall ---")
    test_prompt = "Classify this: I hate rainy days, they make me cry."
    print(f"\n[TEST RUN] Input: {test_prompt}")
    graph = cortex.route(test_prompt)
    nucleus.execute(graph, test_prompt)
    
    res.shutdown()

if __name__ == "__main__":
    main()
