import time
import sys
from hive import run, shutdown
import hive.api

def main():
    print("=== Testing Shutdown Race Condition ===")
    
    # 1. Warm up the engine
    print("\n[Test] Warming up engine...")
    res = run("summarize this: warm up run.")
    res.wait_for_consolidation()
    
    # 2. Inject a simulated slow consolidation (3 seconds)
    engine = hive.api._default_engine
    original_consolidate = engine.nucleus.consolidator.consolidate
    
    def slow_consolidate(trace):
        print("\n[Test-Hook] Consolidator started... simulating slow 3s network call...")
        time.sleep(3)
        print("[Test-Hook] Consolidator finished slow network call.")
        return original_consolidate(trace)
        
    engine.nucleus.consolidator.consolidate = slow_consolidate
    
    # 3. Fire a run and instantly exit
    print("\n[Test] Call 2 (Slow Consolidation): summarize this: testing shutdown race.")
    run("summarize this: testing shutdown race.")
    
    print("\n[Test] Main thread is done. Process is exiting NOW. atexit should block and wait!")

if __name__ == "__main__":
    main()
