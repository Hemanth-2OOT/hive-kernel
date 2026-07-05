import threading
import time
import os
import sys

from hive.memory.hippocampus import Hippocampus
from hive.config import HiveConfig

class MockReservoir:
    def infer(self, cell_type, task_id, text):
        import numpy as np
        return {
            "status": "success",
            "result": {
                "vector": np.random.rand(1536).tolist()
            }
        }

def worker(hip, thread_id):
    for i in range(10):
        text = f"Memory from thread {thread_id} iter {i}"
        hip.store_semantic(text, {"source": "test", "tid": thread_id, "iter": i})
        # Simulate some read/penalize operations
        hip.penalize_memory(text, penalty=0.5, task_id=thread_id)

def main():
    print("=== Phase I: Semantic Memory Atomic Write Chaos Test ===")
    
    if os.path.exists("data/semantic.npy"): os.remove("data/semantic.npy")
    if os.path.exists("data/semantic_meta.json"): os.remove("data/semantic_meta.json")
    
    res = MockReservoir()
    config = HiveConfig()
    hip = Hippocampus(res, None, config)
    
    # Pre-populate _verified_memory_ids_by_task so penalize_memory doesn't skip
    hip._verified_memory_ids_by_task = {tid: set() for tid in range(50)}
    
    threads = []
    print("Spawning 50 concurrent writers...")
    for i in range(50):
        t = threading.Thread(target=worker, args=(hip, i))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    # Verify the file
    import numpy as np
    import json
    
    try:
        vecs = np.load("data/semantic.npy")
        with open("data/semantic_meta.json", "r") as f:
            meta = json.load(f)
            
        print(f"Final vectors shape: {vecs.shape}")
        print(f"Final metadata len: {len(meta)}")
        
        if len(vecs) == len(meta) and len(vecs) == 500:
            print("[SUCCESS] No lost updates! 500/500 memories saved correctly.")
        else:
            print(f"[FAILED] Lost updates detected. Expected 500, got {len(vecs)}")
            
    except Exception as e:
        print(f"[FAILED] File corruption detected: {e}")

if __name__ == "__main__":
    main()
