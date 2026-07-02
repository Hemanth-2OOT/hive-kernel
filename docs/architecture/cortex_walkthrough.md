# Hive Phase C1: Cortex Router

## Architecture
The Cortex Router is the front-end parser for the Hive architecture. It operates strictly deterministically (without LLMs) to map natural language intents into a rigorous Directed Acyclic Graph (DAG) representing a multi-step execution plan.

## Deliverables

### `task_graph.py`
Defines the structure of the pipeline.
- `Task` structure containing: `id`, `type`, `depends_on`, and `input_source` (either `raw` or `dependency`).
- `TaskGraph` container for JSON serialization.

### `cortex.py`
The rule-based DAG generator. 
Rather than guessing dependencies based on sentence grammar (which is brittle), it relies on a hardcoded architectural truth table:
```python
self.rules = {
    "sentiment": ["summarize"],
    "classify": ["summarize"],
    "embed": ["summarize", "generate"],
    "summarize": ["generate"],
    "generate": []
}
```
This forces the tasks into a strict topological sort, ensuring that when the resulting TaskGraph is passed down to the Nucleus scheduler, data will flow correctly from node to node.

## Verification
A standalone harness (`main_c1.py`) was run against complex multi-intent sentences, producing perfectly structured graphs exactly as specified. 

For example, `"Generate article, summarize it, then classify and embed it"` correctly produced a 4-node DAG where node 1 generated, node 2 depended on 1, and nodes 3 and 4 correctly depended on the upstream tasks.

**Status**: Phase C1 is complete and strictly tested in isolation.
