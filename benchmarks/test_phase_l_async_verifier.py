import time
import os
import json
import threading
from typing import List, Optional

from hive.memory.verifier import SemanticVerifier, MemoryCandidate, VerifiedMemory
from hive.memory.hippocampus import Hippocampus
from hive.config import HiveConfig

class MockReservoir:
    def __init__(self):
        self.call_count = 0

    def infer(self, cell_type, task_id, payload):
        self.call_count += 1
        time.sleep(1.0) # simulate slow LLM
        return {
            "status": "success",
            "result": {"text": "FINAL_JUDGMENT: YES"}
        }

def test_async_verifier():
    os.makedirs("data", exist_ok=True)
    if os.path.exists("data/verifier_cache.json"):
        os.remove("data/verifier_cache.json")
        
    config = HiveConfig()
    reservoir = MockReservoir()
    verifier = SemanticVerifier(reservoir, config)
    
    hippo = Hippocampus(reservoir, verifier, config)
    
    hippo.embeddings = [[1.0] * 384]
    hippo.metadata = [{
        "_memory_id": "test_mem_1",
        "_content": "Test content",
        "_decay_factor": 1.0
    }]
    
    def mock_query(*args, **kwargs):
        return [MemoryCandidate(
            memory_id=hippo.metadata[0]["_memory_id"],
            content=hippo.metadata[0]["_content"],
            embedding_score=0.99,
            raw_memory=hippo.metadata[0]
        )]
        
    hippo.query = mock_query
    
    print("Testing rapid DAG iterations (should not block)...")
    start_time = time.time()
    
    verified = hippo.query_verified("test query", task_id=1)
    
    iteration_time = time.time() - start_time
    print(f"Iteration 1 time: {iteration_time:.2f}s")
    
    assert iteration_time < 0.5, "Iteration 1 blocked on verifier!"
    assert len(verified) == 0, "Unverified memory was not skipped!"
    assert "test_mem_1" in hippo._in_flight_verifications, "Memory was not added to in-flight set"
    
    start_time2 = time.time()
    verified2 = hippo.query_verified("test query", task_id=2)
    iter2_time = time.time() - start_time2
    print(f"Iteration 2 time: {iter2_time:.2f}s")
    
    assert iter2_time < 0.5, "Iteration 2 blocked!"
    assert len(verified2) == 0, "Unverified memory was not skipped!"
    
    print("Waiting for background worker to finish verification...")
    time.sleep(1.5)
    
    assert "test_mem_1" not in hippo._in_flight_verifications, "Memory was not removed from in-flight set after success"
    
    start_time3 = time.time()
    verified3 = hippo.query_verified("test query", task_id=3)
    iter3_time = time.time() - start_time3
    print(f"Iteration 3 time: {iter3_time:.2f}s")
    
    assert iter3_time < 0.5, "Iteration 3 blocked!"
    assert len(verified3) == 1, "Verified memory was not picked up!"
    assert verified3[0].memory_id == "test_mem_1", "Wrong memory picked up"
    
    print("All assertions passed!")
    
if __name__ == "__main__":
    test_async_verifier()
