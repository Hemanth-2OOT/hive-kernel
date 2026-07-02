# Hive Phase F2B: Swarm-Native Semantic Learning

## Architecture
Hive has achieved self-modification and optimization without the need for fragile centralized databases or explicit rule engines. By harnessing its existing `Hippocampus` semantic memory, Hive naturally gravitates toward efficient DAG execution, reinforcing successful pathways and physically suppressing mutations that lead to failure.

## Deliverables

### The Biological Learning Loop
1. **The Oracle (Mutation Generation)**: When an inefficient DAG runs, the Oracle explicitly encodes structured optimization targets (`remove_task`, `target_task`) directly into the final `ExecutionContext` trace.
2. **The Consolidator (Memory Storage)**: The semantic lesson is permanently saved in the Hippocampus, carrying the mutation proposals as payload metadata.
3. **The Policy Validator (Interceptor)**: When Cortex initiates a new execution, the `PolicyValidator` performs a semantic lookahead. It retrieves the highest-confidence prior lessons. If it discovers an optimization, it clones the DAG and applies the mutation. 
    - **Safety Guards**: It ensures *Sink Preservation*. It will unconditionally reject an optimization if removing a task strands downstream consumers or deletes the only remaining task in the graph.
    - **Stochastic Exploration**: It randomly ignores optimizations `10%` of the time to continually explore the base behavior and prevent premature optimization collapse.
4. **The Nucleus (Apoptosis & Decay)**: If the Validator-mutated DAG is executed, and it induces a `RuntimeError` (e.g. strict RAM out-of-bounds, dependency failure), the Nucleus instantly issues a penalty command. The Hippocampus physically mutates the vector metadata, applying a `0.10x` decay multiplier to the exact memory that provided the fatal suggestion, burying it in the retrieval space.

## Benchmark Validation
We stress-tested the associative learning engine using `main_f2b.py`.

1. **Initial Experience**: Fed a heavy DAG to the swarm. It successfully stored an `OptimizationSuggestion` to remove an unused `embed` task.
2. **Reinforcement**: Fed the exact same intent again. The `PolicyValidator` intercepted the query, correctly retrieved the optimization from memory, validated sink preservation, and successfully **mutated the DAG** at runtime to skip the `embed` step!
3. **Poison Test**: We severely choked the swarm's RAM to `100MB` to induce a fatal crash during the optimized execution. The Nucleus caught the `RuntimeError` and triggered Hippocampus Apoptosis.
4. **Verification**: When querying the Hippocampus afterward, the decay penalty was fully engaged, slashing the offending memory's retrieval score to `0.10`, ensuring the swarm would permanently "forget" the dangerous optimization.

**Status**: Phase F2B is verified! Hive is now a safe, self-optimizing semantic swarm.
