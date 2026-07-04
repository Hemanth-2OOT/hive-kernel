import time
from hive.runtime.reservoir import Reservoir
from hive.core.nucleus import Nucleus
from hive.core.dag import TaskGraph, Task

def test_async_decoupling():
    print("=== Phase F: Async Consolidator Decoupling Test ===")
    res = Reservoir(max_vram_mb=6000, idle_ttl_sec=300)
    nucleus = Nucleus(res)
    
    # We create a simple graph with a single task
    # We will simulate a slow consolidation by mocking the consolidator slightly,
    # or just let it do an embedding which takes a few seconds naturally.
    
    graph = TaskGraph()
    graph.add_task(Task(task_id=1, task_type="generate", depends_on=[], input_source="dependency"))
    
    print("\n[MAIN] Starting execution...")
    start_time = time.time()
    
    # Run the DAG
    context = nucleus.execute(graph, "Test async decoupling")
    
    exec_end_time = time.time()
    print(f"\n[MAIN] execute() returned! Time elapsed: {exec_end_time - start_time:.2f}s")
    
    print("[MAIN] Doing other work while consolidation finishes in background...")
    for i in range(5):
        time.sleep(1)
        print(f"[MAIN] Main thread alive... {i+1}s")
        
    res.shutdown()

if __name__ == "__main__":
    test_async_decoupling()
