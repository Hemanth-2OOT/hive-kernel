import time
import os
import signal
import subprocess
from hive.runtime.reservoir import Reservoir
from hive.core.nucleus import Nucleus
from hive.core.dag import TaskGraph, Task

def test_async_fail():
    print("=== Phase F: Async Consolidator Failure Test ===")
    res = Reservoir(max_vram_mb=6000, idle_ttl_sec=300)
    nucleus = Nucleus(res)
    
    graph = TaskGraph()
    graph.add_task(Task(task_id=1, task_type="generate", depends_on=[], input_source="dependency"))
    
    print("\n[MAIN] Starting execution...")
    context = nucleus.execute(graph, "Test async failure decoupling")
    print("\n[MAIN] execute() returned!")
    
    # We will kill Ollama manually while the embedding model is booting in the background
    print("[MAIN] Simulating crash by killing Ollama process mid-consolidation...")
    os.system("taskkill /F /IM ollama.exe /T >nul 2>&1")
    
    for i in range(5):
        time.sleep(1)
        print(f"[MAIN] Main thread alive... {i+1}s")
        
    # restart ollama for future tests
    subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    
    res.shutdown()

if __name__ == "__main__":
    test_async_fail()
