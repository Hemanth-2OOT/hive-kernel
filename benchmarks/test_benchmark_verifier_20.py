import os
import shutil
import json
from hive.runtime.reservoir import Reservoir
from hive.memory.hippocampus import Hippocampus
from hive.memory.verifier import SemanticVerifier
from hive.config import HiveConfig

def test_verified_retrieval_full():
    print("=== Phase K: Verifier Benchmark (n=20) ===")
    
    if os.path.exists("data"):
        for f in ["semantic.npy", "semantic_meta.json", "episodic.jsonl"]:
            p = os.path.join("data", f)
            if os.path.exists(p):
                os.remove(p)
        
    config = HiveConfig(max_vram_mb=6000)
    res = Reservoir(config)
    verifier = SemanticVerifier(res, cell_name="hermes3:8b") 
    hippo = Hippocampus(res, verifier=verifier, config=config)
    
    clusters = {
        "1": {"A": "How do I fix a CUDA OutOfMemoryError in PyTorch?", "B": "My PyTorch model is running out of GPU memory during training, what can I do?", "D": "How do I convert a PyTorch tensor to a NumPy array?"},
        "2": {"A": "Write a python script to scrape data from a website.", "B": "How can I extract data from HTML using Python?", "D": "Write a python script to scrape rust off metal."},
        "3": {"A": "Translate this text into French.", "B": "Can you convert the following English sentence to French?", "D": "Translate this text into Spanish."},
        "4": {"A": "Create a React component for a dropdown menu.", "B": "How do I build a custom select component in React?", "D": "Create a React component for a date picker."},
        "5": {"A": "Write a short poem about the rain.", "B": "Write a short poem about a rainy day.", "D": "Write a short poem about the sun."},
        "6": {"A": "How do I reverse a linked list in C++?", "B": "What is the C++ code to invert a singly linked list?", "D": "How do I reverse a string in C++?"},
        "7": {"A": "Explain quantum entanglement to a 5 year old.", "B": "Can you describe how quantum entanglement works simply?", "D": "Explain quantum computing to a college student."},
        "8": {"A": "What are the health benefits of green tea?", "B": "Why is drinking green tea good for you?", "D": "What are the health benefits of black coffee?"},
        "9": {"A": "How do I bake a chocolate cake from scratch?", "B": "What is a good recipe for homemade chocolate cake?", "D": "How do I bake chocolate chip cookies?"},
        "10": {"A": "Write a SQL query to find the second highest salary.", "B": "How do I get the max salary excluding the absolute highest in SQL?", "D": "Write a SQL query to find the lowest salary."},
        "11": {"A": "What is the capital of Australia?", "B": "Which city is the capital of Australia?", "D": "What is the capital of Austria?"},
        "12": {"A": "How do I tie a Windsor knot?", "B": "Can you give me instructions for tying a Windsor knot?", "D": "How do I tie my shoelaces?"},
        "13": {"A": "Explain the difference between TCP and UDP.", "B": "Compare the TCP and UDP network protocols.", "D": "Explain the difference between IPv4 and IPv6."},
        "14": {"A": "Write a bash script to backup a directory.", "B": "How can I create a tarball of a folder in a shell script?", "D": "Write a bash script to delete a directory."},
        "15": {"A": "What are the rules of chess?", "B": "How do you play chess?", "D": "What are the rules of checkers?"},
        "16": {"A": "How do I plant tomatoes in a garden?", "B": "What's the best way to plant tomatoes in a garden bed?", "D": "How do I plant potatoes in a garden?"},
        "17": {"A": "Explain the theory of relativity.", "B": "What did Einstein mean by relativity?", "D": "Explain the theory of evolution."},
        "18": {"A": "How do I configure Nginx as a reverse proxy?", "B": "What is the Nginx config to forward requests to a backend?", "D": "How do I configure Apache as a web server?"},
        "19": {"A": "What is the plot of The Great Gatsby?", "B": "Can you summarize the story of The Great Gatsby?", "D": "What is the plot of To Kill a Mockingbird?"},
        "20": {"A": "How do I resolve a git merge conflict?", "B": "What steps do I take when git says I have conflicting files?", "D": "How do I undo a git commit?"}
    }
    
    print(f"\n[Seeding] Storing {len(clusters)} 'A' memories...")
    for cid, prompts in clusters.items():
        hippo.store_semantic(prompts["A"], {"cluster": cid, "type": "A"})
        
    print(f"Total memories stored: {len(hippo.embeddings)}")
    
    results = {"true_positive": {"pass": 0, "fail": 0}, "hard_negative": {"pass": 0, "fail": 0}}
    failed_tp = []
    
    for cid, prompts in clusters.items():
        print(f"\n--- Testing Cluster {cid} ---", flush=True)
        
        # Test True Positive (B)
        query_b = prompts["B"]
        try:
            hippo.query_verified(query_b, task_id=int(cid)*10 + 1)
            
            import time
            while not hippo._verify_queue.empty() or hippo._in_flight_verifications:
                time.sleep(0.5)
                
            verified_cands_b = hippo.query_verified(query_b, task_id=int(cid)*10 + 1)
            passed = any(v.raw_memory.get("cluster") == cid for v in verified_cands_b)
            if passed: 
                results["true_positive"]["pass"] += 1
            else: 
                results["true_positive"]["fail"] += 1
                failed_tp.append((prompts["A"], query_b))
                print(f"[FAIL] True Positive missed: '{query_b}' != '{prompts['A']}'")
        except Exception as e:
            results["true_positive"]["fail"] += 1
            failed_tp.append((prompts["A"], query_b))
            print(f"[FAIL] True Positive exception: {e}")
            
        # Test Hard Negative (D)
        query_d = prompts["D"]
        try:
            hippo.query_verified(query_d, task_id=int(cid)*10 + 2)
            
            import time
            while not hippo._verify_queue.empty() or hippo._in_flight_verifications:
                time.sleep(0.5)
                
            verified_cands_d = hippo.query_verified(query_d, task_id=int(cid)*10 + 2)
            passed = not any(v.raw_memory.get("cluster") == cid for v in verified_cands_d)
            if passed: 
                results["hard_negative"]["pass"] += 1
            else: 
                results["hard_negative"]["fail"] += 1
                print(f"[FAIL] Hard Negative missed (False Positive)! '{query_d}' incorrectly matched with '{prompts['A']}'", flush=True)
        except Exception as e:
            results["hard_negative"]["fail"] += 1
            print(f"[FAIL] Hard Negative exception: {e}", flush=True)
            
    print("\n=== Final Results ===")
    print(f"True Positives:  Pass={results['true_positive']['pass']}, Fail={results['true_positive']['fail']}")
    print(f"Hard Negatives:  Pass={results['hard_negative']['pass']}, Fail={results['hard_negative']['fail']}")
    
    output_path = os.path.join(os.path.dirname(__file__), "results", "verifier_20.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
        
    try:
        res.shutdown()
    except Exception:
        pass

if __name__ == "__main__":
    test_verified_retrieval_full()
