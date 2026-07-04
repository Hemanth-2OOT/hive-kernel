import sys
from hive import run, shutdown

def main():
    print("=== Testing Hive API ===")
    
    # 1. First run
    print("\n[Test] Call 1: summarize this: We built a fully isolated OS-process swarm architecture.")
    res1 = run("summarize this: We built a fully isolated OS-process swarm architecture.")
    print("[Test] Call 1 finished executing.")
    
    # Check race condition contract
    print("[Test] Testing strict-access contract on consolidation_error...")
    try:
        err = res1.consolidation_error
        print("[Test] FAILED: Was able to access consolidation_error without waiting!")
        sys.exit(1)
    except RuntimeError as e:
        print(f"[Test] SUCCESS: Caught expected RuntimeError: {e}")
        
    res1.wait_for_consolidation()
    print(f"[Test] Call 1 consolidation finished with error = {res1.consolidation_error}")
    
    # 2. Second run
    print("\n[Test] Call 2: summarize this: testing overlapping calls and state persistence.")
    res2 = run("summarize this: testing overlapping calls and state persistence.")
    print("[Test] Call 2 finished executing.")
    
    # Intentionally not waiting to see if it breaks anything on exit
    # (The atexit handler should clean up correctly)
    print("\n[Test] Smoke test complete. Exiting process. atexit should fire.")
    
if __name__ == "__main__":
    main()
