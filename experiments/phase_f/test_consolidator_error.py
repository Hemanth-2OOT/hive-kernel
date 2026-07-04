import sys
from hive.core.nucleus import Nucleus
from hive.runtime.reservoir import Reservoir
from hive.core.dag import TaskGraph, Task

def main():
    print("=== Testing Consolidator Error Surfacing ===")
    res = Reservoir(max_vram_mb=6000, idle_ttl_sec=30)
    nuc = Nucleus(res)
    
    # Intentionally break the consolidator by mocking it to raise an error
    class BrokenConsolidator:
        def consolidate(self, trace):
            raise ValueError("Deliberate background failure: API rate limit exceeded")
            
    nuc.consolidator = BrokenConsolidator()
    
    graph = TaskGraph()
    graph.add_task(Task(1, "sentiment", [], "raw"))
    
    print("[Main] Executing DAG...")
    ctx = nuc.execute(graph, "I am so happy!")
    
    print("[Main] Execution complete. Caller received context.")
    
    if ctx.consolidation_thread:
        print("[Main] Waiting for background consolidation thread to finish...")
        ctx.consolidation_thread.join()
        
    if ctx.consolidation_error:
        print(f"[Main] SUCCESS: Caller successfully detected background error: {ctx.consolidation_error}")
        res.shutdown()
        sys.exit(0)
    else:
        print("[Main] FAILURE: Error was swallowed and caller is unaware.")
        res.shutdown()
        sys.exit(1)

if __name__ == "__main__":
    main()
