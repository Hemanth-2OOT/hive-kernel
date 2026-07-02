import time
import psutil
from reservoir import Reservoir

def get_rss(pid):
    try:
        return psutil.Process(pid).memory_info().rss / 1e6
    except psutil.NoSuchProcess:
        return -1.0

def main():
    print("=== Reservoir v0.1: Multi-Cell Routing Test ===")
    res = Reservoir()
    
    print("Starting Sentiment Cell...")
    res.start_cell("sentiment")
    
    print("Starting Embedding Cell...")
    res.start_cell("embedding")
    
    pid_sent = res.get_child_pid("sentiment")
    pid_emb = res.get_child_pid("embedding")
    
    print(f"Sentiment PID: {pid_sent}")
    print(f"Embedding PID: {pid_emb}")
    
    print("\nExecuting alternating inferences...")
    
    # 1 cold start for each to prep the model weights in RAM
    print("Cold start Sentiment...")
    res.infer("sentiment", 0, "cold start")
    print("Cold start Embedding...")
    res.infer("embedding", 0, "cold start")
    
    sent_rss_track = []
    emb_rss_track = []
    
    for i in range(1, 16):
        print(f"\n--- Round {i} ---")
        
        # 1. Route to Sentiment
        req_sent = f"Sentiment test payload {i}"
        resp_sent = res.infer("sentiment", i*10, req_sent)
        rss_s = get_rss(pid_sent)
        sent_rss_track.append(rss_s)
        
        # Verify routing (Sentiment MUST return 'label' and 'confidence')
        if "label" not in resp_sent.get("result", {}):
            print(f"ROUTING ERROR! Sentiment cell returned: {resp_sent}")
        else:
            print(f"Sentiment OK -> {resp_sent['result']['label']} (RSS: {rss_s:.1f} MB)")
            
        # 2. Route to Embedding
        req_emb = f"Embedding test payload {i}"
        resp_emb = res.infer("embedding", i*10 + 1, req_emb)
        rss_e = get_rss(pid_emb)
        emb_rss_track.append(rss_e)
        
        # Verify routing (Embedding MUST return 'vector' array)
        if "vector" not in resp_emb.get("result", {}):
            print(f"ROUTING ERROR! Embedding cell returned: {resp_emb}")
        else:
            print(f"Embedding OK -> Vector length {len(resp_emb['result']['vector'])} (RSS: {rss_e:.1f} MB)")
            
    res.shutdown()
    
    print("\n=== FINAL MEMORY REPORT ===")
    print(f"Sentiment RSS (Round 1 -> 15): {sent_rss_track[0]:.1f} MB -> {sent_rss_track[-1]:.1f} MB")
    print(f"Embedding RSS (Round 1 -> 15): {emb_rss_track[0]:.1f} MB -> {emb_rss_track[-1]:.1f} MB")
    print("Done.")

if __name__ == "__main__":
    main()
