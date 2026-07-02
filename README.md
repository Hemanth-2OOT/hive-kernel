# Hive Kernel

> Experimental fault-tolerant local AI orchestration as an operating system problem.

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![Status](https://img.shields.io/badge/status-research_prototype-orange)
![License](https://img.shields.io/badge/license-MIT-green)

Hive is a research-oriented **experimental fault-tolerant local AI orchestration microkernel**. It is designed to run multiple ML workloads under constrained hardware (consumer laptops / edge devices). Hive is **not** a chatbot, an agent wrapper, or an AutoGPT clone. 

It treats AI execution as an **operating systems problem**, optimizing for survival, fault containment, and memory safety over raw speed.

---

## 🛑 The Problem Statement

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

## 🛠️ Why Hive Exists

Why build Hive instead of using Ray, Threadpools, Agent frameworks, or Async pipelines?

- **Ray / Celery:** Designed for distributed clusters with massive resources, not tightly constrained single-machine edge devices where memory swapping is lethal.
- **Standard Threadpools:** Loading PyTorch models into threads within the same process leads to shared-state corruption and GIL bottlenecks. If one thread OOMs, the OS kills the entire process.
- **Agent Frameworks (AutoGPT, LangChain):** These focus on API routing and prompt chaining, blindly trusting that the underlying compute environment has infinite capacity.

**Hive optimizes for survival and fault containment.** It operates under the assumption that ML processes *will* crash, hang, and exhaust resources. When a model fails, Hive isolates the failure, gracefully degrades the specific execution branch, and keeps the global scheduler alive.

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

## 📂 Repository Structure

```text
hive/
 ├─ core/         # Scheduling and DAG execution
 ├─ runtime/      # Memory + process management
 ├─ adaptation/   # Reflex and routing adaptation
 └─ memory/       # Semantic memory systems

cells/            # Isolated ML subprocess workers
benchmarks/       # Phase Z benchmark suite
tests/            # Runtime tests
docs/             # Architecture and audit notes
experiments/      # Historical development phases
```

---

## ✨ Key Features

- **Fault Containment:** Hard cell architecture completely isolates ML worker crashes from the central orchestration loop.
- **Memory-Bounded Execution:** The Reservoir actively monitors RSS and evicts idle or lower-priority models to strictly respect user-defined RAM caps.
- **DAG Scheduling:** Translates complex workflows into directed acyclic graphs for parallel execution.
- **Adaptive Recovery:** Cascades failures seamlessly. If a branch fails due to resource exhaustion, it gracefully degrades rather than deadlocking.
- **Semantic Memory:** Learns from past execution topologies, bypassing redundant task branches by recalling cached state.
- **Benchmark Suite:** Comes with a rigorous Phase Z benchmark suite targeting micro-latencies and chaos engineering.

---

## 📊 Benchmark Summary

Hive was tested against an aggressive Phase Z benchmark on consumer hardware (i7-12650HX, 16GB RAM, RTX 4050 6GB). 

- **Cold Start Penalty:** `4.369s` (OS subprocess initialization)
- **IPC Round-Trip (p50):** `0.016s` (Highly efficient pipe serialization)
- **Sequential DAG Latency:** `~1.10s`
- **Parallel DAG Latency:** `3.15s`
- **Memory Pressure Test:** `7.61s` @ `1200MB cap`
- **Internal FCI benchmark score:** `1.0`

**Conclusion:** Hive is not the fastest runtime—spinning up OS subprocesses incurs a heavy cold-start tax. However, under extreme memory constraints (capping RAM at 1200MB while attempting to load >2.5GB of models), Hive cleanly failed downstream dependencies, gracefully degraded, and kept the kernel alive. **It survives conditions where naive systems crash.**

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
from hive.core.nucleus import Nucleus
from hive.runtime.reservoir import Reservoir
from hive.core.dag import TaskGraph, Task

# Initialize runtime with strict memory bounds
reservoir = Reservoir(max_ram_mb=1200)
nucleus = Nucleus(reservoir)

# Define a simple execution graph
g = TaskGraph()
g.add_task(Task(1, "generate", [], "raw_input"))

# Execute the graph safely
nucleus.execute(g, "What is the capital of France?")

# Clean up subprocesses
reservoir.shutdown()
```
Or run the built-in demo entrypoint:
```bash
python -m hive
```

---

## ⚠️ Current Limitations

Hive remains a research prototype.

Known limitations:
- High cold-start latency due to subprocess boot cost.
- Routing policies remain heuristic-based.
- Limited evaluation on production-scale workloads.
- Complexity overhead may not justify simple sequential workloads.
- Not optimized for distributed multi-machine execution.

---

## 🔬 Research Context

Hive does not claim to invent entirely new theoretical primitives.

Instead, it synthesizes ideas from:
- operating systems
- actor runtimes
- DAG schedulers
- fault-tolerant distributed systems
- semantic memory architectures

Its novelty lies in combining these concepts into a resilient local AI orchestration kernel.
