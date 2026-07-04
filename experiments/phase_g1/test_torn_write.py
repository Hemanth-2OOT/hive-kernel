import sys
import time
import threading
import os
from hive.runtime.reservoir import Reservoir

def test_torn_write():
    res = Reservoir(max_vram_mb=6000, idle_ttl_sec=300)
    
    print("=== Testing Torn-Write IPC Edge Case ===")
    
    # Pre-start the cell
    try:
        res.infer("embedding", 0, "ping")
    except Exception:
        pass

    def crash_thread():
        try:
            print("[Thread 1] Sending torn write...")
            res.infer("embedding", 1, "CRASH_CLIENT_TORN_WRITE")
        except Exception as e:
            print(f"[Thread 1] Crashed as expected: {e}")

    t1 = threading.Thread(target=crash_thread)
    t1.start()
    t1.join()

    print("[Main] Thread 1 finished. Cell lock should be released.")
    print("[Main] Thread 2 attempting normal request...")
    
    result = {"status": "pending"}
    def normal_request():
        try:
            resp = res.infer("embedding", 2, "Normal request")
            result["status"] = "success"
            result["resp"] = resp
            print("[Thread 2] Received response successfully!")
        except Exception as e:
            result["status"] = "error"
            result["error"] = e
            print(f"[Thread 2] Error: {e}")

    t2 = threading.Thread(target=normal_request)
    t2.start()
    t2.join(timeout=5.0)
    
    if t2.is_alive():
        print("DEADLOCK CONFIRMED: Thread 2 is hung waiting for response from cell.")
        # Force exit so the test doesn't hang forever
        os._exit(0)
    else:
        print(f"[Main] Thread 2 finished with result: {result['status']}")
        
        # Now prove Thread 3 succeeds!
        print("[Main] Thread 3 attempting request to prove cell recovered...")
        t3_result = {"status": "pending"}
        def recovery_request():
            try:
                resp = res.infer("embedding", 3, "Recovery request")
                t3_result["status"] = "success"
                print("[Thread 3] Received response successfully!")
            except Exception as e:
                t3_result["status"] = "error"
                print(f"[Thread 3] Error: {e}")

        t3 = threading.Thread(target=recovery_request)
        t3.start()
        t3.join(timeout=5.0)
        
        print(f"Final Result: Thread 2={result['status']}, Thread 3={t3_result['status']}")
        res.shutdown()

if __name__ == "__main__":
    test_torn_write()
