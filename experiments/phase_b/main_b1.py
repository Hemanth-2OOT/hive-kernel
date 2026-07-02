import time
import psutil
from reservoir import Reservoir

def get_child_rss(pid):
    try:
        return psutil.Process(pid).memory_info().rss / 1e6
    except psutil.NoSuchProcess:
        return -1.0

def main():
    print("=== Phase B1: Multi-Cell Coexistence Benchmark ===")
    res = Reservoir()
    
    print("Spawning Sentiment (Type S)...")
    res.start_cell("sentiment")
    
    print("Spawning Embedding (Type S)...")
    res.start_cell("embedding")
    
    print("Spawning LLM (Type D)...")
    res.start_cell("llm")
    
    pids = {
        "sentiment": res.get_child_pid("sentiment"),
        "embedding": res.get_child_pid("embedding"),
        "llm": res.get_child_pid("llm")
    }
    
    print("\nWarm up (Cold Starts for all 3)...")
    res.infer("sentiment", 0, "cold start")
    res.infer("embedding", 0, "cold start")
    res.infer("llm", 0, "cold start")
    
    print("\nExecuting 10 rounds of alternating inferences...")
    
    for i in range(1, 11):
        print(f"\n--- Round {i} ---")
        
        # 1. Sentiment
        resp_s = res.infer("sentiment", i*10, f"I love round {i}")
        rss_s = get_child_rss(pids["sentiment"])
        print(f"Sentiment | Label: {resp_s.get('result', {}).get('label')} | RSS: {rss_s:.1f} MB")
        
        # 2. Embedding
        resp_e = res.infer("embedding", i*10+1, f"Context for round {i}")
        rss_e = get_child_rss(pids["embedding"])
        v_len = len(resp_e.get('result', {}).get('vector', []))
        print(f"Embedding | VecLen: {v_len} | RSS: {rss_e:.1f} MB")
        
        # 3. LLM
        resp_l = res.infer("llm", i*10+2, f"Briefly explain number {i}:")
        rss_l = get_child_rss(pids["llm"])
        t_len = len(resp_l.get('result', {}).get('text', ''))
        print(f"LLM       | OutLen: {t_len:3d} chars | RSS: {rss_l:.1f} MB")
        
        # Total Coexistence RAM
        total_rss = rss_s + rss_e + rss_l
        print(f"-> TOTAL CHILD RAM: {total_rss:.1f} MB")
        
    res.shutdown()
    print("Done.")

if __name__ == "__main__":
    main()
