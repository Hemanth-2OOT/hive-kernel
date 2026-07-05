"""
Direct subprocess-level verification: spawn llm_server.py with keep_alive_sec=360
and intercept its stdout handshake, then confirm /api/ps shows ~360s expiry.
This verifies the argv→int()→request-body chain inside the child process itself.
"""
import subprocess
import sys
import json
import time
import urllib.request
from datetime import datetime, timezone

KEEP_ALIVE_SEC = 360
MODEL = "qwen2.5-coder:7b"
script = "cells/llm_server.py"

print(f"Spawning llm_server.py with argv: ['{MODEL}', '{KEEP_ALIVE_SEC}']")

proc = subprocess.Popen(
    ["python", script, MODEL, str(KEEP_ALIVE_SEC)],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    text=True,
    bufsize=1
)

# Read handshake
boot = json.loads(proc.stdout.readline())
ready = json.loads(proc.stdout.readline())
print(f"Boot: {boot}")
print(f"Ready: {ready}")

# Send one inference request
req_payload = json.dumps({"task_id": 99, "payload": "Say: argv_wire_test_ok"}) + "\n"
proc.stdin.write(req_payload)
proc.stdin.flush()

resp = json.loads(proc.stdout.readline())
print(f"Inference response: {resp}")

# Now check /api/ps — this is the ground truth from Ollama itself
print("\n=== /api/ps Expiry (Ollama ground truth) ===")
try:
    with urllib.request.urlopen("http://localhost:11434/api/ps") as r:
        ps = json.loads(r.read().decode())
    for m in ps.get("models", []):
        if MODEL in m.get("name", ""):
            exp_str = m.get("expires_at", "")
            now_utc = datetime.now(timezone.utc)
            exp = datetime.fromisoformat(exp_str.replace("Z", "+00:00"))
            secs = (exp - now_utc).total_seconds()
            print(f"  model={m['name']}")
            print(f"  expires_at={exp_str}")
            print(f"  expires_in={secs:.1f}s")
            print(f"  expected=~{KEEP_ALIVE_SEC}s")
            margin = abs(secs - KEEP_ALIVE_SEC)
            if margin < 30:
                print(f"  [OK] keep_alive={KEEP_ALIVE_SEC} confirmed in Ollama (margin={margin:.1f}s)")
                # The margin is a fixed offset: inference round-trip + /api/ps query lag +
                # Ollama computing expires_at from request-received rather than sent time.
                # It is NOT proportional to KEEP_ALIVE_SEC. If this value is ever tightened
                # significantly (e.g. to 10s for a latency-sensitive workload), re-evaluate
                # the 30s pass threshold — a 2s absolute offset is benign at 360s, but
                # would be a large fraction of a 10s target.
            else:
                print(f"  [FAIL] Margin {margin:.1f}s > 30s — value may not have reached Ollama")
            # Also check that it's NOT the default 300s (5 min Ollama default)
            if abs(secs - 300) < 30:
                print(f"  [FAIL] Expiry matches Ollama default (300s) — keep_alive was likely ignored")
except Exception as e:
    print(f"  /api/ps error: {e}")

# Clean kill via keep_alive:0
proc.stdin.close()
proc.wait(timeout=10)
print("\nChild exited cleanly.")
