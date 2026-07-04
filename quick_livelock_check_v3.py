import time
import threading
from hive.config import HiveConfig
from hive.runtime.reservoir import Reservoir

def test_step_3():
    print("--- STEP 3: Normal DAG Path Contention ---")
    config = HiveConfig(max_vram_mb=5500, idle_ttl_sec=30)
    res = Reservoir(config)
    
    print("Setup: Thread A wants qwen2.5-coder:7b (4900MB).")
    print("Setup: Thread B wants hermes3:8b (5300MB).")
    print("Budget: 5500MB. Only one can be loaded at a time.")
    
    start_time = time.time()
    
    def thread_a():
        print("[Thread A] Requesting qwen2.5-coder:7b...")
        try:
            res.infer("qwen2.5-coder:7b", 1, "Hello from A")
            print(f"[Thread A] Finished in {time.time() - start_time:.2f}s")
        except Exception as e:
            print(f"[Thread A] Error: {e}")

    def thread_b():
        print("[Thread B] Requesting hermes3:8b...")
        try:
            res.infer("hermes3:8b", 2, "Hello from B")
            print(f"[Thread B] Finished in {time.time() - start_time:.2f}s")
        except Exception as e:
            print(f"[Thread B] Error: {e}")

    t1 = threading.Thread(target=thread_a)
    t2 = threading.Thread(target=thread_b)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()
    
    print(f"\n[MAIN] Both threads finished normally. Total time: {time.time() - start_time:.2f}s")

if __name__ == "__main__":
    test_step_3()
