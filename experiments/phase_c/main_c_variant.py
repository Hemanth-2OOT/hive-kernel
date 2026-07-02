import os
from reservoir import Reservoir
from nucleus_executor import NucleusExecutor
from task_graph import TaskGraph, Task

def main():
    print("=== Phase C Audit: Failed Dependency Cascade ===")
    res = Reservoir(max_ram_mb=4000, idle_ttl_sec=300)
    nucleus = NucleusExecutor(res)
    
    # We construct a DAG where Task 1 is guaranteed to fail, and Task 2 depends on it.
    # We tag Task 1 with source="reflex" so it fails gracefully without crashing the executor.
    graph = TaskGraph()
    t1 = Task(1, "generate", [], "raw", source="reflex")
    t2 = Task(2, "summarize", [1], "dependency", source="user")
    graph.add_task(t1)
    graph.add_task(t2)
    
    # The "CRASH_CLIENT_MIDFLIGHT" payload will trigger the exception hook we added to Reservoir.
    # This guarantees a hard failure.
    print("\n[TEST] Running DAG with guaranteed graceful failure in Task 1...")
    context = nucleus.execute(graph, "CRASH_CLIENT_MIDFLIGHT")
    
    t1_status = context.results.get(1, {}).get("status")
    t2_status = context.results.get(2, {}).get("status")
    
    t1_failed = context.results.get(1, {}).get("error")
    t2_failed = context.results.get(2, {}).get("error")
    
    print(f"\n[DEBUG] Task 1 Status (Expected 'failed'): {t1_status}")
    print(f"[DEBUG] Task 1 Failed Reason: {t1_failed}")
    
    print(f"[DEBUG] Task 2 Status (Expected 'failed' because it cascaded): {t2_status}")
    print(f"[DEBUG] Task 2 Failed Reason: {t2_failed}")
    
    assert t1_status == "failed", f"Task 1 should be failed, got {t1_status}"
    assert t1_failed is not None, "Task 1 should have an error string!"
    
    assert t2_status == "failed", f"[AUDIT FAIL] Task 2 executed despite Task 1 failing! Status: {t2_status}"
    assert t2_failed == "Dependency failed", f"[AUDIT FAIL] Task 2 did not cascade correctly! Reason: {t2_failed}"
    
    print("\n[AUDIT SUCCESS] Phase C Graceful Cascade is fully functional. Task 2 correctly inherited the FAILED state and skipped execution.")
    res.shutdown()

if __name__ == "__main__":
    main()
