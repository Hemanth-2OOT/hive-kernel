import time
import urllib.request
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hive.config import HiveConfig
from hive.runtime.reservoir import Reservoir

def get_vram_mb():
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/ps") as r:
            ps = json.loads(r.read().decode())
        return sum(m.get("size_vram", 0) for m in ps.get("models", [])) // (1024 * 1024)
    except Exception:
        return -1

from datetime import datetime

def current_time():
    return datetime.now().strftime('%H:%M:%S.%f')[:-3]

def main():
    model = "qwen2.5-coder:7b"
    config = HiveConfig()
    res = Reservoir(config)

    print("\n--- Manual clock trace ---")
    print(f"{current_time()} | Step 1: Evicting model")
    with res.topology_lock:
        if model in res.cells:
            res._kill_cell_unsafe(model)
    
    print(f"{current_time()} | VRAM before sleep: {get_vram_mb()}MB")
    
    print(f"{current_time()} | Step 2: Sleep starts")
    time.sleep(5)
    print(f"{current_time()} | Step 2: Sleep ends")
    
    print(f"{current_time()} | VRAM after sleep, before infer: {get_vram_mb()}MB")

    print(f"{current_time()} | Step 3: infer() starts")
    t0 = time.perf_counter()
    result = res.infer(model, task_id=999, payload="Say hello")
    t1 = time.perf_counter()
    print(f"{current_time()} | Step 3: infer() returns")
    
    wall_ms = (t1 - t0) * 1000
    print(f"\nTotal infer() wall_ms = {wall_ms:.1f}ms")
    print(f"VRAM after infer: {get_vram_mb()}MB")

    # cleanup
    with res.topology_lock:
        if model in res.cells:
            res._kill_cell_unsafe(model)

if __name__ == "__main__":
    main()
