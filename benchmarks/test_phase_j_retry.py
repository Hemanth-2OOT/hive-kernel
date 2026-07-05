import time
import concurrent.futures
from hive.config import HiveConfig
from hive.runtime.reservoir import Reservoir
from hive.runtime.reservoir import ReservoirContentionTimeout

def test_phase_j_retry():
    print("--- Testing Phase J Contention Retry Loop ---")
    config = HiveConfig()
    config.max_vram_mb = 6144
    res = Reservoir(config)
    
    # We will launch 4 threads that all try to acquire VRAM simultaneously.
    # qwen (4900) and hermes (5300) are mutually exclusive.
    # If 4 threads spam infer(), the contention logic will trigger.
    
    def worker(cell_type, task_id):
        try:
            print(f"Worker {task_id} requesting {cell_type}...")
            # We send a long payload to ensure it holds the lock for >10 seconds
            res.infer(cell_type, task_id, "Write a very detailed essay about the history of artificial intelligence, at least 500 words long.")
            print(f"Worker {task_id} finished {cell_type}.")
            return "SUCCESS"
        except Exception as e:
            print(f"Worker {task_id} FAILED: {e}")
            return str(e)
            
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for i in range(4):
            # alternate qwen and hermes
            cell = "qwen2.5-coder:7b" if i % 2 == 0 else "hermes3:8b"
            futures.append(executor.submit(worker, cell, i))
            # stagger starts slightly
            time.sleep(0.5)
            
        results = [f.result() for f in futures]
        
    failures = [r for r in results if r != "SUCCESS"]
    if failures:
        print(f"TEST FAILED: {len(failures)} workers crashed with uncaught exceptions!")
        for f in failures:
            print(f"  {f}")
    else:
        print("TEST PASSED: All workers succeeded through contention retries!")
        
    res.shutdown()

if __name__ == "__main__":
    main()
