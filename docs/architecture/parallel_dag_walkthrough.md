# Phase G1 Audit: IPC Stream Desynchronization

## Audit Objective
Phase G1 transformed the Nucleus into a concurrent scheduler using `ThreadPoolExecutor`. The AI workers (cells) are stateful processes accessed via a single `stdin`/`stdout` pipe, protected by a mutex `cell_lock`. 

We hypothesized that if a Python worker thread acquired the `cell_lock`, successfully transmitted its payload, and then forcefully crashed *before* consuming the output, the Python runtime would automatically release the lock. The orphaned response line would remain in the cell's `stdout` pipe buffer, causing the *next* concurrent thread to instantly read the previous task's output instead of its own, leading to a permanent, unrecoverable off-by-one IPC cascade for the rest of the node's uptime.

## The Bug: Unpatched Execution
We created `main_g1_audit.py` with 4 concurrent/sequential tasks targeting the LLM cell, modifying `llm_server.py` to prepend `[RESPONSE TO TASK X]` to the generated text.

We injected a 2-line exception hook into `Reservoir.infer()` specifically keyed to `task_id == 1` and a `CRASH_CLIENT_MIDFLIGHT` payload to precisely simulate a thread dying mid-flight.

When we ran the unpatched system, the output proved the hypothesis:

```text
[NUCLEUS] Submitting Task 1 (generate) to ThreadPool
[NUCLEUS] Submitting Task 2 (generate) to ThreadPool
[RESERVOIR] DELIBERATE CRASH mid-flight for Task 1 after flush()!
[NUCLEUS] Execution Failed: Mid-flight thread crash simulated
[HARNESS] Caught expected mid-flight crash: Mid-flight thread crash simulated

...
[DEBUG] IPC Stream Results:
Task 3 (Should be Bananas): [RESPONSE TO TASK 2] The client crashed during the mid-flight.
Task 4 (Should be Carrots): [RESPONSE TO TASK 3] are a good source of potassium. Bananas are a good source of potassium.
```

The system completely lost its bearings. Task 3 consumed Task 2's output. Task 4 consumed Task 3's output. All answers from that cell forward would be mismatched.

## The Fix: Identity-Enforced Draining
Because we already pass `task_id` back and forth via the IPC protocol JSON, the most robust architectural fix was enforcing identity validation at read time. 

Instead of a single `readline()`, the `Reservoir` now loops until it reads a payload containing the `task_id` of the executing thread. Any lines belonging to an unexpected `task_id` are identified as orphaned, drained from the pipe, explicitly logged, and discarded.

```python
while True:
    line = proc.stdout.readline()
    if not line:
        raise RuntimeError(f"Cell {cell_type} closed stdout unexpectedly")
        
    resp = json.loads(line)
    resp_task_id = resp.get("task_id")
    
    if resp_task_id == task_id:
        break
    else:
        print(f"[{cell_type.upper()}] DRAINED ORPHANED LINE (Expected {task_id}, Got {resp_task_id}): {line.strip()}", flush=True)
```

## Verification Result: Patched Execution
Running the exact same test sequence against the patched executor yielded a perfect recovery:

```text
[RESERVOIR] DELIBERATE CRASH mid-flight for Task 1 after flush()!
[LLM] DRAINED ORPHANED LINE (Expected 2, Got 1): {"task_id": 1, "status": "done", "result": {"text": "[RESPONSE TO TASK 1] The client crashed during the mid-flight."}}
[NUCLEUS] Execution Failed: Mid-flight thread crash simulated
...
[DEBUG] IPC Stream Results:
Task 3 (Should be Bananas): [RESPONSE TO TASK 3] are a good source of potassium. Bananas are a good source of potassium.
Task 4 (Should be Carrots): [RESPONSE TO TASK 4] are a good source of vitamin A.
[TEST SUCCESS] IPC Stream is synchronized correctly.
```

The bug was successfully reproduced, contained, and permanently eliminated. Phase G1 has earned its proven status!

> [!NOTE]
> **Known Untested Edge Case (Torn Writes)**
> This audit specifically proved resilience against a clean crash *after* `flush()` but *before* `readline()`. A messier crash *during* the write itself could leave a torn or partial JSON line on the pipe. This would corrupt the line itself, meaning `json.loads()` on the child side would likely throw an error. This is a different failure shape (a corrupt stream rather than an orphaned response) and remains an untested edge case for future audits.
