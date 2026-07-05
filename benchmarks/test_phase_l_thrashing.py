import time
import os
import threading
from hive.memory.hippocampus import Hippocampus
from hive.memory.verifier import SemanticVerifier, MemoryCandidate
from hive.runtime.reservoir import Reservoir
from hive.config import HiveConfig
from hive.core.nucleus import Nucleus
from hive.core.dag import TaskGraph, Task
import queue

def create_mock_workload():
    g = TaskGraph()
    # A single fast task that requests qwen2.5-coder:7b
    # Qwen will demand 4.9GB, which evicts Hermes (5.3GB) under 6.1GB max
    g.add_task(Task(1, "generate", [], "raw_input"))
    return g

def test_thrashing():
    config = HiveConfig()
    config.max_vram_mb = 6144
    reservoir = Reservoir(config)
    verifier = SemanticVerifier(reservoir, config=config)
    
    nucleus = Nucleus(reservoir, config)
    hippo = nucleus.hippocampus
    hippo._verifier = verifier
    # We must restart the worker because hippo was created before we attached the verifier!
    hippo._verifier_thread = threading.Thread(target=hippo._verifier_worker_loop, daemon=True)
    hippo._verifier_thread.start()
    
    import uuid
    for i in range(3):
        cand = MemoryCandidate(
            memory_id=f"thrash_{i}_{uuid.uuid4().hex[:8]}",
            content=f"Some text to verify {i} {uuid.uuid4().hex}",
            embedding_score=0.99,
            raw_memory={"_task_id": 0}
        )
        hippo._in_flight_verifications.add(cand.memory_id)
        hippo._verify_queue.put(("test query", cand, 0))

    print("[TEST] Verifier queue loaded with 3 items. Starting fast foreground loop...")
    
    for i in range(3):
        start_t = time.time()
        ctx = nucleus.execute(create_mock_workload(), f"Fast run {i}")
        duration = time.time() - start_t
        print(f"[TEST] Foreground DAG {i} completed in {duration:.2f}s")
        if i == 0:
            assert duration < 150, f"Foreground DAG {i} blocked for too long! ({duration:.2f}s)"
        else:
            assert duration < 150, f"Foreground DAG {i} blocked for too long! ({duration:.2f}s)"
        
    print("[TEST] Foreground burst complete. Waiting for background worker to hit ceilings or finish...")
    
    start_wait = time.time()
    while not hippo._verify_queue.empty() or len(hippo._in_flight_verifications) > 0:
        time.sleep(0.5)
        if time.time() - start_wait > 90:
            print("[TEST] Timeout waiting for background worker")
            break
            
    print(f"[TEST] In-flight verifications: {hippo._in_flight_verifications}")
    assert len(hippo._in_flight_verifications) == 0, "Memory leaked in in-flight set"
    
    print("[TEST] Thrashing test complete!")

if __name__ == "__main__":
    test_thrashing()
