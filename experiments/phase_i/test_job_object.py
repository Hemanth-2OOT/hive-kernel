import subprocess
import time
import sys
import psutil

def get_vram_usage():
    try:
        output = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            text=True
        )
        return int(output.strip())
    except Exception as e:
        print(f"Error checking nvidia-smi: {e}")
        return 0

def run_parent():
    from hive.runtime.reservoir import Reservoir
    from hive.config import HiveConfig
    print("[PARENT] Initializing Reservoir...")
    config = HiveConfig(max_vram_mb=8000)
    res = Reservoir(config)
    print("[PARENT] Starting heavy cell (qwen2.5-coder:7b)...")
    res.infer("qwen2.5-coder:7b", 0, "Hello!")
    print("[PARENT] Heavy cell booted and VRAM should be populated.")
    print("[PARENT] Waiting for hard kill...")
    while True:
        time.sleep(1)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "child":
        run_parent()
        sys.exit(0)

    print("=== Phase I: Windows Job Object VRAM Reclamation Test ===")
    vram_before = get_vram_usage()
    print(f"VRAM before boot: {vram_before} MB")
    
    parent_proc = subprocess.Popen([sys.executable, __file__, "child"])
    
    print("Waiting 15 seconds for model to load into VRAM...")
    time.sleep(15)
    
    vram_during = get_vram_usage()
    print(f"VRAM during execution: {vram_during} MB")
    
    if vram_during <= vram_before + 1000:
        print("WARNING: VRAM didn't spike as expected, maybe model didn't load fully?")
    else:
        print(f"VRAM successfully spiked by {vram_during - vram_before} MB")

    print("\n[CHAOS] Executing hard taskkill /F on parent process...")
    subprocess.run(["taskkill", "/F", "/PID", str(parent_proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    print("Waiting 5 seconds for OS to process Job Object teardown...")
    time.sleep(5)
    
    vram_after = get_vram_usage()
    print(f"VRAM after parent hard kill: {vram_after} MB")
    
    if vram_after <= vram_before + 200:
        print("\n[SUCCESS] VRAM fully reclaimed! Windows Job Object correctly terminated orphaned children.")
    else:
        print("\n[FAILED] VRAM leak detected. Job object failed to terminate children.")
        sys.exit(1)
