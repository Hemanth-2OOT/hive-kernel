import time
from hive.runtime.reservoir import Reservoir

def main():
    print("=== Reservoir v0: Manual IPC Testing ===")
    res = Reservoir()
    
    print("\nSending Request 1 (Cold Start: Includes PyTorch Import + Model Load)...")
    t2 = time.time()
    resp1 = res.infer("sentiment", 1, "I love this architecture!")
    t3 = time.time()
    print(f"Resp 1: {resp1}")
    print(f"Latency 1: {t3-t2:.2f}s")
    
    print("\nSending Request 2 (Warm Inference)...")
    t4 = time.time()
    resp2 = res.infer("sentiment", 2, "This is garbage.")
    t5 = time.time()
    print(f"Resp 2: {resp2}")
    print(f"Latency 2: {t5-t4:.2f}s")

    print("\nSending Request 3 (Warm Inference)...")
    t6 = time.time()
    resp3 = res.infer("sentiment", 3, "Whatever.")
    t7 = time.time()
    print(f"Resp 3: {resp3}")
    print(f"Latency 3: {t7-t6:.2f}s")

    print("\nShutting down Reservoir...")
    res.shutdown()
    print("Done.")

if __name__ == "__main__":
    main()
