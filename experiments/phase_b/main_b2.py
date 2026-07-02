import time
from reservoir import Reservoir

def main():
    print("=== Reservoir v0.2: RAM Budget & Eviction Test ===")
    
    # Setting max_ram_mb to 2000 limits the pool tightly.
    # LLM(1500) + Sent(550) + Emb(400) = 2450 MB (Will force an eviction!)
    res = Reservoir(max_ram_mb=2000, idle_ttl_sec=300)
    
    print("\n--- Spawning LLM (Cost: 1500) ---")
    res.start_cell("llm")
    res.infer("llm", 0, "cold start") # Force full memory load
    time.sleep(2.5) # Give it artificial idle time so its eviction score climbs
    
    print("\n--- Spawning Embedding (Cost: 400) ---")
    res.start_cell("embedding")
    res.infer("embedding", 0, "cold start") # Force full memory load
    time.sleep(1) 
    
    print("\n--- Current RAM before Sentiment ---")
    print(f"Total Active RSS: {res.get_total_rss():.1f} MB")
    
    print("\n--- Spawning Sentiment (Cost: 550) ---")
    print("Expecting LLM to be evicted due to high RSS, long idle, and low priority...")
    res.start_cell("sentiment")
    res.infer("sentiment", 0, "cold start") # Force full memory load
    
    print("\n--- Current RAM after Eviction ---")
    print(f"Total Active RSS: {res.get_total_rss():.1f} MB")
    print(f"Active Cells: {list(res.cells.keys())}")
    
    print("\n--- Inferencing on Evicted LLM ---")
    print("This should seamlessly trigger a cold start and evict Sentiment.")
    # Wait to make Sentiment older than Embedding, adjusted for Priority
    time.sleep(3) 
    res.infer("llm", 1, "Hello from the respawned LLM!")
    
    print("\n--- Current RAM after LLM Respawn ---")
    print(f"Total Active RSS: {res.get_total_rss():.1f} MB")
    print(f"Active Cells: {list(res.cells.keys())}")
    
    print("\n--- Testing TTL Eviction ---")
    print("Setting TTL to 2 seconds and waiting 3 seconds...")
    res.idle_ttl_sec = 2
    time.sleep(3)
    res.ensure_capacity(0) # Force a cleanup pass
    
    print("\n--- Final RAM ---")
    print(f"Total Active RSS: {res.get_total_rss():.1f} MB")
    print(f"Active Cells: {list(res.cells.keys())}")
    
    res.shutdown()
    print("\nDone.")

if __name__ == "__main__":
    main()
