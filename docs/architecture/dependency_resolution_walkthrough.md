# Phase C Audit: Dependency Resolution & Race Conditions

This document covers the empirical testing and verification of Phase C's dependency resolution logic, specifically focusing on multi-dependency race conditions and graceful degradation cascades under adversarial concurrency.

## The Hypothesis

Phase C is responsible for ensuring that the TaskGraph resolves correctly. Two major failure modes were hypothesized:
1. **Multi-Dependency Race Condition**: When a task (e.g., Task 3) depends on multiple upstream tasks (e.g., Task 1 and 2), and both complete at the exact same millisecond, could a torn state read cause Task 3 to fire prematurely before both results are fully written?
2. **Failed Dependency Cascade**: If a task fails mid-flight, do downstream dependencies correctly inherit the `FAILED` state and abort, or do they mistakenly execute on missing/corrupt data?

## Testing Methodology

Rather than relying on natural timing (which could pass purely by chance), we implemented forced contention using a `threading.Barrier` injected directly into the IPC `infer()` method.
This forced the worker threads for Task 1 and Task 2 to block until both arrived, and then release simultaneously, guaranteeing maximum contention on the executor's readiness checks. We ran this adversarial test in a loop of 15 iterations.

For the failed dependency cascade, we configured the `Reservoir` with a deliberate exception hook to simulate a thread crash mid-flight after a `flush()`, and monitored whether the downstream tasks aborted correctly.

## Results

> [!TIP]
> Both audits passed flawlessly. Phase C's dependency resolution is remarkably robust, and we now have empirical proof of its safety.

### 1. Multi-Dependency Race Condition: SAFE
The race condition test successfully ran through all 15 iterations under maximum forced contention without a single failure or torn read.

**Why it's safe:** The `ThreadPoolExecutor` does not mutate DAG state directly. Instead, worker threads place their results into a `queue.Queue()`. The `NucleusExecutor` runs a single-threaded event loop that pops from this queue sequentially. Because Python's `queue.Queue()` is thread-safe and the state mutation loop is single-threaded, it is architecturally impossible for a readiness check (`all(...)`) to observe a torn state dict. Phase G1's concurrency model inadvertently bulletproofed Phase C against multi-dependency race conditions!

### 2. Failed Dependency Cascade: SAFE
The cascade test successfully triggered a mid-flight crash in Task 1. The `NucleusExecutor` gracefully degraded, marked Task 1 as failed, and correctly cascaded the failure to Task 2. Task 2 was skipped with a "Dependency failed" error, completely preventing execution on corrupt data.

## Architectural Invariants

We have added a load-bearing comment to `nucleus_executor.py` explicitly documenting why this code is safe:

```python
# WARNING: ARCHITECTURAL INVARIANT
# Do NOT move state mutation or DAG readiness checks out of this single-threaded loop!
# The safety of Phase C multi-dependency resolution completely relies on `completion_queue`
# serializing all thread completions. If multiple threads were allowed to mutate `states` concurrently,
# torn reads could occur where a downstream task fires prematurely.
```

If a future refactor attempts to move state mutation out of the single-threaded event loop "for performance", this invariant will break and the race condition will resurface.
