# Hive Kernel

> Experimental fault-tolerant local AI orchestration as an operating system problem.

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![Status](https://img.shields.io/badge/status-research_prototype-orange)
![License](https://img.shields.io/badge/license-MIT-green)

Hive is a research-oriented experimental fault-tolerant local AI orchestration microkernel. It is designed to run multiple ML workloads under constrained hardware (consumer laptops / edge devices). Hive is not a chatbot, an agent wrapper, or an AutoGPT clone. 

It treats AI execution as an operating systems problem, optimizing for survival, fault containment, and memory safety over raw throughput.

---

## The Problem Statement

Running complex, multi-model AI workflows on local hardware usually ends in catastrophic failure. Existing AI orchestration systems and naive pipelines fail because they do not respect the physical constraints of the host machine:

- **VRAM Exhaustion:** Loading multiple large models simultaneously instantly crashes the GPU.
- **RAM Leaks:** Long-running Python processes hosting PyTorch inevitably fragment and leak memory.
- **Subprocess Crashes:** When an ML worker hits a `MemoryError` or CUDA out-of-memory error, it takes down the entire parent orchestration process.
- **Agent Deadlocks:** Swarm architectures frequently stall when inter-process communication (IPC) desynchronizes.
- **Poor Fault Isolation:** A failure in a downstream summarization task shouldn't crash the entire routing system.

Naive pipelines are fragile. When the hardware runs out of breath, the whole system dies.

### Why this matters

Modern local AI stacks assume abundant resources or cloud execution. That assumption breaks on consumer hardware where RAM, VRAM, and process isolation become first-order constraints.

Hive explores a different question:

> Can AI orchestration be designed like a microkernel that survives hardware hostility?

---

## Why Hive Exists

Why build Hive instead of using Ray, Threadpools, Agent frameworks, or Async pipelines?

- **Ray / Celery:** Designed for distributed clusters with massive resources, not tightly constrained single-machine edge devices where memory swapping is lethal.
- **Standard Threadpools:** Loading PyTorch models into threads within the same process leads to shared-state corruption and GIL bottlenecks. If one thread OOMs, the OS kills the entire process.
- **Agent Frameworks (AutoGPT, LangChain):** These focus on API routing and prompt chaining, blindly trusting that the underlying compute environment has infinite capacity.

**Hive optimizes for survival and fault containment.** It operates under the assumption that ML processes *will* crash, hang, and exhaust resources. When a model fails, Hive isolates the failure, gracefully degrades the specific execution branch, and keeps the global scheduler alive.

---

## Experimental Validation Philosophy

Hive was developed strictly through adversarial systems audits, not just happy-path demonstrations. Every major subsystem was intentionally stress-tested under race conditions, OOM (out-of-memory) pressure, deadlocks, IPC stream corruption, and unhandled lifecycle crashes. 

Hive only considers a subsystem “complete” once its failure modes are empirically understood, isolated, and bounded. Patching around lucky behavior is rejected in favor of explicit, bounded, and testable engineering guarantees.

---

## 🏗️ Core Architecture

Hive isolates execution logic from orchestration logic. 

```text
       User Request
            ↓
      [Cortex Router]
            ↓
    [Nucleus Scheduler]  ←──(DAG Orchestration)
            ↓
       [Reservoir]       ←──(Memory Management & Eviction)
            ↓
       [Hard Cells]      ←──(Isolated ML Subprocesses)
            ↓
      (ML Inference)
            ↺
[Reflex Engine + Hippocampus] ←──(Adaptive Recovery & Semantic Memory)
```

---

## Empirical Proofs / Key Findings

The following are the strongest empirical results derived during adversarial phase auditing:

### Hard Cell Isolation
- **PyTorch leak containment:** Achieved via strict OS subprocess isolation.
- **Latency improvement:** Context switching dropped from ~8,000ms to ~38ms via optimized IPC piping.
- **Memory Safety:** Proved that generative LLM KV caches plateau and are reliably flushed rather than leaking unboundedly into the orchestrator.

### VRAM Scheduling (Phase B)
- **Environment:** Tested on an RTX 4050 Laptop GPU (6GB VRAM constraint).
- **Workloads:** `hermes3:8b` (≈ 5300MB) and `qwen2.5-coder:7b` (≈ 4900MB).
- **Result:** Attempting to run both models concurrently caused a ~300% latency spike due to extreme PCIe thrashing.
- **Solution:** Hive now strictly enforces a single-heavyweight-model scheduling topology. Deadlocks during model eviction are prevented via a deterministic locking hierarchy.

### Parallel DAG Execution
- Hive relies on a `ThreadPoolExecutor` for concurrent graph resolution.
- To eliminate torn reads and race conditions during DAG evaluation, state mutations are rigorously single-threaded through a queue-based serialization mechanism.

### Fault Containment Index
- Internal chaos engineering benchmarks achieved a **Fault Containment Index (FCI) = 1.0**.
- *FCI is defined as: the fraction of subsystem failures contained without global scheduler collapse.* Hive successfully isolates 100% of injected worker crashes, OOMs, and torn writes.

---

## Major Bugs Discovered During Audits

The adversarial auditing philosophy surfaced several subtle race conditions and systems bugs that were systematically isolated and repaired:

| Bug | Failure Mode | Fix |
|---|---|---|
| **Misdirected Apoptosis Bug** | An OOM failure in a dynamic Reflex task caused the global executor to blindly penalize an innocent semantic memory. | Intercepted OOMs and injected "task origin" metadata, cleanly cascading failures down the specific DAG branch while protecting the Hippocampus. |
| **IPC Stream Desynchronization** | A thread crashing mid-flight left orphaned output in the IPC pipe, permanently shifting the communication stream off-by-one for all future concurrent callers. | Implemented robust `task_id` identity verification, transparently draining orphaned lines to instantly restore synchronization. |
| **Torn Write Deadlock** | A mid-write crash produced malformed JSON; the child consumed the next thread's payload trying to complete it, returning a null task ID and deadlocking the parent's read loop. | Intercepted null task IDs as fatal errors, failing-fast with a `RuntimeError` to break the deadlock and leave the pipe clean. |
| **Infinite Retry Bug** | Requesting a model whose baseline footprint exceeded the absolute hardware VRAM ceiling caused the scheduler to infinitely retry and hang the swarm. | Proactively implemented a fail-fast mechanism throwing a terminal `MemoryError` before attempting impossible allocations. |
| **Shutdown Rug-Pull Race** | Calling `hive.shutdown()` before process exit aggressively tore down the Reservoir while detached asynchronous Consolidator threads were still writing memory traces. | Added explicit execution tracking and a bounded asynchronous shutdown wait-loop to safely land background tasks. |
| **Ghost Cell VRAM Leak** | Unhandled interpreter crashes (`os._exit` or `SIGINT`) bypassed standard teardown, leaving gigabyte-sized models permanently marooned in VRAM. | Leveraged OS pipe EOF guarantees to trigger a synchronous C-level cleanup hook directly inside the child process loop exit. |

---

## Architectural Invariants

The following load-bearing rules govern Hive's codebase. Violating these invariants may silently corrupt scheduler correctness and reintroduce deadlocks:

* **Reservoir write/read operations must remain atomic inside `cell_lock`**: Splitting them for performance breaks IPC synchronization and stacks orphaned lines.
* **DAG readiness mutation must remain single-threaded**: Worker threads must queue their completions. Multi-threaded DAG evaluation reintroduces torn reads.
* **External code must never pre-acquire Reservoir cell locks**: Modifying the deterministic locking order will result in circular wait OS-level deadlocks.
* **Impossible VRAM requests must fail fast**: The orchestrator must not attempt to fulfill allocation requests that exceed absolute hardware ceilings.

---

## Research Scope / Non-Goals

Hive intentionally does **NOT** optimize for:
- Raw throughput or sub-millisecond latency.
- Cloud-scale distributed serving across multiple host machines.
- State-of-the-art model accuracy or zero-shot routing precision.
- Agent autonomy or unconstrained reasoning loops.

Hive specifically optimizes for:
- **Survival** under extreme hardware hostility.
- **Bounded failure** and predictable degradation.
- **Memory correctness** and explicit cleanup.
- **Safe local orchestration** on constrained consumer edge devices.

---

## 🚀 Installation & Quick Start

Hive is packaged as a local Python library. It requires Python 3.10+.

```bash
git clone https://github.com/Hemanth-2OOT/hive-kernel.git
cd hive-kernel
pip install -e .
```

### Quick Start

```python
import hive

# Run a single instruction through the fully orchestrated Swarm
context = hive.run("Summarize the impact of torn-write deadlocks in IPC communication.")

# The HiveEngine singleton lazily initializes on the first run, 
# gracefully handles concurrent requests, and manages its own safe teardown.
```
