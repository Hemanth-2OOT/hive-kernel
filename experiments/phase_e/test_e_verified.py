import os
import shutil
from reservoir import Reservoir
from hippocampus import Hippocampus
from verifier import SemanticVerifier

def test_verified_retrieval_full():
    print("=== Phase E: Comprehensive Stage 2 Verification Test ===")
    
    if os.path.exists("data"):
        shutil.rmtree("data")
        
    res = Reservoir(max_ram_mb=4000, idle_ttl_sec=300)
    verifier = SemanticVerifier(res, cell_name="llm")
    hippo = Hippocampus(res, verifier=verifier)
    
    clusters = {
        "1": {
            "A": "How do I fix a CUDA OutOfMemoryError in PyTorch?",
            "B": "My PyTorch model is running out of GPU memory during training, what can I do?",
            "D": "How do I convert a PyTorch tensor to a NumPy array?"
        },
        "3": {
            "A": "Translate this text into French.",
            "B": "Can you convert the following English sentence to French?",
            "D": "Translate this text into Spanish."
        },
        "4": {
            "A": "Create a React component for a dropdown menu.",
            "B": "How do I build a custom select component in React?",
            "D": "Create a React component for a date picker."
        },
        "5": {
            "A": "Write a short poem about the rain.",
            "B": "Compose a haiku about a rainy day.",
            "D": "Write a short poem about the sun."
        }
    }
    
    print("\n[Seeding] Storing all 'A' memories to test batching behavior...")
    for cid, prompts in clusters.items():
        hippo.store_semantic(prompts["A"], {"cluster": cid, "type": "A"})
        
    print(f"Total memories stored: {len(hippo.embeddings)}")
    
    for cid, prompts in clusters.items():
        print(f"\n--- Testing Cluster {cid} ---")
        
        # Test True Positive (B)
        query_b = prompts["B"]
        print(f"\n[TRUE POSITIVE] Query: '{query_b}'")
        try:
            # Task ID increases so we can track in logs if needed
            verified_cands_b = hippo.query_verified(query_b, task_id=int(cid)*10 + 1)
            
            # Find if the target cluster A was verified as relevant
            passed = any(v.raw_memory.get("cluster") == cid for v in verified_cands_b)
            print(f"Verified count: {len(verified_cands_b)}")
            print(f"Target A accepted? {'YES (Pass)' if passed else 'NO (FAIL)'}")
            for v in verified_cands_b:
                print(f"  -> Accepted: [Cluster {v.raw_memory.get('cluster')}] {v.content}")
        except Exception as e:
            print(f"Failed True Positive test: {e}")
            
        # Test Hard Negative (D)
        query_d = prompts["D"]
        print(f"\n[HARD NEGATIVE] Query: '{query_d}'")
        try:
            verified_cands_d = hippo.query_verified(query_d, task_id=int(cid)*10 + 2)
            
            # Find if the target cluster A was verified as relevant (it SHOULD NOT BE)
            passed = any(v.raw_memory.get("cluster") == cid for v in verified_cands_d)
            print(f"Verified count: {len(verified_cands_d)}")
            print(f"Target A accepted? {'YES (FAIL)' if passed else 'NO (Pass)'}")
            for v in verified_cands_d:
                print(f"  -> Accepted: [Cluster {v.raw_memory.get('cluster')}] {v.content}")
        except Exception as e:
            print(f"Failed Hard Negative test: {e}")
            
    res.shutdown()

if __name__ == "__main__":
    test_verified_retrieval_full()
