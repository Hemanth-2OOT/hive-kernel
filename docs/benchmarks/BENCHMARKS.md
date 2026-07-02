# Hive: Benchmark Specification (Phase Z)

This document defines the methodology for validating the Hive kernel. The objective is to rigorously prove that its architectural complexity is mathematically justified by its fault containment, resilience, and resource bounding under adversarial conditions.

## 1. Baselines

To justify Hive, it must be measured against naive approaches and a strong industry-standard baseline.

| Baseline | Architecture | What it isolates |
| :--- | :--- | :--- |
| **Baseline A** | **Naive Sync** | Single-process blocking loop. All inference happens natively in the main thread. Isolates the absolute baseline of compute latency vs orchestration overhead. |
| **Baseline B** | **Subprocess Sequential** | Sequential execution with isolated subprocesses loaded on demand, but no parallel execution. Isolates subprocess IPC and startup overhead. |
| **Baseline C** | **Threadpool DAG** | Parallel execution with a naive threadpool and in-memory routing, but NO Reservoir (unbounded memory) and NO Stigmergy. Isolates standard concurrency scaling vs memory contention. |
| **Baseline E** | **Production Actor Runtime** | A "Ray-lite" architecture: worker pool, process isolation, bounded concurrency, and task queue, but NO stigmergy and NO semantic memory. Isolates the question: *Does Hive beat a well-engineered conventional runtime?* |
| **Baseline D** | **Full Hive Kernel** | Hard Cells + Reservoir + Nucleus + Reflex + Hippocampus. |

## 2. Core Metrics

### Latency & Throughput
- **p50, p95, p99 Latency**: End-to-end DAG execution time.
- **Throughput**: DAGs completed per second under sustained load.
- **Peak RSS / Avg RSS**: Resident Set Size across main process + all children.

### Orchestration Overhead Ratio
Critically measures how much time is spent on scheduling, locks, IPC, and memory bookkeeping versus actual inference.
`Overhead = (TotalRuntime - PureInferenceTime) / TotalRuntime`
*Goal*: Ensure Hive's overhead remains reasonable (< 40%).

### Fault Containment Index (FCI)
The primary metric validating Hive's existence. Measures the kernel's ability to survive fatal errors.
`FCI = 1 - (fatal_kernel_crashes / total_fault_injections)`
- **1.0**: Kernel always survives, seamlessly failing downstream tasks.
- **0.0**: Kernel completely crashes.
*Goal*: Hive must achieve an FCI of 1.0 against catastrophic failures where Baselines C and E collapse.

---

## Z1 — Microbenchmarks
*Focus: Measuring baseline orchestration tax.*
- **Workloads**: Raw IPC round-trips, lock acquisition contention, scheduler queue wakeup latency, and Hard Cell cold start times.
- **Iterations**: 1,000 – 10,000 iterations.
- **Goal**: Establish the absolute floor of the `Orchestration Overhead Ratio`.

## Z2 — Macro Workloads
*Focus: Real-world DAG performance and parallel scaling.*
- **Workloads**: 
  - **Simple Classification**: Deep 1x10 sequential chain.
  - **Mixed Multimodel DAG**: Branching DAG mixing generation and embedding.
  - **Wide Parallel DAG**: Massively parallel fan-out (1 -> 50 -> 1) to test ThreadPool bottlenecking.
  - **Memory Constrained DAG**: Forces the working set of models to wildly exceed the host `max_ram_mb` ceiling, triggering heavy evictions.
- **Iterations**: 30 – 100 iterations per workload.
- **Goal**: Compare Hive's latency and throughput against Baseline E. Hive may lose slightly on latency but must win dramatically on Peak RSS under constraints.

## Z3 — Chaos Engineering
*Focus: Calculating the Fault Containment Index (FCI).*
- **Fault Injections**:
  - **Worker Kill**: Random `kill -9` on worker threads.
  | Expected: DAG aborts dependencies; Kernel survives.
  - **Pipe Corruption**: Randomly close `stdin` mid-transaction.
  | Expected: Reservoir detects desync via `task_id`, drains pipe, and recovers.
  - **Forced OOM**: Synthetic `MemoryError` injected into ML process.
  | Expected: Reflex isolates it; Hippocampus triggers Apoptosis; Kernel survives.
- **Iterations**: 50 – 100 randomized faults.
- **Goal**: Prove that Baseline C and E suffer kernel corruption or deadlock, while Hive achieves an FCI of 1.0.

## Z4 — Long Soak (72-Hour Stability Test)
*Focus: Proving long-lived survival and zero corruption.*
- **Methodology**: Run continuous, randomized workloads (mixing Z2 and Z3 profiles) for 72 hours without restarting the main process.
- **Tracked Metrics**:
  - RSS over time (must plateau, proving no memory leaks).
  - Orphaned pipes and Zombie processes (must be zero).
  - Queue growth and Thread count drift.
  - Stale semantic cache checks (proving epoch isolation works).
- **Goal**: Prove the architecture is viable as a long-lived local OS daemon.

## Z5 — Ablation Studies
*Focus: Measuring subsystem necessity.*
- **Hive w/o Hard Cells**: Prove system leaks PyTorch memory linearly.
- **Hive w/o Reflex**: Prove system deadlocks/crashes when unpredictable congestion signals arise.
- **Hive w/o Hippocampus**: Prove system repeats cyclic adversarial task failures blindly (no Apoptosis).
- **Hive w/o SemanticVerifier**: Prove high False Positive rate corrupts DAG topologies.
- **Hive w/o Parallel Scheduler**: Prove unacceptable p50 latency scaling on Wide DAGs.

---

## Reviewer Verdict Criteria
Hive will not be judged as the "fastest local AI runtime". 
Hive will be judged as the "first fault-tolerant AI orchestration microkernel". 
If the suite demonstrates that Hive is marginally slower than Baseline E but achieves an **FCI of 1.0** and a **flat memory plateau during a 72-hour soak test**, the architectural complexity is entirely justified and the system is ready for publication.
