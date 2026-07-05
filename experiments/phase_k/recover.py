import json
import time
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cold_start_baseline_30 import analyze

times = [
    9775, 10094, 9937, 10411, 10440, 9446, 10521, 9817, 10498, 11143,
    10403, 8233, 10409, 10129, 10556, 10857, 10149, 10343, 10602, 10397,
    9947, 10583, 9261, 10444, 10426, 10389, 10301, 10379, 10141, 10016
]

samples = []
for i, t in enumerate(times):
    samples.append({
        "iteration": i + 1,
        "wall_ms": t,
        "cold_start": True,
        "vram_mb_before": 0,
        "status": "done"
    })

OUTPUT_JSON = os.path.join(os.path.dirname(__file__), "results", "cold_start_phase_j.json")
OUTPUT_HIST = os.path.join(os.path.dirname(__file__), "results", "cold_start_phase_j_histogram.txt")

all_results = {"metadata": {
    "n_iterations": 30,
    "inter_iter_sleep_sec": 5,
    "p95_threshold_ms": 6000,
    "stdev_threshold_ms": 800,
    "methodology": "pre-registered in review_bundle.md \u00a715.2.1",
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
}, "models": {}}

model = "qwen2.5-coder:7b"
stats = analyze(model, samples)
all_results["models"][model] = {"samples": samples, "stats": stats}

os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
with open(OUTPUT_JSON, "w") as f:
    json.dump(all_results, f, indent=2)
with open(OUTPUT_HIST, "w") as f:
    f.write(f"=== {model} ===\n{stats.get('histogram_ascii', '')}\n")

print(f"\n[DONE] Results written to {OUTPUT_JSON}")
print(f"[DONE] Histogram written to {OUTPUT_HIST}")
