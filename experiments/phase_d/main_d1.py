from cortex import CortexRouter
from reservoir import Reservoir
from nucleus_executor import NucleusExecutor

def main():
    print("=== Hive Phase D1: Stigmergy Signals ===")
    
    res = Reservoir(max_ram_mb=4096, idle_ttl_sec=300) 
    cortex = CortexRouter()
    nucleus = NucleusExecutor(res)
    
    ambiguous_inputs = [
        "This movie was okay I guess, neither good nor bad.",
        "The food was extremely average, not terrible but I won't return.",
        "I absolutely loved it! It was amazing.", # High confidence, no signal expected
        "Testing the stigmergy signal directly. FORCE_AMBIGUITY"
    ]
    
    for i, text in enumerate(ambiguous_inputs, 1):
        # We prefix with "Classify this:" to trigger the "classify" route in Cortex
        user_request = f"Classify this: {text}"
        print(f"\n--- Run {i} ---")
        print(f"Input: {text}")
        
        graph = cortex.route(user_request)
        context = nucleus.execute(graph, user_request)
        
        # Print results
        print("\nResults:")
        for t_id, data in context.results.items():
            print(f"  Task {t_id} ({data['task_type']}) Output: {data['output']}")
            
        signals = context.get_signals()
        print("\nSignals:")
        if signals:
            for s in signals:
                print(f"  -> {s.signal_type.upper()} (Strength: {s.strength:.2f}) [Source Task {s.source_task_id}]")
        else:
            print("  No signals emitted.")
            
        print("\nColony Aggregates:", context.aggregate_signals())
        
    res.shutdown()

if __name__ == "__main__":
    main()
