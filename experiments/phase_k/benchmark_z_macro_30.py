import time
import os
import psutil
import json
from hive.runtime.reservoir import Reservoir
from hive.core.nucleus import Nucleus
from hive.core.dag import TaskGraph, Task
from hive.memory.verifier import SemanticVerifier
from hive.config import HiveConfig

def measure_rss():
    process = psutil.Process(os.getpid())
    mem = process.memory_info().rss
    for child in process.children(recursive=True):
        try:
            mem += child.memory_info().rss
        except psutil.NoSuchProcess:
            pass
    return mem / (1024 * 1024)

def create_workload_a():
    g = TaskGraph()
    g.add_task(Task(1, "generate", [], "raw_input"))
    g.add_task(Task(2, "classify", [1], "dependency"))
    g.add_task(Task(3, "summarize", [2], "dependency"))
    return g

def create_workload_b():
    g = TaskGraph()
    g.add_task(Task(1, "generate", [], "raw_input"))
    g.add_task(Task(2, "embed", [1], "dependency"))
    g.add_task(Task(3, "classify", [1], "dependency"))
    g.add_task(Task(4, "llm_verify", [1], "dependency"))
    g.add_task(Task(5, "summarize", [2, 3, 4], "dependency"))
    return g

def run_macro_benchmark(iterations=30):
    print(f"--- Macrobenchmark (n={iterations}) ---")
    results = {"workload_a": [], "workload_b": []}
    
    config = HiveConfig(max_vram_mb=6144)
    res = Reservoir(config)
    verifier = SemanticVerifier(res)
    nuc = Nucleus(res, config)
    nuc.hippocampus._verifier = verifier
    
    print("Running Workload A...")
    for i in range(iterations):
        start_time = time.time()
        nuc.execute(create_workload_a(), "Analyze the sentiment of standard input.")
        latency = time.time() - start_time
        results["workload_a"].append(latency)
        print(f"  [A {i+1:02d}/{iterations}] {latency:.2f}s")
        
    print("Running Workload B...")
    for i in range(iterations):
        start_time = time.time()
        nuc.execute(create_workload_b(), "Generate a parallel sentiment analysis pipeline.")
        latency = time.time() - start_time
        results["workload_b"].append(latency)
        print(f"  [B {i+1:02d}/{iterations}] {latency:.2f}s")
        
    res.shutdown()
    
    # Calculate stats
    for w_name, data in results.items():
        data.sort()
        mean = sum(data) / len(data)
        stdev = (sum((x - mean) ** 2 for x in data) / len(data)) ** 0.5
        p50 = data[len(data)//2]
        p95 = data[int(len(data)*0.95)]
        print(f"\nStats for {w_name}:")
        print(f"  Mean:  {mean:.2f}s")
        print(f"  p50:   {p50:.2f}s")
        print(f"  p95:   {p95:.2f}s")
        print(f"  Stdev: {stdev:.2f}s")
        
    output_path = os.path.join(os.path.dirname(__file__), "results", "macrobenchmark_30.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults written to {output_path}")

if __name__ == "__main__":
    run_macro_benchmark(30)
