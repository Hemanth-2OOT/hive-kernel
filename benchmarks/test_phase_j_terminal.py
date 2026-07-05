import time
import concurrent.futures
from hive.config import HiveConfig
from hive.runtime.reservoir import Reservoir

def test_phase_j_terminal():
    print("--- Testing Phase J Terminal Error Bound ---")
    config = HiveConfig(max_vram_mb=6144)
    res = Reservoir(config)
    
    def lock_holder():
        print("Lock Holder acquiring qwen2.5-coder:7b lock...")
        with res.cell_locks["qwen2.5-coder:7b"]:
            # Boot it so it takes up VRAM
            with res.topology_lock:
                res._start_cell_unsafe("qwen2.5-coder:7b")
            print("Lock Holder successfully holding qwen2.5-coder:7b for 200s to simulate unresolvable contention.")
            time.sleep(200.0)
            print("Lock Holder releasing qwen2.5-coder:7b.")
        return "SUCCESS"
            
    def requester():
        # Wait a moment for Lock Holder to grab the lock and boot the cell
        time.sleep(10.0)
        try:
            print("Requester asking for hermes3:8b (which requires evicting qwen2.5-coder:7b)...")
            res.infer("hermes3:8b", 0, "ping")
            print("Requester miraculously finished? (This shouldn't happen!)")
            return "SUCCESS"
        except Exception as e:
            print(f"Requester FAILED loudly as expected: {e}")
            return "TERMINAL_ERROR"

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(lock_holder)
        f2 = executor.submit(requester)
        
        # We only care about f2's result
        r2 = f2.result()
        
    if r2 == "TERMINAL_ERROR":
        print("TEST PASSED: The unresolvable contention hit the terminal bound and threw loudly.")
    else:
        print("TEST FAILED: Requester did not throw a terminal error!")
        
    res.shutdown()

if __name__ == "__main__":
    main()
