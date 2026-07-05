import pytest
import os
import time
import json
from hive.memory.verifier import SemanticVerifier, MemoryCandidate
from hive.config import HiveConfig

class MockReservoir:
    def infer(self, cell_type, task_id, payload):
        return {
            "status": "success",
            "result": {"text": "FINAL_JUDGMENT: YES\nReason: Dummy mock response"}
        }

def test_cache_eviction():
    config = HiveConfig()
    config.data_dir = "data"
    
    # Ensure clean slate
    cache_path = os.path.join(config.data_dir, "verifier_cache.json")
    if os.path.exists(cache_path):
        os.remove(cache_path)
        
    verifier = SemanticVerifier(reservoir=MockReservoir(), config=config)
    
    # Insert 1200 unique queries
    print("Inserting 1200 items into cache...")
    for i in range(1200):
        c = MemoryCandidate(
            memory_id=f"mem_{i}",
            content=f"content_{i}",
            embedding_score=0.99,
            raw_memory={"_task_id": 0}
        )
        # Background worker method
        verifier.verify_single(f"query {i}", c)
        
    # After 1200 inserts, it should have triggered eviction at 1001
    # 1001 -> drops 200 -> 801
    # Then inserts up to 1200 -> reaches 1000
    # Wait, exactly at 1001 it dropped 200, so it became 801. 
    # It adds 199 more items -> 1000. So size should be exactly 1000.
    
    with verifier._io_lock:
        cache_size = len(verifier._judgment_cache)
        
    print(f"Final cache size: {cache_size}")
    assert cache_size == 1000, f"Expected 1000 entries, got {cache_size}"
    
    # Let's verify WHICH keys were dropped. 
    # Because we insert i=0 to 1199, when it hits 1001 (which is i=1000), 
    # the first 200 items (i=0 to 199) are dropped.
    # So the oldest surviving item should be i=200!
    # And the newest should be i=1199.
    
    # We need to construct the cache keys to test this.
    import hashlib
    # query 0 should be missing
    query_0 = "query 0"
    query_hash_0 = hashlib.md5(query_0.encode()).hexdigest()
    key_0 = f"{verifier._cell_name}_{verifier._prompt_hash}_{query_hash_0}_mem_0"
    
    # query 199 should be missing
    query_199 = "query 199"
    query_hash_199 = hashlib.md5(query_199.encode()).hexdigest()
    key_199 = f"{verifier._cell_name}_{verifier._prompt_hash}_{query_hash_199}_mem_199"
    
    # query 200 should exist
    query_200 = "query 200"
    query_hash_200 = hashlib.md5(query_200.encode()).hexdigest()
    key_200 = f"{verifier._cell_name}_{verifier._prompt_hash}_{query_hash_200}_mem_200"
    
    # query 1199 should exist
    query_1199 = "query 1199"
    query_hash_1199 = hashlib.md5(query_1199.encode()).hexdigest()
    key_1199 = f"{verifier._cell_name}_{verifier._prompt_hash}_{query_hash_1199}_mem_1199"
    
    with verifier._io_lock:
        assert key_0 not in verifier._judgment_cache, "Oldest key 0 should have been evicted!"
        assert key_199 not in verifier._judgment_cache, "Oldest key 199 should have been evicted!"
        assert key_200 in verifier._judgment_cache, "Key 200 should have survived eviction!"
        assert key_1199 in verifier._judgment_cache, "Newest key 1199 should exist!"
        
        # Ensure all 1000 keys are precisely from i=200 to i=1199
        expected_indices = set(range(200, 1200))
        actual_indices = set()
        
        for k in verifier._judgment_cache.keys():
            # Extract the mem index from the key: ..._mem_X
            idx_str = k.split("_mem_")[1]
            actual_indices.add(int(idx_str))
            
        assert actual_indices == expected_indices, "The remaining keys do not perfectly match the 800 newest entries!"
        
    print("Test passed! Cache correctly evicted oldest 20% while retaining newest items.")

if __name__ == "__main__":
    test_cache_eviction()
