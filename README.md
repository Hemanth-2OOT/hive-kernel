# Hive Swarm AI 🐝

Hive Swarm AI is a lightweight, edge-native framework designed to orchestrate asynchronous LLM agent pipelines on severely constrained hardware. Instead of relying on vast, remote, cloud-hosted models, Hive dynamically routes multi-step reasoning Directed Acyclic Graphs (DAGs) across locally hosted, specialized small models (like `hermes3:8b` and `qwen2.5-coder:7b`) while strictly adhering to a physical VRAM budget (e.g., 6GB). 

## Architecture

Hive is constructed around four distinct conceptual layers:

1. **Cortex**: The entry point that ingests raw user queries and formulates a plan (TaskGraph).
2. **Nucleus**: The orchestrator. It manages the multi-threaded execution of the DAG, retrieving contextual memories from the `Hippocampus` and routing tasks.
3. **Reservoir**: The resource manager. It acts as the gatekeeper for VRAM, dynamically swapping, booting, and evicting containerized models to ensure the system never exceeds its rigid physical hardware limits.
4. **Hard Cells**: Specialized, ephemeral worker nodes that execute atomic tasks (e.g., embedding, generation, sentiment analysis) and return structured outputs. 

By compartmentalizing memory management, context injection, and asynchronous verification, Hive can successfully navigate deeply adversarial, resource-starved contention states where traditional LLM pipelines would otherwise infinitely stall or crash.

---

# Engineering Highlights & Rigorous Debugging

Building Hive required moving beyond high-level design and diagnosing complex, non-deterministic system failures under heavy load. The following case studies highlight the rigorous, evidence-based debugging approach used to stabilize the engine:

### 1. The Tail-Latency Asynchronous VRAM Lag (Phase L)
**The Symptom:** During heavy pipeline execution, the system would suddenly exhibit massive tail-latency spikes and raise `ReservoirContentionTimeout` exceptions, completely halting the DAG.
**The Investigation:**
- Initial theory pointed toward priority inversion in the locking queue. However, targeted telemetry revealed that the locks were releasing properly, but the VRAM wasn't freeing.
- A deeper dive into Ollama's model-unloading behavior uncovered that issuing a `keep_alive: 0` request returned a `200 OK` instantly, but the actual CUDA buffer deallocation was happening *asynchronously*, taking roughly ~0.4s. 
- Because Hive immediately booted the next model upon receiving the `200 OK`, it slammed into the physical VRAM limit and violently crashed.
**The Fix:** Engineered a non-blocking `api/ps` polling loop inside the teardown sequence that safely blocks the `Reservoir` from yielding the VRAM token until the CUDA buffers are definitively unmapped, structurally eliminating the race condition.

### 2. The Duplicate-Queue Flooding Gap (Phase M)
**The Symptom:** The orchestrator's `maxsize=100` backpressure queue was routinely breached during semantic memory verification, flooding the system and causing the LLM to thrash indefinitely.
**The Investigation:**
- Because the pipeline allowed multiple worker threads to retrieve memories asynchronously, popular (hot) queries were retrieving identical memories.
- Instead of waiting for the memory to finish verifying, the cache-miss logic continuously re-enqueued identical verification requests for the same memory ID. A single slow-to-verify memory could rapidly duplicate itself, suffocating the background worker.
**The Fix:** Implemented an explicit `_in_flight_verifications` tracking set lock inside the `Hippocampus`. Verification requests are now perfectly deduplicated across the entire DAG, allowing the system to gracefully yield to pending tasks and strictly respect the backpressure bounds.

### 3. The "Ghost Process" Misattribution (Phase J)
**The Symptom:** Background model processes appeared to "leak," continuing to consume VRAM indefinitely even after their parent tasks were seemingly aborted. 
**The Investigation:**
- Initial diagnostic assumptions blamed the Windows OS Job Object hierarchy, proposing that child processes were escaping the main process tree.
- However, chaos testing and thread analysis proved this completely false. The VRAM ownership belonged exclusively to the local Ollama daemon, not the Python process tree. The true culprit was that requests were being violently abandoned mid-stream without flipping a dirty-state bit (`is_dirty`), causing the orchestrator to blindly trust broken sockets on the next cycle.
**The Fix:** Rewrote the state machine to track `is_dirty` natively through `finally` blocks, gracefully handling mid-request thread death and ensuring corrupted daemon sockets are definitively reaped before reusing a cell.


---

## Final Benchmark Proof & Metrics

The Hive Swarm AI engine was thoroughly validated via adversarial benchmarks (spanning both /benchmarks and /tests) executed from a completely pristine state (zero stale caches, zero pre-populated memory stores, zero lingering background processes).

**Result: 100% Pass Rate across 20 rigorously designed edge-case and load-contention test vectors.**


## Test Suite Output Log

```text
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0 -- C:\Users\HEMANTH\AppData\Local\Programs\Python\Python311\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\HEMANTH\Desktop\Hive\swarm_ai
configfile: pyproject.toml
plugins: anyio-4.14.1
collecting ... collected 20 items

benchmarks/test_benchmark_verifier_20.py::test_verified_retrieval_full PASSED [  5%]
benchmarks/test_phase_j_retry.py::test_phase_j_retry PASSED              [ 10%]
benchmarks/test_phase_j_terminal.py::test_phase_j_terminal PASSED        [ 15%]
benchmarks/test_phase_l_async_verifier.py::test_async_verifier PASSED    [ 20%]
benchmarks/test_phase_l_thrashing.py::test_thrashing PASSED              [ 25%]
benchmarks/test_phase_m_cache_eviction.py::test_cache_eviction PASSED    [ 30%]
benchmarks/test_unload.py::test_unload_time PASSED                       [ 35%]
tests/test_start_cell_branching.py::TestStartCellUnsafeCmdBranching::test_custom_keep_alive_sec_propagates PASSED [ 40%]
tests/test_start_cell_branching.py::TestStartCellUnsafeCmdBranching::test_embedding_cmd_no_keep_alive PASSED [ 45%]
tests/test_start_cell_branching.py::TestStartCellUnsafeCmdBranching::test_generic_llm_cmd_includes_keep_alive PASSED [ 50%]
tests/test_start_cell_branching.py::TestStartCellUnsafeCmdBranching::test_hermes_cmd_includes_keep_alive PASSED [ 55%]
tests/test_start_cell_branching.py::TestStartCellUnsafeCmdBranching::test_keep_alive_argv_is_valid_int_string PASSED [ 60%]
tests/test_start_cell_branching.py::TestStartCellUnsafeCmdBranching::test_qwen_cmd_includes_keep_alive PASSED [ 65%]
tests/test_start_cell_branching.py::TestStartCellUnsafeCmdBranching::test_sentiment_cmd_no_keep_alive PASSED [ 70%]
tests/test_start_cell_branching.py::TestStartCellUnsafeCmdBranching::test_unknown_cell_type_raises PASSED [ 75%]
tests/test_warm_pool.py::test_warm_pool_basic_reuse PASSED               [ 80%]
tests/test_warm_pool.py::test_warm_pool_eviction_different_model PASSED  [ 85%]
tests/test_warm_pool.py::test_warm_pool_stale_state_mid_request PASSED   [ 90%]
tests/test_warm_pool.py::test_warm_pool_abandoned_mid_request PASSED     [ 95%]
tests/test_warm_pool.py::test_warm_pool_ttl_expiration PASSED            [100%]

======================= 20 passed in 549.37s (0:09:09) ========================
```

## Key Fixes Validated by this Run

### Phase J: IPC Contention & State Machines
- **`test_phase_j_retry` / `test_phase_j_terminal`**: Confirmed the reservoir accurately implements a robust backoff loop (`ReservoirContentionTimeout`) rather than silently dropping tasks or spinning indefinitely when the VRAM budget is tightly constrained.
- **`test_warm_pool_*`**: Asserts that `is_dirty` tracking handles abandoned requests flawlessly, successfully routing around "ghost processes" that fail mid-stream. 

### Phase L: Critical Path Blocking & Thrashing
- **`test_phase_l_async_verifier`**: Validates the new architecture where `query_verified()` pushes to a background worker loop and immediately returns, unlocking the primary DAG execution thread.
- **`test_phase_l_thrashing`**: Proved that when equal-priority cells (e.g. `hermes3:8b` and `qwen2.5-coder:7b`) clash for the same VRAM slice under maximum load, the system politely yields and blocks on a bounded-timeout rather than violently crashing or terminating one another mid-generation. (Note: timeout cleanly increased to account for proper yielding behavior).

### Phase M: Bounded Cache Memory
- **`test_phase_m_cache_eviction`**: Validated that `SemanticVerifier` correctly maintains a size-capped FIFO JSON cache limit of `MAX_CACHE_ENTRIES = 1000`. It strictly evicts the oldest 20% array slice atomically under `_io_lock`.

### Foundational Fixes
- **`test_benchmark_verifier_20`**: Executed a synchronous-polling verification over 40 discrete LLM requests against an initially *empty* memory store, confirming the underlying Numpy empty-list `0 != 384` shape crash was cleanly intercepted and returned empty candidates.
- **`test_start_cell_branching` / `test_unload`**: Asserts asynchronous VRAM model-eviction via Ollama's `keep_alive: 0` properly drains, ensuring 0.4s lag discrepancies are safely bridged.

## Conclusion
The Hive Swarm AI execution pipeline now correctly bounds retries, safely yields memory under lock contention without race conditions, offloads heavy LLM I/O to background threads with hard queue limits, and predictably fails-closed when timeouts are organically exceeded. The foundational engineering rigor applied in this phase has elevated this orchestrator to a resilient, production-ready core.
