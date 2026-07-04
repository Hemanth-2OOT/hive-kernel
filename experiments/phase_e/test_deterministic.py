import time
from hive.runtime.reservoir import Reservoir

def test_det():
    res = Reservoir(max_vram_mb=6000, idle_ttl_sec=300)
    
    strict_prompt = """Task: Determine if the candidate memory is EXACTLY the same underlying task/intent as the QUERY.
Lexical overlap (e.g. translating to different languages) means NO.

QUERY: {query}
CANDIDATE: {candidate}

Output EXACTLY one word: YES or NO.
OUTPUT:"""

    q = "Translate this text into Spanish."
    c = "Translate this text into French."
    
    prompt = strict_prompt.format(query=q, candidate=c)
    
    print("=== Testing deterministic output for HN (Spanish vs French) ===")
    
    results = []
    for i in range(10):
        try:
            raw = res.infer(cell_type="hermes3:8b", task_id=0, payload=prompt)
            resp = raw["result"]["text"].strip().upper()
            val = "YES" if "YES" in resp else "NO"
            results.append(val)
            print(f"Run {i+1}: {val}")
        except Exception as e:
            print(f"Error: {e}")
            
    yes_count = results.count("YES")
    no_count = results.count("NO")
    print(f"\nSummary: YES: {yes_count}/10, NO: {no_count}/10")
    
    res.shutdown()

if __name__ == "__main__":
    test_det()
