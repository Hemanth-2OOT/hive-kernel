# Hive: Adversarial Audit Archive

## 1. Phase C: Forced Contention Race Condition
- **Audit**: `main_c_audit.py`
- **Subsystem**: Nucleus Executor / TaskGraph
- **Failure Injected**: 15 iterations of forced thread contention using a `threading.Barrier` to perfectly align worker thread completions on a multi-dependency task.
- **Expected Failure Mode**: Downstream task triggers prematurely due to a torn read of the DAG state.
- **Actual Bug Discovered**: *None.* The architecture proved immune.
- **Root Cause**: The Nucleus uses a strictly serialized event loop via a `queue.Queue()`.
- **Fix Implemented**: Documented the "Scheduler Single Writer Invariant" to protect the load-bearing design from future optimizations.
- **Invariant Created**: Scheduler Single Writer Invariant.

## 2. Phase C: Thread Crash Cascading
- **Audit**: `main_c_variant.py`
- **Subsystem**: Nucleus Executor
- **Failure Injected**: Simulated a catastrophic thread failure mid-execution in a wide DAG.
- **Expected Failure Mode**: Global deadlock or partial DAG execution.
- **Actual Bug Discovered**: Successfully caught and aborted downstream dependencies, degrading gracefully.
- **Fix Implemented**: Validated existing fail-safe cascade logic.

## 3. Phase D: Misdirected Apoptosis
- **Audit**: `main_d_audit.py`
- **Subsystem**: Reflex Engine / Hippocampus
- **Failure Injected**: Forced a dynamically spawned Reflex task to hit a hardware OOM ceiling.
- **Expected Failure Mode**: Reflex task dies; main DAG survives.
- **Actual Bug Discovered**: The OOM crashed the global executor, triggering Apoptosis and blindly penalizing an innocent semantic memory.
- **Root Cause**: The Nucleus lacked causal attribution for dynamically spawned tasks.
- **Fix Implemented**: Injected `source="reflex"` origin metadata. Nucleus now intercepts Reflex failures and cascades them harmlessly.
- **Invariant Created**: Reflex Failure Attribution Invariant.

## 4. Phase E: Lexical Overlap False Positives
- **Audit**: `main_e_audit.py`
- **Subsystem**: Hippocampus (Semantic Memory)
- **Failure Injected**: Pitted a true semantic match ("Translate to French") against a lexical-overlap hard negative ("Translate to Spanish").
- **Expected Failure Mode**: Threshold 0.5 correctly filters the negative.
- **Actual Bug Discovered**: The hard negative easily bypassed the threshold (0.747 > 0.718) and ranked #1, proving scalar thresholding fatally flawed.
- **Root Cause**: Cosine similarity is structural, not semantic. 
- **Fix Implemented**: Built a Two-Stage Retrieval Pipeline (`SemanticVerifier`) to intercept and explicitly verify Stage-1 candidates via an LLM Hard Cell before passing them to the Policy Validator. Also identified and fixed cross-cycle epoch staleness leaking memory during this phase.
- **Invariant Created**: Execution Epoch Isolation Invariant.

## 5. Phase G1: IPC Stream Desynchronization
- **Audit**: `main_g1_audit.py`
- **Subsystem**: Reservoir (Hard Cells)
- **Failure Injected**: Two concurrent tasks target the same Cell; the first task's thread is violently crashed exactly after writing to `stdin` but before reading `stdout`.
- **Expected Failure Mode**: The crashed task fails, the second task succeeds.
- **Actual Bug Discovered**: The lock released cleanly, leaving the first task's output orphaned in the pipe. The second task read the orphaned output, permanently shifting the IPC stream off-by-one.
- **Root Cause**: Separation of lock boundaries, or assumption of perfect thread survival across blocking I/O.
- **Fix Implemented**: Active identity checking using `task_id` prefixes in the read loop to detect mismatches and drain the pipe.
- **Invariant Created**: Atomic IPC Transaction Invariant.

## Lessons Learned from Adversarial Testing
Bugs in swarm architectures are rarely syntax errors; they are causal attribution failures, epoch staleness, and IPC desynchronizations. Designing an AI orchestration kernel requires treating ML models not as trusted intelligence, but as volatile, untrusted hardware peripherals. Architecture can only be proven under adversarial runtime conditions.
