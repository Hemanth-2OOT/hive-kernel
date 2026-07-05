"""
Phase J: Cold-Start Distribution Benchmark
===========================================
Pre-registered methodology (see review_bundle.md §15.2.1).

Sampling design decisions (decided before running, not after):
- N=30 per model.
- Each iteration: evict -> sleep 5s -> infer -> record wall-clock ms.
- Sleep + eviction between iterations prevents Ollama's warm-model cache
  from masking the tail variance that determines pool sizing.
- Measurement window: Reservoir.infer() call start -> first valid response
  (user-visible latency, not internal spawn time).
- Records per sample: wall_ms, cold_start (from telemetry), vram_mb_before.
- Pass/fail criterion (pre-registered):
    p95 < 6000ms AND stdev < 800ms -> unimodal -> single-slot pool sufficient.
    Otherwise -> re-evaluate pool design before implementing.

Output: benchmarks/results/cold_start_phase_j.json
        benchmarks/results/cold_start_phase_j_histogram.txt (ASCII)
"""
import json
import time
import statistics
import urllib.request
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hive.config import HiveConfig
from hive.runtime.reservoir import Reservoir

# -- Config --------------------------------------------------------------------
MODELS = ["qwen2.5-coder:7b"]      # extend to ["qwen2.5-coder:7b", "hermes3:8b"] if VRAM allows
N_ITERATIONS = 30
INTER_ITER_SLEEP_SEC = 5           # must be > 0 — see methodology rationale
TEST_PROMPT = "Say exactly: cold_start_benchmark_ok"
OUTPUT_JSON = os.path.join(os.path.dirname(__file__), "results", "cold_start_phase_j.json")
OUTPUT_HIST = os.path.join(os.path.dirname(__file__), "results", "cold_start_phase_j_histogram.txt")

# -- Pass/fail criterion (pre-registered) -------------------------------------
P95_THRESHOLD_MS = 6000
STDEV_THRESHOLD_MS = 800

# -- Helpers -------------------------------------------------------------------

def get_vram_mb():
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/ps") as r:
            ps = json.loads(r.read().decode())
        return sum(m.get("size_vram", 0) for m in ps.get("models", [])) // (1024 * 1024)
    except Exception:
        return -1


def percentile(data, p):
    """Simple percentile without numpy dependency."""
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(sorted_data) - 1)
    return sorted_data[lo] + (sorted_data[hi] - sorted_data[lo]) * (k - lo)


def ascii_histogram(data_ms, bins=20, width=60):
    """Return a plain ASCII histogram string."""
    lo, hi = min(data_ms), max(data_ms)
    bin_size = (hi - lo) / bins or 1
    counts = [0] * bins
    for v in data_ms:
        idx = min(int((v - lo) / bin_size), bins - 1)
        counts[idx] += 1
    max_count = max(counts) or 1
    lines = []
    lines.append(f"{'ms':>8}  {'count':>5}  histogram")
    lines.append("-" * (width + 20))
    for i, c in enumerate(counts):
        bucket_lo = lo + i * bin_size
        bar = "#" * int(c / max_count * width)
        lines.append(f"{bucket_lo:8.0f}  {c:5d}  {bar}")
    return "\n".join(lines)


# -- Main ---------------------------------------------------------------------

def run_model(model: str, config: HiveConfig):
    print(f"\n{'='*60}")
    print(f"Model: {model}  |  N={N_ITERATIONS}  |  sleep={INTER_ITER_SLEEP_SEC}s between iterations")
    print(f"{'='*60}")

    res = Reservoir(config)
    samples = []

    for i in range(N_ITERATIONS):
        # Step 1: ensure the model is evicted before each measurement
        with res.topology_lock:
            if model in res.cells:
                res._kill_cell_unsafe(model)

        vram_before = get_vram_mb()

        # Step 2: sleep — prevents Ollama warm-model cache from hiding tail variance
        print(f"  [{i+1:02d}/{N_ITERATIONS}] sleeping {INTER_ITER_SLEEP_SEC}s -> ", end="", flush=True)
        time.sleep(INTER_ITER_SLEEP_SEC)

        # Step 3: measure wall-clock time from infer() call to valid response
        t0 = time.perf_counter()
        result = res.infer(model, task_id=i + 1, payload=TEST_PROMPT)
        t1 = time.perf_counter()

        wall_ms = (t1 - t0) * 1000
        cold_start = result.get("telemetry", {}).get("cold_start", False)
        status = result.get("status", "?")

        samples.append({
            "iteration": i + 1,
            "wall_ms": round(wall_ms, 1),
            "cold_start": cold_start,
            "vram_mb_before": vram_before,
            "status": status,
        })

        print(f"{wall_ms:7.0f}ms  cold={cold_start}  vram_before={vram_before}MB  status={status}")

    # Step 4: final eviction
    with res.topology_lock:
        if model in res.cells:
            res._kill_cell_unsafe(model)

    return samples


def analyze(model: str, samples: list):
    wall_times = [s["wall_ms"] for s in samples if s["status"] == "done"]
    n = len(wall_times)

    if n == 0:
        print("  No successful samples to analyze.")
        return {}

    mn   = min(wall_times)
    mx   = max(wall_times)
    mean = statistics.mean(wall_times)
    stdev = statistics.stdev(wall_times) if n > 1 else 0.0
    p50  = percentile(wall_times, 50)
    p95  = percentile(wall_times, 95)
    p99  = percentile(wall_times, 99)

    print(f"\n-- Distribution ({model}, n={n}) -----------------------------")
    print(f"  min={mn:.0f}ms  max={mx:.0f}ms  mean={mean:.0f}ms  stdev={stdev:.0f}ms")
    print(f"  p50={p50:.0f}ms  p95={p95:.0f}ms  p99={p99:.0f}ms")

    # Pre-registered pass/fail
    verdict = "UNIMODAL — single-slot pool sufficient" \
        if p95 < P95_THRESHOLD_MS and stdev < STDEV_THRESHOLD_MS \
        else "HIGH-VARIANCE — re-evaluate pool design before implementing"
    print(f"\n  [VERDICT] p95={p95:.0f}ms (threshold {P95_THRESHOLD_MS}ms), "
          f"stdev={stdev:.0f}ms (threshold {STDEV_THRESHOLD_MS}ms)")
    print(f"  [VERDICT] {verdict}")

    hist = ascii_histogram(wall_times)
    print("\n" + hist)

    return {
        "model": model,
        "n": n,
        "min_ms": round(mn, 1),
        "max_ms": round(mx, 1),
        "mean_ms": round(mean, 1),
        "stdev_ms": round(stdev, 1),
        "p50_ms": round(p50, 1),
        "p95_ms": round(p95, 1),
        "p99_ms": round(p99, 1),
        "verdict": verdict,
        "histogram_ascii": hist,
    }


def main():
    config = HiveConfig()
    print("Phase J: Cold-Start Distribution Benchmark")
    print(f"Pre-registered methodology: N={N_ITERATIONS}, sleep={INTER_ITER_SLEEP_SEC}s/iter")
    print(f"Pass/fail: p95<{P95_THRESHOLD_MS}ms AND stdev<{STDEV_THRESHOLD_MS}ms -> single-slot pool")
    print(f"Output: {OUTPUT_JSON}")

    all_results = {"metadata": {
        "n_iterations": N_ITERATIONS,
        "inter_iter_sleep_sec": INTER_ITER_SLEEP_SEC,
        "p95_threshold_ms": P95_THRESHOLD_MS,
        "stdev_threshold_ms": STDEV_THRESHOLD_MS,
        "methodology": "pre-registered in review_bundle.md §15.2.1",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }, "models": {}}

    hist_lines = []

    for model in MODELS:
        samples = run_model(model, config)
        stats = analyze(model, samples)
        all_results["models"][model] = {"samples": samples, "stats": stats}
        hist_lines.append(f"=== {model} ===\n{stats.get('histogram_ascii', '')}\n")

    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w") as f:
        json.dump(all_results, f, indent=2)
    with open(OUTPUT_HIST, "w") as f:
        f.write("\n".join(hist_lines))

    print(f"\n[DONE] Results written to {OUTPUT_JSON}")
    print(f"[DONE] Histogram written to {OUTPUT_HIST}")


if __name__ == "__main__":
    main()
