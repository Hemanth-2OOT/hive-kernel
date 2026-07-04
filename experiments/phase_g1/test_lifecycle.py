import subprocess
import json
import urllib.request
import time
import os
import sys
import signal
from hive.runtime.reservoir import Reservoir

def get_ollama_models():
    try:
        req = urllib.request.Request("http://localhost:11434/api/ps")
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            return [m["name"] for m in data.get("models", [])]
    except Exception as e:
        print(f"Error querying Ollama: {e}")
        return []

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "crash_child":
        res = Reservoir(max_vram_mb=6000, idle_ttl_sec=300)
        res.start_cell("hermes3:8b")
        print(f"[Orchestrator] Models loaded: {get_ollama_models()}")
        print("[Orchestrator] Simulating catastrophic crash (os._exit)...")
        sys.stdout.flush()
        os._exit(1)
        
    if len(sys.argv) > 1 and sys.argv[1] == "sigint_child":
        res = Reservoir(max_vram_mb=6000, idle_ttl_sec=300)
        res.start_cell("hermes3:8b")
        print(f"[Orchestrator] Models loaded: {get_ollama_models()}")
        print("[Orchestrator] Entering infinite loop to wait for SIGINT...")
        sys.stdout.flush()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("[Orchestrator] Caught KeyboardInterrupt! Let's see if we exit cleanly or swallow it.")
            # If we were swallowing it, we'd loop again. But standard behavior is to let it crash the process.
            # We just raise it to simulate normal python behavior.
            raise

    print("=== Testing Unhandled Crash (os._exit) ===")
    try:
        urllib.request.urlopen(urllib.request.Request("http://localhost:11434/api/generate", method="POST", data=json.dumps({"model": "hermes3:8b", "keep_alive": 0}).encode(), headers={'Content-Type': 'application/json'}))
    except: pass

    print("[Main] Booting dummy Orchestrator process to start hermes3:8b...")
    proc = subprocess.Popen([sys.executable, __file__, "crash_child"])
    proc.wait()
    time.sleep(3.0)
    models = get_ollama_models()
    print(f"[Main] After os._exit(1), Current Ollama VRAM: {models}")
    
    print("\n=== Testing SIGINT (CTRL+C) ===")
    try:
        urllib.request.urlopen(urllib.request.Request("http://localhost:11434/api/generate", method="POST", data=json.dumps({"model": "hermes3:8b", "keep_alive": 0}).encode(), headers={'Content-Type': 'application/json'}))
    except: pass
    
    print("[Main] Booting dummy Orchestrator process for SIGINT...")
    # CREATE_NEW_PROCESS_GROUP is needed on Windows to send CTRL_C_EVENT safely to the child without killing the parent test script
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    proc2 = subprocess.Popen([sys.executable, __file__, "sigint_child"], creationflags=creationflags)
    
    time.sleep(4.0) # wait for model to load
    print("[Main] Sending SIGINT to Orchestrator...")
    if sys.platform == "win32":
        os.kill(proc2.pid, signal.CTRL_C_EVENT)
    else:
        os.kill(proc2.pid, signal.SIGINT)
        
    proc2.wait(timeout=5.0)
    time.sleep(3.0)
    models2 = get_ollama_models()
    print(f"[Main] After SIGINT, Current Ollama VRAM: {models2}")
    
    if any(m.startswith("hermes") for m in models) or any(m.startswith("hermes") for m in models2):
        print("VRAM LEAK DETECTED!")
    else:
        print("LIFECYCLE IMMUNITY PROVEN for both Crash and SIGINT!")

if __name__ == "__main__":
    main()
