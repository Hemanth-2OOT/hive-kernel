import json
import time
from cortex import CortexRouter
from reservoir import Reservoir
from nucleus_executor import NucleusExecutor

def main():
    print("=== Hive Phase C2: End-to-End DAG Execution ===\n")
    
    # 1. Boot Reservoir (using 2000MB limit to prove eviction seamlessly works behind the scenes!)
    res = Reservoir(max_ram_mb=2000, idle_ttl_sec=300) 
    cortex = CortexRouter()
    nucleus = NucleusExecutor(res)
    
    # 2. User Intent
    user_request = "Generate a 1-sentence story about a happy robot, summarize it, and classify its sentiment."
    print(f"[USER REQUEST]: {user_request}\n")
    
    # 3. Routing
    graph = cortex.route(user_request)
    print("[CORTEX] Parsed DAG:")
    print(graph.to_json())
    print("\n--- Starting Execution ---")
    
    # 4. State-Driven Scheduling
    t0 = time.perf_counter()
    context = nucleus.execute(graph, user_request)
    t1 = time.perf_counter()
    
    print(f"\n--- Execution Complete in {t1-t0:.2f}s ---")
    print("\n[FINAL EXECUTION CONTEXT DUMP]")
    for t_id, data in context.results.items():
        print(f"\nTask {t_id} [{data['task_type'].upper()}]")
        print(f"Timestamp: {data['timestamp']}")
        print(f"Output: {data['output']}")
        
    res.shutdown()

if __name__ == "__main__":
    main()
