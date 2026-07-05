import time
from hive.runtime.reservoir import Reservoir
from hive.core.nucleus import Nucleus
from hive.core.dag import TaskGraph, Task
from hive.config import HiveConfig

def create_workload_a():
    g = TaskGraph()
    g.add_task(Task(1, "generate", [], "raw_input"))
    g.add_task(Task(2, "classify", [1], "dependency"))
    g.add_task(Task(3, "summarize", [2], "dependency"))
    return g

def main():
    print("Running Workload A until tail latency (>50s) occurs...")
    config = HiveConfig(max_vram_mb=6144)
    res = Reservoir(config)
    nuc = Nucleus(res, config)
    
    for i in range(1, 31):
        print(f"--- Iteration {i} ---")
        start_time = time.time()
        try:
            nuc.execute(create_workload_a(), "Analyze the sentiment of standard input.")
            latency = time.time() - start_time
            print(f"Latency: {latency:.2f}s")
            if latency > 50.0:
                print(f"TAIL LATENCY DETECTED at iteration {i}: {latency:.2f}s")
                break
        except Exception as e:
            print(f"Failed at iteration {i}: {e}")
            break
            
    res.shutdown()

if __name__ == "__main__":
    main()
