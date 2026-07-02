# Hive: Master Architecture Specification

## 1. Executive Summary
Hive is a Python prototype of a local task-orchestration system modeled strictly on OS process scheduling and biological swarm coordination. Its core design philosophy is to solve the inherent instability and memory leaks of modern ML workflows by treating Large Language Models (LLMs) not as application logic, but as isolated, volatile hardware resources that must be managed, scheduled, and ruthlessly evicted by a robust kernel.

## 2. System Components
- **Cortex Router**: The entry point that interprets raw user input and compiles it into an initial Directed Acyclic Graph (DAG) of semantic intents.
- **TaskGraph**: The canonical state machine of a cycle, tracking dependency chains and task completion states.
- **Nucleus Executor**: The central OS-like scheduler. It manages a `ThreadPoolExecutor` and dynamically routes tasks to the Reservoir via a single-threaded state mutation loop to guarantee race-free dependency resolution.
- **Reservoir**: The physical resource manager. It wraps ML models in isolated subprocesses ("Hard Cells"), handles IPC streaming, and enforces eviction heuristics when RAM ceilings are hit.
- **Reflex Engine**: The Stigmergy handler. It evaluates asynchronous worker signals (e.g., congestion, confusion) and dynamically mutates the DAG (spawning new tasks or evicting cells) at runtime.
- **Hippocampus**: The memory subsystem. It handles episodic trace serialization and semantic memory (vector embeddings), applying an Apoptosis (forgetting) decay factor when traces lead to failure.
- **Consolidator**: An asynchronous worker that distills complex execution traces into dense semantic lessons without blocking the Nucleus teardown.
- **Oracle**: A meta-cognitive observer that analyzes execution telemetry to recommend future structural improvements.
- **Policy Validator**: An interception layer that mutates the initial TaskGraph based on past experiences (semantic memory) retrieved from the Hippocampus.

## 3. Execution Lifecycle
1. **Input & Compilation**: The user provides raw text. Cortex compiles it into a `TaskGraph`.
2. **Recall & Interception**: The `Nucleus Executor` queries `Hippocampus` for relevant past experiences, passing verified candidates to the `Policy Validator`, which mutates the DAG.
3. **Execution Loop**: The Nucleus dispatches READY tasks to a `ThreadPoolExecutor`.
4. **Resolution**: Workers interact with the `Reservoir` (IPC). Worker completions are placed on a thread-safe `completion_queue`.
5. **State Mutation**: A single-threaded event loop processes the `completion_queue`, updating `TaskGraph` states and resolving downstream dependencies.
6. **Teardown & Consolidation**: Upon completion or failure, the trace is serialized and handed to the asynchronous `Consolidator`. `Hippocampus` cache variables are evicted via a `finally` block to prevent leaks.

## 4. Memory Lifecycle
- **Episodic**: Raw execution traces (latency, memory, signals, outcomes) are logged sequentially.
- **Semantic**: The `Consolidator` distills traces into text lessons, stored as vector embeddings in the `Hippocampus`.
- **Apoptosis**: If a DAG crashes due to a dynamic mutation or OOM, the kernel penalizes the specific semantic memory that triggered the mutation, multiplying its decay factor. This ensures toxic behaviors are forgotten.

## 5. Signal Lifecycle
- **Stigmergy**: Cells emit pheromone-like `Signals` (e.g., `memory_pressure`, `confusion`) during inference.
- **Reflex Execution**: The Nucleus collects signals and passes them to the `Reflex Engine`.
- **Dynamic Mutation**: The Reflex Engine can inject emergency tasks (e.g., fallback summarization) or trigger preemptive evictions to save the swarm from crashing.

## 6. Concurrency Model
- **Thread Ownership**: Workers only interact with stateless cell inference. They do not own or mutate the DAG.
- **Event Loop**: All state mutations and readiness checks happen synchronously in the Nucleus's main thread reading from a blocking queue.
- **IPC Streaming**: The `Reservoir` uses a strict `cell_lock` to serialize `stdin` writes and `stdout` reads, guaranteeing atomicity at the subprocess boundary.

## 7. Critical Architectural Invariants
> [!IMPORTANT]
> The following invariants are load-bearing. Violating them will result in unrepairable state corruption.

- **Scheduler Single Writer**: State mutation and DAG readiness checks MUST occur inside the single-threaded Nucleus event loop.
- **Atomic IPC Transaction**: `write` and `read` operations to a Hard Cell MUST remain strictly serialized together inside the `Reservoir`'s `cell_lock`.
- **Execution Epoch Isolation**: `Hippocampus` cache variables must be strictly keyed by `task_id` (cycle ID) and aggressively popped upon cycle exit to prevent memory leaks and cross-cycle staleness.
- **Reflex Failure Attribution**: Dynamically spawned tasks must be tagged (`source="reflex"`) so their OOM failures gracefully cascade without aborting the main execution pipeline.

## 8. Known Limitations
- **Verifier Accuracy**: The `SemanticVerifier` is structurally sound but currently relies on a 0.5B local model incapable of zero-shot semantic discrimination.
- **Algorithmic Simplicity**: Decision policies (routing, heuristics) are currently rule-based, not learned.
- **Cross-Node Orchestration**: Hive is strictly a local orchestration kernel; distributed swarm topology is deferred.
