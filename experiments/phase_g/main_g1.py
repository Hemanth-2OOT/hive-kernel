import os
import time
from cortex import CortexRouter
from reservoir import Reservoir
from nucleus_executor import NucleusExecutor
from task_graph import TaskGraph, Task

def build_wide_dag():
    graph = TaskGraph()
    # Task 1: Root generates context
    graph.add_task(Task(1, "generate", [], "raw"))
    
    # Independent Branch 1: Embed
    graph.add_task(Task(2, "embed", [1], "dependency"))
    
    # Independent Branch 2: Classify sentiment
    graph.add_task(Task(3, "classify", [1], "dependency"))
    
    # Independent Branch 3: Verify sentiment
    graph.add_task(Task(4, "llm_verify", [1], "dependency"))
    
    # Final Sink: Summarize taking inputs from all branches
    graph.add_task(Task(5, "summarize", [2, 3, 4], "dependency"))
    return graph

def main():
    print("=== Hive Phase G1: Parallel DAG Execution ===")
    
    res = Reservoir(max_ram_mb=4000, idle_ttl_sec=300) 
    cortex = CortexRouter()
    nucleus = NucleusExecutor(res)
    nucleus.policy_validator.exploration_rate = 1.0 # Force no optimizations for test
    
    prompt = "I feel so alive today! The sun is shining and everything is perfect."
    print(f"\n[USER] {prompt}")
    
    graph = build_wide_dag()
    
    start_time = time.time()
    context = nucleus.execute(graph, prompt)
    end_time = time.time()
    
    print(f"\n[TEST] DAG Execution Latency: {end_time - start_time:.2f}s")
    
    res.shutdown()

if __name__ == "__main__":
    main()
