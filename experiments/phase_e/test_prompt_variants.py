import time
from hive.runtime.reservoir import Reservoir

def test_prompts():
    res = Reservoir(max_vram_mb=6000, idle_ttl_sec=300)
    
    test_cases = [
        # The 2 True Positives that failed (False Negatives)
        {"type": "TP", "query": "Can you convert the following English sentence to French?", "candidate": "Translate this text into French.", "expected": "YES"},
        {"type": "TP", "query": "Compose a haiku about a rainy day.", "candidate": "Write a short poem about the rain.", "expected": "YES"},
        
        # The 5 Hard Negatives that passed (True Negatives)
        {"type": "HN", "query": "How do I convert a PyTorch tensor to a NumPy array?", "candidate": "How do I fix a CUDA OutOfMemoryError in PyTorch?", "expected": "NO"},
        {"type": "HN", "query": "Write a python script to scrape rust off metal.", "candidate": "Write a python script to scrape data from a website.", "expected": "NO"},
        {"type": "HN", "query": "Translate this text into Spanish.", "candidate": "Translate this text into French.", "expected": "NO"},
        {"type": "HN", "query": "Create a React component for a date picker.", "candidate": "Create a React component for a dropdown menu.", "expected": "NO"},
        {"type": "HN", "query": "Write a short poem about the sun.", "candidate": "Write a short poem about the rain.", "expected": "NO"},
    ]
    
    variants = {
        "Variant_B_Looser": """Task: Determine if the candidate memory solves the same underlying intent as the QUERY, even if phrased differently.
However, completely different specific tasks (e.g. translating to a different language, or a date picker vs dropdown) means NO.

QUERY: {query}
CANDIDATE: {candidate}

Output EXACTLY one word: YES or NO.
OUTPUT:""",
        "Variant_C_Reasoning": """Task: Are these two requests asking for the same type of output or solving the same core problem?
If they ask for different specific things (like translating to Spanish vs French, or sun vs rain), output NO.
If they ask for the same thing in different words (like a poem vs haiku about rain), output YES.

QUERY: {query}
CANDIDATE: {candidate}

Output EXACTLY one word: YES or NO.
OUTPUT:"""
    }
    
    for v_name, v_prompt in variants.items():
        print(f"\n=== Testing {v_name} ===")
        tp_passed = 0
        hn_passed = 0
        
        for case in test_cases:
            prompt = v_prompt.format(query=case["query"], candidate=case["candidate"])
            try:
                raw_response = res.infer(cell_type="hermes3:8b", task_id=0, payload=prompt)
                text_resp = raw_response["result"]["text"].strip().upper()
                
                is_yes = "YES" in text_resp
                is_no = "NO" in text_resp
                
                actual = "UNKNOWN"
                if is_yes and not is_no:
                    actual = "YES"
                elif is_no and not is_yes:
                    actual = "NO"
                
                passed = (actual == case["expected"])
                
                if case["type"] == "TP" and passed: tp_passed += 1
                if case["type"] == "HN" and passed: hn_passed += 1
                
                print(f"[{case['type']}] Expected {case['expected']} | Got {actual} | {'PASS' if passed else 'FAIL'} | Q: {case['query'][:30]}...")
            except Exception as e:
                print(f"Error: {e}")
                
        print(f"Summary for {v_name}: TP {tp_passed}/2 passed, HN {hn_passed}/5 passed.")
        
    res.shutdown()

if __name__ == "__main__":
    test_prompts()
