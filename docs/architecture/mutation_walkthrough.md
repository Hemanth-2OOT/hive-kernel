# Hive Phase D2: Dynamic DAG Mutation

## Architecture
Hive is now a dynamic, self-adapting machine intelligence. Through the introduction of the `ReflexEngine`, the Nucleus Executor can react to stigmergic signals in real-time, dynamically expanding the execution DAG to handle edge cases, uncertainty, and anomalies without requiring upfront LLM planning or external supervision.

## Deliverables

### `ReflexEngine`
A deterministic, rule-based mutation engine. It evaluates incoming signals against architectural thresholds.
For Phase D2, it implements the Ambiguity Reflex:
```python
if signal.signal_type == "ambiguity" and signal.strength > 0.7:
    # Spawn an LLM Verification task
```

### Dynamic Graph Injection
The `TaskGraph` structure was upgraded to support runtime mutation (`get_next_task_id()`). When the Reflex Engine emits a `"spawn_task"` action, the Nucleus constructs a new `Task` and injects it directly into the `TaskGraph` while execution is already underway.

### State-Machine Adaptability
Because we transitioned to a State-Driven Ready-Queue scheduler in Phase C2, injecting the new task was seamless. The Nucleus simply adds the newly spawned task to the `WAITING` queue. The state machine's natural unlock logic takes over, ensuring the new task executes exactly when its dynamically assigned dependencies are resolved.

## Benchmark Validation
We tested the system with a deliberately ambiguous input:
`"Classify this: Testing the reflex engine mutation directly. FORCE_AMBIGUITY"`

1. **Initial State**: The Cortex router rigidly parsed this into a single-node DAG (`classify`).
2. **Execution & Telemetry**: Task 1 (Sentiment) executed, hit the ambiguity threshold (0.55 confidence), and emitted a `0.90` strength Stigmergy Signal over IPC.
3. **Reflex Action**: The Nucleus detected the signal, queried the Reflex Engine, and dynamically injected `Task 2 (llm_verify)` into the DAG. Task 2 was meticulously configured to depend on Task 1 (ordering) but safely requested the `raw` input source so the LLM could read the original sentence.
4. **Adaptive Execution**: The Nucleus safely unlocked and executed Task 2, cold-starting the massive LLM cell to double-check the ambiguous work produced by the smaller sentiment model.

**Status**: Phase D2 is completely verified. Hive successfully demonstrated decentralized Stigmergy leading to autonomous dynamic scaling!
