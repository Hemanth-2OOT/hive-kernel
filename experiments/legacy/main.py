import time
import psutil
import os
from reservoir import Reservoir
import statistics

def main():
    print("=== Reservoir v0: 50-Call Measurement Harness (Child RSS) ===")
    
    res = Reservoir()
    
    t0 = time.perf_counter()
    res.start_embedding_cell()
    t1 = time.perf_counter()
    print(f"Cell Popen (Process Spawn) Time: {t1 - t0:.3f}s")
    
    child_proc = psutil.Process(res.child_pid)
    print(f"Tracking Child Process PID: {res.child_pid}")
    
    # First request (Cold Start)
    t2 = time.perf_counter()
    resp1 = res.infer_sentiment(0, "Initialize model.")
    t3 = time.perf_counter()
    cold_start_time = t3 - t2
    print(f"Cold Start Request Latency: {cold_start_time:.3f}s")
    
    warm_latencies = []
    child_rss_checkpoints = {}
    
    print("Starting 50 Warm Requests...")
    
    for i in range(1, 51):
        t_start = time.perf_counter()
        
        if i == 25:
            resp = res.infer_raw("{MALFORMED JSON: I AM BREAKING THE PROTOCOL!!!]")
        else:
            # Vary input length to stress the PyTorch tensor cache allocator
            varied_payload = "This is a request. " * (i % 5 + 1)
            resp = res.infer_sentiment(i, varied_payload)
            
        t_end = time.perf_counter()
        warm_latencies.append(t_end - t_start)
        
        if i in [1, 10, 25, 26, 50]:
            try:
                current_rss = child_proc.memory_info().rss / 1e6
                child_rss_checkpoints[i] = current_rss
            except psutil.NoSuchProcess:
                child_rss_checkpoints[i] = -1.0
                
    res.shutdown()
    
    print("\n=== FINAL SUMMARY TABLE ===")
    print(f"Cold Start Latency: {cold_start_time:.3f}s")
    
    print("\nWarm Inference Latency (50 calls):")
    print(f"  Min:    {min(warm_latencies):.4f}s")
    print(f"  Max:    {max(warm_latencies):.4f}s")
    print(f"  Mean:   {statistics.mean(warm_latencies):.4f}s")
    print(f"  Median: {statistics.median(warm_latencies):.4f}s")
    
    print("\nCHILD RSS Tracking (PyTorch Allocator Drift Check):")
    for cp, mem in child_rss_checkpoints.items():
        print(f"  After Call {cp:<2}: {mem:.1f} MB")
    print("===========================================")

if __name__ == "__main__":
    main()
