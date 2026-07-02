from cortex import CortexRouter
from reservoir import Reservoir
from nucleus_executor import NucleusExecutor

def main():
    print("=== Hive Phase D2: Dynamic DAG Mutation ===")
    
    res = Reservoir(max_ram_mb=4096, idle_ttl_sec=300) 
    cortex = CortexRouter()
    nucleus = NucleusExecutor(res)
    
    # We use the FORCE_AMBIGUITY payload to trigger the 0.55 confidence score -> 0.90 ambiguity signal
    user_request = "Classify this: Testing the reflex engine mutation directly. FORCE_AMBIGUITY"
    
    print(f"\n[USER REQUEST]: {user_request}\n")
    
    graph = cortex.route(user_request)
    print("[CORTEX] Initial DAG:")
    print(graph.to_json())
    print("\n--- Starting Execution ---")
    
    context = nucleus.execute(graph, user_request)
    
    print("\n--- Execution Complete ---")
    
    print("\n[FINAL MUTATED DAG STRUCTURE]")
    print(graph.to_json())
    
    print("\n[FINAL EXECUTION CONTEXT DUMP]")
    for t_id, data in context.results.items():
        print(f"\nTask {t_id} [{data['task_type'].upper()}]")
        print(f"Output: {data['output']}")
        
    res.shutdown()

if __name__ == "__main__":
    main()
