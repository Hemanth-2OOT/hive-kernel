from hive.runtime.reservoir import Reservoir
from hive.config import HiveConfig

config = HiveConfig(max_vram_mb=6000)
res = Reservoir(config)

prompt = """Task: Compare the underlying intent and specific parameters/entities between the QUERY and the CANDIDATE.

Before judging semantic equivalence, first extract the primary subject/data-structure/entity each query operates on (e.g. "string", "linked list", "array", "salary", "employee record").

Two queries are equivalent ONLY IF:
1. The primary subject/entity matches exactly or is a clear synonym, AND
2. The action/intent matches.

If the subject/entity differs (e.g. "string" vs "linked list", "lowest" vs "second highest" as distinct target values), the queries are NOT equivalent, even if the surrounding task structure or phrasing is very similar. Similarity of approach or algorithm is not sufficient for equivalence — the operated-on object and the specific target must both match.

When entities differ in name, ask: do they refer to the same underlying mechanism or class of thing (e.g. "tarball" and "backup" — a tarball IS a backup mechanism, or "reverse proxy" and "forward requests" — forwarding requests IS the function of a reverse proxy), or are they genuinely different sub-types/targets within the same category (e.g. "haiku" IS A poem, but a different specific kind — treat sub-types and distinct targets as non-equivalent)? Only merge in the former case.

Respond with your reasoning: first state the extracted subject/entity for each query, then state the extracted action, then give your final equivalence judgment on a new line exactly as "FINAL_JUDGMENT: YES" or "FINAL_JUDGMENT: NO".

QUERY: Compose a haiku about a rainy day.
CANDIDATE: Write a short poem about the rain.

OUTPUT:"""

try:
    print("Calling Hermes3 on Cluster 5 True Positive...")
    resp = res.infer("hermes3:8b", payload=prompt, task_id=999)
    print("\n--- REASONING TRACE ---")
    print(resp.get("result", {}).get("text", resp))
    print("-----------------------")
finally:
    res.shutdown()
