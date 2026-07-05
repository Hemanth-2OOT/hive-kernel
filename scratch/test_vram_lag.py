import urllib.request
import json
import time

def get_ps():
    req = urllib.request.Request("http://127.0.0.1:11434/api/ps", method="GET")
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read().decode())

def load_model(model="qwen2.5-coder:7b"):
    print(f"Loading {model}...")
    req = urllib.request.Request("http://127.0.0.1:11434/api/generate", method="POST")
    req.add_header('Content-Type', 'application/json')
    urllib.request.urlopen(req, data=json.dumps({"model": model, "keep_alive": "5m"}).encode())
    print("Loaded.")

def unload_model(model="qwen2.5-coder:7b"):
    print(f"Unloading {model}...")
    req = urllib.request.Request("http://127.0.0.1:11434/api/generate", method="POST")
    req.add_header('Content-Type', 'application/json')
    urllib.request.urlopen(req, data=json.dumps({"model": model, "keep_alive": 0}).encode())
    print("Unload requested.")

if __name__ == "__main__":
    model = "qwen2.5-coder:7b"
    load_model(model)
    time.sleep(1)
    
    ps = get_ps()
    found = False
    for m in ps.get("models", []):
        if m["name"].startswith("qwen2.5-coder"):
            found = True
            print(f"Before unload: {m['name']} size_vram={m.get('size_vram')}")
            
    if not found:
        print("Model not loaded?")
        
    unload_model(model)
    
    start = time.time()
    while True:
        ps = get_ps()
        models = ps.get("models", [])
        found = False
        for m in models:
            if m["name"].startswith("qwen2.5-coder"):
                found = True
                print(f"[{time.time()-start:.2f}s] {m['name']} size_vram={m.get('size_vram')}")
        if not found:
            print(f"[{time.time()-start:.2f}s] Model removed from /api/ps completely!")
            break
        time.sleep(0.1)
        if time.time() - start > 10:
            print("Timeout!")
            break
