import time
import psutil
import statistics
import random
from reservoir import Reservoir

def get_child_rss(pid):
    try:
        return psutil.Process(pid).memory_info().rss / 1e6
    except psutil.NoSuchProcess:
        return -1.0

def run_phase(res, cell_pid, phase_name, requests):
    print(f"\n=== {phase_name} ===")
    latencies = []
    rss_track = []
    
    prev_rss = get_child_rss(cell_pid)
    print(f"Starting RSS: {prev_rss:.2f} MB\n")
    
    for i, req in enumerate(requests, 1):
        t0 = time.perf_counter()
        resp = res.infer("llm", i, req)
        t1 = time.perf_counter()
        
        latency = t1 - t0
        current_rss = get_child_rss(cell_pid)
        delta_rss = current_rss - prev_rss
        
        text_out = resp.get("result", {}).get("text", "")
        # Very rough output length approximation (chars)
        out_len = len(text_out)
        
        print(f"Call {i:2d} | OutLen: {out_len:4d} chars | Latency: {latency:6.3f}s | RSS: {current_rss:7.2f} MB | Delta: {delta_rss:+6.2f} MB", flush=True)
        
        latencies.append(latency)
        rss_track.append(current_rss)
        prev_rss = current_rss
        
    return latencies, rss_track

def main():
    print("=== Generative LLM KV Cache Stress Test ===")
    res = Reservoir()
    
    print("Starting LLM Cell...")
    t0 = time.perf_counter()
    res.start_cell("llm")
    t1 = time.perf_counter()
    print(f"Process spawned in {t1-t0:.3f}s")
    
    pid = res.get_child_pid("llm")
    
    # Cold Start
    print("Sending cold start request (Loads model + creates initial KV cache)...")
    t2 = time.perf_counter()
    res.infer("llm", 0, "Hello!")
    t3 = time.perf_counter()
    print(f"Cold Start Latency: {t3-t2:.3f}s")
    
    baseline_rss = get_child_rss(pid)
    
    # Phase A: 30 Identical Requests
    # Constant input length -> Tests if fixed generation causes unbounded drift
    phase_a_prompts = ["Tell me a 1-sentence story about a space traveler."] * 30
    lat_a, rss_a = run_phase(res, pid, "PHASE A (30 Identical Prompts)", phase_a_prompts)
    
    # Phase B: 20 Variable Prompts
    # Wildly varying input lengths + variable output lengths (model hits EOS at different times)
    base_text = "Here is a fact: Water boils at 100 degrees Celsius. "
    phase_b_prompts = []
    for i in range(20):
        length_multiplier = random.randint(1, 20)
        phase_b_prompts.append(base_text * length_multiplier + f" Elaborate on point {i} in great detail.")
        
    lat_b, rss_b = run_phase(res, pid, "PHASE B (20 Variable Prompts)", phase_b_prompts)
    
    final_rss = get_child_rss(pid)
    all_latencies = lat_a + lat_b
    all_rss = rss_a + rss_b
    peak_rss = max(all_rss)
    
    res.shutdown()
    
    print("\n=== FINAL SUMMARY ===")
    print(f"Baseline RSS (Post Cold Start): {baseline_rss:.2f} MB")
    print(f"Peak RSS during run:            {peak_rss:.2f} MB")
    print(f"Final RSS before shutdown:      {final_rss:.2f} MB")
    print(f"Cumulative RSS Drift:           {(final_rss - baseline_rss):+.2f} MB")
    print(f"Average Latency (50 calls):     {statistics.mean(all_latencies):.3f}s")
    print("=======================")

if __name__ == "__main__":
    main()
