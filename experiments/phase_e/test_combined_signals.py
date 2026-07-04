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

def test_combined():
    res = Reservoir(max_vram_mb=6000, idle_ttl_sec=300)
    
    test_cases = [
        {"type": "TP", "query": "My PyTorch model is running out of GPU memory during training, what can I do?", "candidate": "How do I fix a CUDA OutOfMemoryError in PyTorch?"},
        {"type": "TP", "query": "How can I extract data from HTML using Python?", "candidate": "Write a python script to scrape data from a website."},
        {"type": "TP", "query": "How do I build a custom select component in React?", "candidate": "Create a React component for a dropdown menu."},
        {"type": "TP_REC", "query": "Can you convert the following English sentence to French?", "candidate": "Translate this text into French."},
        {"type": "TP_REC", "query": "Compose a haiku about a rainy day.", "candidate": "Write a short poem about the rain."},
        {"type": "HN", "query": "How do I convert a PyTorch tensor to a NumPy array?", "candidate": "How do I fix a CUDA OutOfMemoryError in PyTorch?"},
        {"type": "HN", "query": "Write a python script to scrape rust off metal.", "candidate": "Write a python script to scrape data from a website."},
        {"type": "HN", "query": "Translate this text into Spanish.", "candidate": "Translate this text into French."},
        {"type": "HN", "query": "Create a React component for a date picker.", "candidate": "Create a React component for a dropdown menu."},
        {"type": "HN", "query": "Write a short poem about the sun.", "candidate": "Write a short poem about the rain."},
    ]
    
    strict_prompt = """Task: Compare the underlying intent and specific parameters/entities between the QUERY and the CANDIDATE.
Step 1: Identify the core action/intent.
Step 2: Identify the specific parameters/entities involved (e.g., target language, specific error name, subject of a poem, specific UI component type).
Step 3: If the core action is the same AND all specific parameters/entities match (or are synonymous), output YES. If ANY specific parameter (like target language, subject, or UI component) differs, you MUST output NO.

QUERY: {query}
CANDIDATE: {candidate}

Output EXACTLY one word: YES or NO.
OUTPUT:"""

    print(f"{'Type':<8} | {'Cosine':<6} | {'LLM':<4} | {'Query':<35} | {'Candidate':<35}")
    print("-" * 100)
    
    for case in test_cases:
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

    res.shutdown()

if __name__ == "__main__":
    test_combined()
