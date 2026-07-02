# Hive Phase F1: Meta-Cognition Engine (Oracle)

## Architecture
Hive can now evaluate and critique its own operational workflows. By introducing the Meta-Cognition Engine (`Oracle`), the Nucleus can step back from task execution and perform a post-mortem analysis of the entire `ExecutionContext`. This allows the colony to detect structural inefficiencies, redundant tasks, and memory bottlenecks, passing these optimized suggestions directly into its Long-Term Memory.

## Deliverables

### The Meta-Cognition Oracle
The `oracle.py` engine is invoked strictly *after* the DAG has completed. It ingests the raw execution trace, including the Task Graph and physical telemetry metrics, and evaluates it against structural optimization rules.
For Phase F1, we implemented five foundational rules:
1. **Repeated Cold Starts**: Detects if the swarm is thrashing (frequent booting).
2. **Eviction Frequency**: Diagnoses if the `Reservoir` RAM budget is too heavily constrained relative to the workload.
3. **Redundant Validation**: Checks if expensive LLM verification cells were spun up unnecessarily (e.g., if a smaller classifier had already achieved >0.90 confidence).
4. **Dead Ends**: Identifies tasks whose outputs were completely ignored by downstream dependencies.
5. **Prompt Merging**: Detects sequentially dependent tasks that are being routed to the exact same physical cell (e.g., using the LLM to `generate`, and then explicitly passing that back into the LLM to `summarize`), suggesting they be merged into a single payload.

### Context Telemetry
The `ExecutionContext` was extended to track runtime hardware performance:
- `total_latency`
- `peak_ram_mb`
- `cold_starts`
- `evictions`

These telemetry metrics are now explicitly serialized and consolidated alongside the semantic outcomes.

## Benchmark Validation
We forced the Nucleus to execute a brutally inefficient DAG (`generate` -> `classify` -> `summarize` -> `llm_verify` -> `embed`) inside a suffocating `1600 MB` RAM budget on a trivially clear sentence (`"This is a brilliantly clear and positive day!"`).

**Results**:
- The tight budget forced `3` evictions and `5` cold-starts.
- The `classify` task achieved an overwhelming `0.9999` confidence.
- The Oracle intercepted the finalized trace and **successfully detected all 5 inefficiencies**, appending the following recommendations into the Hippocampus memory:
  - `Repeated cold starts detected (5).`
  - `System memory budget too tight (Peak RAM: 1412.6MB, Evictions: 3).`
  - `Task 4 (llm_verify) is redundant. Upstream sentiment already had high confidence (0.9999). Suggest removing.`
  - `Task 5 (embed) output is never used downstream. Suggest removal.`
  - `Tasks 1 (generate) and 3 (summarize) route to the same physical cell (llm). Suggest merging.`

**Status**: Phase F1 is verified! The Oracle is operational.
