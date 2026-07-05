import time
import json
import urllib.request

def run_experiment():
    print("Testing sequential load/unload to simulate Workload A thrashing...")
    models = ["qwen2.5-coder:7b", "hermes3:8b"]
    
    for i in range(5):
        print(f"\n--- Iteration {i} ---")
        for m in models:
            # 1. Boot
            start = time.time()
            try:
                req = urllib.request.Request("http://127.0.0.1:11434/api/generate", method="POST")
                req.add_header('Content-Type', 'application/json')
                urllib.request.urlopen(req, data=json.dumps({"model": m, "keep_alive": 360}).encode())
                boot_time = time.time() - start
                print(f"Boot {m}: {boot_time:.2f}s")
            except Exception as e:
                print(f"Failed to boot {m}: {e}")
                
            # 2. Unload the OTHER model (simulate eviction)
            other = "hermes3:8b" if m == "qwen2.5-coder:7b" else "qwen2.5-coder:7b"
            start = time.time()
            try:
                req = urllib.request.Request("http://127.0.0.1:11434/api/generate", method="POST")
                req.add_header('Content-Type', 'application/json')
                urllib.request.urlopen(req, data=json.dumps({"model": other, "keep_alive": 0}).encode())
                unload_time = time.time() - start
                print(f"Unload {other}: {unload_time:.2f}s")
            except Exception as e:
                print(f"Failed to unload {other}: {e}")

if __name__ == "__main__":
    run_experiment()
