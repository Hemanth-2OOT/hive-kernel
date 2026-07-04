import threading
import time
from hive import run, shutdown
import hive.api

def main():
    print("=== Testing API Concurrency Race Conditions ===")
    
    # Initialize engine
    run("summarize this: warm up")
    engine = hive.api._default_engine
    
    # We will spawn multiple threads calling run() simultaneously.
    # We will also mock the consolidator to ensure it takes a bit of time.
    original_consolidate = engine.nucleus.consolidator.consolidate
    def slow_consolidate(trace):
        time.sleep(1)
        return original_consolidate(trace)
    engine.nucleus.consolidator.consolidate = slow_consolidate

    errors = []
    
    def worker(i):
        try:
            print(f"[Worker {i}] Calling run()...")
            run(f"summarize this: test concurrency payload {i}")
            print(f"[Worker {i}] Returned from run().")
        except Exception as e:
            import traceback
            errors.append(f"Worker {i} error: {e}\n{traceback.format_exc()}")

    threads = []
    for i in range(5):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        
    for t in threads:
        t.start()
        
    for t in threads:
        t.join()
        
    if errors:
        print("[FAIL] Errors during concurrent run:")
        for e in errors:
            print(e)
            
    # At this point, 5 contexts were added. Some might have been pruned.
    # The active_contexts list should correctly hold any still-alive threads.
    print(f"[MAIN] active_contexts count before shutdown: {len(engine.active_contexts)}")
    
    # We will let atexit naturally shutdown. It should wait for all 5 background threads
    print("[MAIN] Process exiting. Shutdown hook should join remaining threads.")

if __name__ == "__main__":
    main()
