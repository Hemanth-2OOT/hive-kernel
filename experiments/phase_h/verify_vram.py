import urllib.request
import json
import time

print("Waiting 3s for cleanup to finish...")
time.sleep(3)

req = urllib.request.Request("http://localhost:11434/api/ps")
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())
    models = [m["name"] for m in data.get("models", [])]
    print(f"Current VRAM models: {models}")
    
    if models:
        print("VRAM LEAK DETECTED!")
    else:
        print("VRAM CLEANUP VERIFIED!")
