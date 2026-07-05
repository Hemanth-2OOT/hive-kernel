import time
from hive.config import HiveConfig
from hive.runtime.reservoir import Reservoir
from hive.core.nucleus import Nucleus
from hive.core.dag import TaskGraph, Task
from hive.memory.verifier import SemanticVerifier

def create_workload_a():
    g = TaskGraph()
    g.add_task(Task(1, "generate", [], "raw_input"))
    g.add_task(Task(2, "classify", [1], "dependency"))
    g.add_task(Task(3, "summarize", [2], "dependency"))
    return g

def main():
    print("Running Tail Latency Detective for Workload A...")
    config = HiveConfig(max_vram_mb=6144)
    res = Reservoir(config)
    verifier = SemanticVerifier(res)
    nuc = Nucleus(res, config)
    nuc.hippocampus._verifier = verifier
    
    for i in range(30):
        start_time = time.time()
        ctx = nuc.execute(create_workload_a(), "Analyze the sentiment of standard input.")
        latency = time.time() - start_time
        
        # Extract task durations and output lengths
        trace = ctx.serialize_trace()
        t1 = trace["results"].get(1, {})
        t2 = trace["results"].get(2, {})
        t3 = trace["results"].get(3, {})
        
        print(f"Iteration {i+1}: Total {latency:.2f}s")
        if latency > 40:
            print(f"  [SPIKE DETECTED!] Latency: {latency:.2f}s")
        
        if "output" in t1 and isinstance(t1["output"], dict):
            out_len = len(str(t1["output"].get("text", "")))
            print(f"  Qwen (Task 1): Len={out_len}")
        if "output" in t3 and isinstance(t3["output"], dict):
            out_len = len(str(t3["output"].get("text", "")))
            print(f"  Hermes (Task 3): Len={out_len}")
            
    res.shutdown()

if __name__ == "__main__":
    main()
