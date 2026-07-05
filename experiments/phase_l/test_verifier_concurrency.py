import os
import time
import concurrent.futures
from typing import List

from hive.runtime.reservoir import Reservoir
from hive.config import HiveConfig
from hive.memory.verifier import SemanticVerifier, MemoryCandidate

def run_concurrent_test():
    # Setup
    config = HiveConfig(max_vram_mb=6000)
    res = Reservoir(config)
    verifier = SemanticVerifier(res, cell_name="hermes3:8b", config=config)

    # Clear cache before test
    cache_path = verifier._cache_file
    if os.path.exists(cache_path):
        os.remove(cache_path)
    verifier._judgment_cache.clear()

    # Create dummy candidates
    queries = [
        "How do I sort a list in Python?",
        "What is the capital of France?",
        "How do I fix a NullPointerException?",
        "Explain the theory of relativity."
    ]
    
    candidates = [
        [MemoryCandidate(memory_id=f"m{i}", content=f"Candidate for {i}", embedding_score=0.9, raw_memory={})]
        for i in range(len(queries))
    ]

    print("Running 4 concurrent cache misses...")
    start_time = time.time()

    def verify_query(i):
        # We pass task_id=i to differentiate tasks if necessary
        return verifier.verify(queries[i], candidates[i], task_id=i)

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(verify_query, i) for i in range(4)]
        for future in concurrent.futures.as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                print(f"Task failed: {e}")

    duration = time.time() - start_time
    print(f"Concurrent execution took: {duration:.2f} seconds")
    
    # Validation
    # If they ran sequentially, 4 queries taking ~4-5s each would be 16-20 seconds.
    # If concurrent, it should take ~5-10 seconds total depending on the system's ability to run parallel infer().
    print(f"Cache size: {len(verifier._judgment_cache)}")
    
    res.shutdown()

if __name__ == "__main__":
    run_concurrent_test()
