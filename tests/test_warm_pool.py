import pytest
import time
import json
import threading
from hive.config import HiveConfig
from hive.runtime.reservoir import Reservoir, ReservoirContentionTimeout

@pytest.fixture
def reservoir():
    config = HiveConfig()
    config.idle_ttl_sec = 0.5 # Fast TTL for tests
    return Reservoir(config)

def test_warm_pool_basic_reuse(reservoir):
    # Start cell
    reservoir.start_cell("sentiment")
    assert "sentiment" in reservoir.cells
    
    # Kill cell (simulating eviction)
    reservoir.evict_cell("sentiment")
    
    # Process should be moved to warm pool, not cells
    assert "sentiment" not in reservoir.cells
    assert "sentiment" in reservoir._warm_pool
    
    # Start cell again (should reuse from pool)
    reservoir.start_cell("sentiment")
    assert "sentiment" in reservoir.cells
    assert "sentiment" not in reservoir._warm_pool

def test_warm_pool_eviction_different_model(reservoir):
    reservoir.start_cell("sentiment")
    reservoir.evict_cell("sentiment")
    
    assert "sentiment" in reservoir._warm_pool
    old_proc = reservoir._warm_pool["sentiment"]
    
    # Start a different cell, it shouldn't use the warm pool slot
    reservoir.start_cell("embedding")
    # But wait, start_cell doesn't evict the warm pool. Warm pool eviction happens when KILLING a cell and the slot is full.
    assert "embedding" in reservoir.cells
    
    # Now kill embedding to put it in the pool
    reservoir.evict_cell("embedding")
    
    # The pool only has one slot, so "sentiment" should be evicted and terminated
    assert "embedding" in reservoir._warm_pool
    assert "sentiment" not in reservoir._warm_pool
    
    # Ensure sentiment process is terminated
    old_proc.wait(timeout=2)
    assert old_proc.poll() is not None

def test_warm_pool_stale_state_mid_request(reservoir):
    # Simulate killing a cell while it's actively processing a request.
    # The process should NOT go to the warm pool because it holds the cell lock (dirty).
    reservoir.start_cell("sentiment")
    
    # We lock it artificially to simulate mid-request
    with reservoir.cell_locks["sentiment"]:
        reservoir.evict_cell("sentiment")
        
    assert "sentiment" not in reservoir.cells
    assert "sentiment" not in reservoir._warm_pool # Should not be pooled if dirty!

def test_warm_pool_abandoned_mid_request(reservoir):
    # Simulate an abandoned request (e.g. caller crashed or timed out and released the lock)
    reservoir.start_cell("sentiment")
    proc = reservoir.cells["sentiment"]
    proc.is_dirty = True  # Set by infer() before writing to stdin
    
    # Caller released lock (by crashing), but cell is still dirty
    reservoir.evict_cell("sentiment")
    
    # Even though lock is free, it should NOT be pooled because it's dirty
    assert "sentiment" not in reservoir.cells
    assert "sentiment" not in reservoir._warm_pool

def test_warm_pool_ttl_expiration(reservoir):
    reservoir.start_cell("sentiment")
    reservoir.evict_cell("sentiment")
    
    assert "sentiment" in reservoir._warm_pool
    
    time.sleep(1.0) # Wait for TTL to expire
    reservoir.cleanup_idle()
    
    assert "sentiment" not in reservoir._warm_pool
