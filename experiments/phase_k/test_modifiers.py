import os
from hive.runtime.reservoir import Reservoir
from hive.config import HiveConfig
from hive.memory.verifier import SemanticVerifier

def main():
    config = HiveConfig(max_vram_mb=6000)
    res = Reservoir(config)
    verifier = SemanticVerifier(res, cell_name="hermes3:8b")

    pairs = [
        ("Summarize this article", "Give me a summary of this article"),
        ("Fix this bug in my code", "Debug this issue in my code"),
        ("How do I install the latest python?", "How do I install the new python version?"),
        ("Change the font size of the header", "Make the header text larger")
    ]
    
    print("Running modifier/rephrasing test...\n")
    
    for i, (q, c) in enumerate(pairs):
        prompt = verifier.VERIFY_PROMPT_TEMPLATE.format(query=q, candidate_content=c)
        try:
            resp = res.infer("hermes3:8b", payload=prompt, task_id=900+i)
            print(f"--- Pair {i+1} ---")
            print(f"Q: {q}")
            print(f"C: {c}")
            print("Trace:\n" + resp["result"]["text"].strip() + "\n")
        except Exception as e:
            print(f"Failed pair {i+1}: {e}")
            
    res.shutdown()

if __name__ == "__main__":
    main()
