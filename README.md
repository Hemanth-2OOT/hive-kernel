# Hive 🐝

**A Local AI Orchestration Kernel**

Hive is not an agent, nor is it an LLM framework. It is a Python prototype of a task-orchestration system modeled strictly on OS process scheduling and biological swarm coordination. It solves the inherent instability, memory leaks, and hardware constraints of modern ML workflows by treating Large Language Models as isolated, volatile hardware resources that must be managed by a robust kernel.

## Core Features
- **Hard Cells**: PyTorch models are wrapped in isolated OS subprocesses to completely eliminate memory leaks.
- **Reservoir**: A physical resource manager that enforces memory ceilings via predictive scheduling and preemptive eviction.
- **Nucleus Executor**: A lock-free, event-driven DAG scheduler that prevents torn reads and handles multi-dependency parallel execution.
- **Hippocampus**: A semantic memory subsystem that utilizes Apoptosis (forgetting) to penalize and decay toxic DAG mutations that lead to crashes.
- **Stigmergy & Reflexes**: Cells emit asynchronous signals (e.g., congestion, confusion) which the Reflex Engine evaluates to dynamically mutate the DAG at runtime.

## Design Philosophy
Hive operates on the **Hard Cell Hypothesis**: modern ML frameworks are architecturally unstable for long-running autonomous swarms. Therefore, intelligence must be physically isolated across IPC boundaries, and the orchestration layer must fail closed, degrade gracefully, and aggressively prioritize its own survival over the completion of any individual task.

## Subsystems Overview
- `TaskGraph`: Canonical state machine tracking dependency resolution.
- `Reservoir`: Subprocess lifecycle and physical resource arbitration.
- `NucleusExecutor`: The central threaded event-loop managing task dispatch and state mutation.
- `ReflexEngine`: Evaluates emitted signals to dynamically spawn tasks or evict cells.
- `Consolidator`: Asynchronously distills execution traces into semantic lessons.
- `PolicyValidator`: Mutates incoming DAGs based on verified semantic memory.

## Adversarial Testing Highlights
Hive's architecture was forged through rigorous adversarial audits. We fixed bugs that only appear in high-pressure runtime conditions:
- **Misdirected Apoptosis**: Prevented dynamically spawned Reflex tasks from crashing the global executor and corrupting semantic memory.
- **Epoch Isolation**: Eliminated cross-cycle caching staleness and unbounded memory leaks via strict `task_id` dictionary eviction on success and failure paths.
- **IPC Desynchronization**: Secured atomic IPC boundaries against catastrophic thread crashes mid-transaction to prevent stream off-by-one errors.

## Benchmark Results
*[Placeholder: Phase Z Benchmarking Data]*

## Future Work
- Learned routing and adaptive DAG synthesis (upgrading the Reflex Engine from heuristics to decision policies).
- Multi-node distributed swarm orchestration.
- Integration with complex edge workloads.
