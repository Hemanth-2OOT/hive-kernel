import numpy as np
from hive.runtime.reservoir import Reservoir

def cosine_similarity(vec1, vec2):
    vec1 = [float(x) for x in vec1]
    vec2 = [float(x) for x in vec2]
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = sum(a * a for a in vec1) ** 0.5
    norm2 = sum(b * b for b in vec2) ** 0.5
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)

def test_held_out():
    res = Reservoir(max_vram_mb=6000, idle_ttl_sec=300)
    
    held_out_cases = [
        {"type": "TP_NEW", "query": "Can you change this English sentence into German?", "candidate": "Translate this text into German."},
        {"type": "HN_NEW", "query": "Translate this text into Italian.", "candidate": "Translate this text into German."},
        {"type": "TP_NEW", "query": "How do I build a custom modal in Vue?", "candidate": "Create a Vue component for a modal."},
        {"type": "HN_NEW", "query": "Create a Vue component for a tooltip.", "candidate": "Create a Vue component for a modal."},
        {"type": "TP_NEW", "query": "Draft an article discussing space exploration.", "candidate": "Write a short essay about space exploration."},
        {"type": "HN_NEW", "query": "Write a short essay about deep sea diving.", "candidate": "Write a short essay about space exploration."},
    ]
    
    strict_prompt = """Task: Compare the underlying intent and specific parameters/entities between the QUERY and the CANDIDATE.
Step 1: Identify the core action/intent.
Step 2: Identify the specific parameters/entities involved (e.g., target language, specific error name, subject of a poem, specific UI component type).
Step 3: If the core action is the same AND all specific parameters/entities match (or are synonymous), output YES. If ANY specific parameter (like target language, subject, or UI component) differs, you MUST output NO.

QUERY: {query}
CANDIDATE: {candidate}

Output EXACTLY one word: YES or NO.
OUTPUT:"""

    print("=== HELD-OUT GENERALIZATION TEST ===")
    print(f"{'Type':<8} | {'Cosine':<6} | {'LLM':<4} | {'Query':<35} | {'Candidate':<35}")
    print("-" * 100)
    
    for case in held_out_cases:
        # Get embeddings
        q_raw = res.infer(cell_type="embedding", task_id=0, payload=case["query"])["result"]
        c_raw = res.infer(cell_type="embedding", task_id=0, payload=case["candidate"])["result"]
        import json
        q_emb = json.loads(q_raw) if isinstance(q_raw, str) else q_raw
        c_emb = json.loads(c_raw) if isinstance(c_raw, str) else c_raw
        if isinstance(q_emb, dict):
            q_emb = q_emb.get("embedding", q_emb.get("vector", []))
        if isinstance(c_emb, dict):
            c_emb = c_emb.get("embedding", c_emb.get("vector", []))
        
        sim = cosine_similarity(q_emb, c_emb)
        
        # Get LLM verification
        prompt = strict_prompt.format(query=case["query"], candidate=case["candidate"])
        try:
            raw_response = res.infer(cell_type="hermes3:8b", task_id=0, payload=prompt)
            text_resp = raw_response["result"]["text"].strip().upper()
            llm_val = "YES" if "YES" in text_resp else "NO"
        except:
            llm_val = "ERR"
            
        print(f"{case['type']:<8} | {sim:.4f} | {llm_val:<4} | {case['query'][:35]:<35} | {case['candidate'][:35]:<35}")

    print("\n=== DETERMINISM CHECK ===")
    hard_cases = [
        {"name": "Spanish/French HN", "query": "Translate this text into Spanish.", "candidate": "Translate this text into French."},
        {"name": "DatePicker/Dropdown HN", "query": "Create a React component for a date picker.", "candidate": "Create a React component for a dropdown menu."}
    ]
    
    for case in hard_cases:
        print(f"\nTesting: {case['name']}")
        prompt = strict_prompt.format(query=case["query"], candidate=case["candidate"])
        for i in range(3):
            try:
                raw_response = res.infer(cell_type="hermes3:8b", task_id=i+1, payload=prompt)
                text_resp = raw_response["result"]["text"].strip().upper()
                llm_val = "YES" if "YES" in text_resp else "NO"
                print(f"  Run {i+1}: {llm_val}")
            except Exception as e:
                print(f"  Run {i+1}: ERR ({e})")

    res.shutdown()

if __name__ == "__main__":
    test_held_out()
