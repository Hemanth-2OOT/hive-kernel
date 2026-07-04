import os
from hive.runtime.reservoir import Reservoir
from hive.core.nucleus import Nucleus
from hive.core.dag import TaskGraph, Task
from hive.config import HiveConfig

def build_sentiment_dag():
    graph = TaskGraph()
    # Task 1: Sentiment (550MB) - fits in 600MB
    graph.add_task(Task(1, "sentiment", [], "raw"))
    return graph

def main():
    print("=== Phase D Audit: Reflex Engine Adversarial Test ===")
    
    if os.path.exists("data/episodic.jsonl"): os.remove("data/episodic.jsonl")
    if os.path.exists("data/semantic.npy"): os.remove("data/semantic.npy")
    if os.path.exists("data/semantic_meta.json"): os.remove("data/semantic_meta.json")
    
    # 1. Start Reservoir with 600MB budget.
    config = HiveConfig(max_vram_mb=600, idle_ttl_sec=300)
    res = Reservoir(config)
    nucleus = Nucleus(res)
    
    prompt = "I guess it was fine but also terrible. Whatever. FORCE_AMBIGUITY"
    
    # Pre-seed the Hippocampus with a pristine semantic memory for this exact prompt.
    print("\n--- PRE-SEED: Storing unrelated memory ---")
    nucleus.hippocampus.store_semantic(prompt, {"lesson": "A perfectly innocent memory about this text."})
    
    # 2. Run adversarial prompt
    print("\n--- RUN 1: Provoking Reflex Engine under Starvation ---")
    prompt = "I guess it was fine but also terrible. Whatever. FORCE_AMBIGUITY" # This triggers 'ambiguity' signal from sentiment
    graph = build_sentiment_dag()
    
    # We expect this to run Task 1 (sentiment), trigger ambiguity, spawn llm_verify, and OOM.
    # But now, we expect graceful degradation, meaning it shouldn't raise an exception globally!
    try:
        context = nucleus.execute(graph, prompt)
    except Exception as e:
        print(f"Exception caught in harness (expected if bug exists): {e}")
        context = None
        
    print("\n--- RUN 2: Verification ---")
    memories = nucleus.hippocampus.recall_from_text(prompt, top_k=1)
    
    print("\n[DEBUG] Hippocampus Metadata Dump:")
    for i, meta in enumerate(nucleus.hippocampus.metadata):
        print(f"Memory {i}: Decay = {meta.get('_decay_factor', 1.0)}, Lesson = {meta.get('lesson')}")
        
    # Check if memory is penalized
    unrelated_decay = nucleus.hippocampus.metadata[0].get("_decay_factor", 1.0)
    
    print(f"\nUnrelated Memory Decay: {unrelated_decay}")
    assert unrelated_decay == 1.0, f"BUG CONFIRMED: Misdirected Apoptosis! Decay dropped to {unrelated_decay}"
    
    assert context is not None, "Execution completely aborted instead of gracefully degrading!"
    
    # Check if llm_verify was marked FAILED
    llm_verify_failed = False
    for task_id, task_res in context.results.items():
        if task_res["task_type"] == "llm_verify" and task_res["status"] == "failed":
            llm_verify_failed = True
            
    assert llm_verify_failed, "llm_verify was not marked as FAILED in context!"
    
    print("[TEST SUCCESS] Unrelated memory remained intact. Graceful degradation succeeded.")
    
    res.shutdown()

if __name__ == "__main__":
    main()
