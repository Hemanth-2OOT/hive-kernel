import time
import urllib.request
import json

def test_unload_time():
    model = "qwen2.5-coder:7b"
    req = urllib.request.Request("http://127.0.0.1:11434/api/generate", method="POST")
    req.add_header('Content-Type', 'application/json')
    
    print(f"Sending keep_alive=0 to {model}...")
    start = time.time()
    try:
        urllib.request.urlopen(req, data=json.dumps({"model": model, "keep_alive": 0}).encode())
        duration = time.time() - start
        print(f"Unloaded {model} in {duration:.2f}s")
    except Exception as e:
        duration = time.time() - start
        print(f"Error unloading {model} in {duration:.2f}s: {e}")

if __name__ == "__main__":
    test_unload_time()
