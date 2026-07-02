from cortex import CortexRouter
from reservoir import Reservoir
from nucleus_executor import NucleusExecutor

def main():
    print("=== Hive Phase D3A: Homeostatic Signals ===")
    
    # Intentionally constrained budget to force Reflex Evictions and Throttling
    # LLM(1500) + Sent(550) + Embed(400) = 2450. Max is 2600.
    # When 3 cells are active, memory pressure is 2450 / 2600 = 0.942 > 0.85
    # Congestion will hit 3/3 = 1.0 > 0.80 and 0.95
    res = Reservoir(max_ram_mb=2600, idle_ttl_sec=300) 
    cortex = CortexRouter()
    nucleus = NucleusExecutor(res)
    
    # We create a full DAG that requires all 3 cells to max out metrics simultaneously
    user_request = "Generate a story, classify its sentiment, and embed the text."
    print(f"\n[USER REQUEST]: {user_request}\n")
    
    graph = cortex.route(user_request)
    print("[CORTEX] Initial DAG:")
    print(graph.to_json())
    print("\n--- Starting Execution Stress Test ---")
    
    context = nucleus.execute(graph, user_request)
    
    print("\n--- Execution Complete ---")
    print("\nColony Aggregates:", context.aggregate_signals())
    
    res.shutdown()

if __name__ == "__main__":
    main()
