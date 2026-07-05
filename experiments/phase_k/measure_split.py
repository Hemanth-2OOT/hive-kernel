import time
import subprocess
import json
import urllib.request
import os
import sys

def main():
    model = "qwen2.5-coder:7b"
    script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hive", "cells", "llm_server.py")
    if not os.path.exists(script_path):
        # try swarm_ai path
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cells", "llm_server.py")

    # Step 1: Force LOAD into Ollama to ensure a WARM VRAM state
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/generate", method="POST")
        req.add_header('Content-Type', 'application/json')
        urllib.request.urlopen(req, data=json.dumps({"model": model, "keep_alive": 360}).encode())
    except:
        pass

    # No sleep needed, it's warm
    
    print("--- Split overhead measurement (WARM VRAM) ---")
    
    t0 = time.perf_counter()
    
    # Spawn process
    proc = subprocess.Popen(
        [sys.executable, script_path, model, "360"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    t_spawn = time.perf_counter()
    
    # Read booting
    line1 = proc.stdout.readline()
    t_booting = time.perf_counter()

    # Read ready
    line2 = proc.stdout.readline()
    t_ready = time.perf_counter()

    # Kill process
    proc.terminate()

    print(f"Subprocess spawn (Popen block): {(t_spawn - t0)*1000:.1f} ms")
    print(f"Python interpreter + import overhead (until 'booting'): {(t_booting - t_spawn)*1000:.1f} ms")
    print(f"Ollama VRAM load + ping (until 'ready'): {(t_ready - t_booting)*1000:.1f} ms")
    print(f"Total time: {(t_ready - t0)*1000:.1f} ms")

if __name__ == "__main__":
    main()
