import os
import time
from reservoir import Reservoir
from nucleus_executor import NucleusExecutor
from task_graph import TaskGraph, Task

def main():
    print("=== Phase G1 Audit: Concurrent Scheduler IPC Desync ===")
    
    # 1. Start Reservoir
    res = Reservoir(max_ram_mb=4000, idle_ttl_sec=300)
    nucleus = NucleusExecutor(res)
    
    # Run 1: Two parallel tasks
    graph1 = TaskGraph()
    t1 = Task(1, "generate", [], "raw")
    t2 = Task(2, "generate", [], "raw")
    graph1.add_task(t1)
    graph1.add_task(t2)
    
    print("\n--- RUN 1: Concurrent execution with mid-flight crash ---")
    prompt1 = "Apples CRASH_CLIENT_MIDFLIGHT"
    
    try:
        context1 = nucleus.execute(graph1, prompt1)
    except Exception as e:
        print(f"\n[HARNESS] Caught expected mid-flight crash: {e}")
        context1 = None
    
    print("\n--- RUN 2: Sequential verification of permanent corruption ---")
    # Task 3 should get Task 2's output
    graph2 = TaskGraph()
    t3 = Task(3, "generate", [], "raw")
    graph2.add_task(t3)
    
    prompt2 = "Bananas"
    context2 = nucleus.execute(graph2, prompt2)
    
    # Task 4 should get Task 3's output
    graph3 = TaskGraph()
    t4 = Task(4, "generate", [], "raw")
    graph3.add_task(t4)
    
    prompt3 = "Carrots"
    context3 = nucleus.execute(graph3, prompt3)
    
    print("\n[DEBUG] IPC Stream Results:")
    task3_result_text = context2.results.get(3, {}).get("output", {}).get("text", "")
    task4_result_text = context3.results.get(4, {}).get("output", {}).get("text", "")
    
    print(f"Task 3 (Should be Bananas): {task3_result_text}")
    print(f"Task 4 (Should be Carrots): {task4_result_text}")
    
    # Task 3 should receive its OWN output, so it should start with [RESPONSE TO TASK 3]
    assert "[RESPONSE TO TASK 3]" in task3_result_text, f"BUG STILL PRESENT (1/2): IPC Desync! Task 3 read wrong output: {task3_result_text}"
    
    # Task 4 should receive its OWN output, so it should start with [RESPONSE TO TASK 4]
    assert "[RESPONSE TO TASK 4]" in task4_result_text, f"BUG STILL PRESENT (2/2): IPC Desync cascaded! Task 4 read wrong output: {task4_result_text}"
    
    print("[TEST SUCCESS] IPC Stream is synchronized correctly.")
    
    res.shutdown()

if __name__ == "__main__":
    main()
