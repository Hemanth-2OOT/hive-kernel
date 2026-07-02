# Hive Reservoir v0.2: OS-Level Scheduler

## Architecture Overview
The Reservoir has officially transitioned from a simple subprocess wrapper into a fully-fledged, predictive OS-level memory scheduler. It treats Hive Cells as memory pages and manages them according to strict bounds and dynamic lifecycle heuristics.

## Implemented Features

### 1. Predictive Memory Reservation
Instead of reacting to an Out-Of-Memory event after a cell allocates its PyTorch tensors, the Reservoir now guarantees safety *before* spawning.
```python
CELL_PROFILES = {"sentiment": 550, "embedding": 400, "llm": 1500}
```
`ensure_capacity(required_mb)` verifies that `current_rss + required_mb <= max_ram_mb`. If this budget is breached, it actively frees memory before spawning the new cell.

### 2. Weighted Eviction Heuristic (Priority LRU)
Evicting purely on "oldest used" is naive because cells have asymmetric memory footprints and asymmetric importance. Evicting a 1.5GB LLM is more valuable than evicting a 50MB regex cell.
The scheduler selects victims using:
```python
score = (rss * idle_seconds) / priority
```
This forces the scheduler to favor killing massive, long-idle models, while protecting lightweight, highly-prioritized models.

### 3. Idle TTL Garbage Collection
Any cell that remains idle for longer than the defined TTL (e.g., 300 seconds) is automatically violently terminated, preventing baseline memory creep from abandoned workflows.

### 4. Seamless Respawning
If a workflow attempts to `.infer()` against a cell that the scheduler previously evicted, the Reservoir automatically intercepts the request, forces a synchronous cold-start respawn, and then successfully routes the inference without raising errors to the caller.

## Benchmark Validation
Using a severely restricted `2000 MB` budget limit, we concurrently requested an LLM (1500MB), an Embedder (400MB), and a Sentiment Classifier (550MB).
1. The Scheduler successfully spawned the LLM and Embedder (`~1800 MB`).
2. Upon requesting the Sentiment Classifier (`+550 MB = 2350 MB`), the scheduler correctly identified that the budget would be breached. It calculated that the LLM had the highest weighted score, violently killed it, and safely spawned the Classifier. Total RAM plummeted to `~893 MB`.
3. When the LLM was requested again later, it seamlessly respawned, automatically evicting *both* the Embedder and Classifier to clear the necessary 1500MB reservation.

**Status**: Phase B (Eviction Policy) is completely validated.
