import os
import shutil
import numpy as np
from reservoir import Reservoir
from hippocampus import Hippocampus

def test_semantic_retrieval():
    print("=== Phase E Audit: Semantic Retrieval Calibration ===")
    
    # 1. Clean slate
    if os.path.exists("data"):
        shutil.rmtree("data")
        
    res = Reservoir(max_ram_mb=4000, idle_ttl_sec=300)
    hippo = Hippocampus(res)
    
    # Define Clusters
    clusters = {
        "1": {
            "A": "How do I fix a CUDA OutOfMemoryError in PyTorch?",
            "B": "My PyTorch model is running out of GPU memory during training, what can I do?",
            "C": "Explain the architecture of a PyTorch Transformer model.",
            "D": "How do I convert a PyTorch tensor to a NumPy array?"
        },
        "2": {
            "A": "Write a Python script to scrape product prices from an e-commerce website.",
            "B": "How can I use BeautifulSoup in Python to extract data from a webpage?",
            "C": "How do I build a REST API in Python using FastAPI?",
            "D": "Write a Python script to calculate the Fibonacci sequence."
        },
        "3": {
            "A": "Translate this text into French.",
            "B": "Can you convert the following English sentence to French?",
            "C": "What is the history of the French language?",
            "D": "Translate this text into Spanish."
        },
        "4": {
            "A": "Create a React component for a dropdown menu.",
            "B": "How do I build a custom select component in React?",
            "C": "What are the performance differences between React and Vue?",
            "D": "Create a React component for a date picker."
        },
        "5": {
            "A": "Write a short poem about the rain.",
            "B": "Compose a haiku about a rainy day.",
            "C": "What is the average annual rainfall in the Amazon rainforest?",
            "D": "Write a short poem about the sun."
        }
    }
    
    print("\n[PHASE 1] Seeding Hippocampus with A-prompts...")
    for c_id, prompts in clusters.items():
        hippo.store_semantic(prompts["A"], {"cluster": c_id, "type": "A", "text": prompts["A"]})
        
    print(f"Stored {len(hippo.embeddings)} base memories.")
    
    print("\n[PHASE 2] Querying and Measuring...")
    
    results_table = []
    
    # Helper to get embedding vector
    def get_embedding(text):
        resp = res.infer("embedding", 0, text)
        return np.array(resp["result"]["vector"])
        
    base_embs = np.array(hippo.embeddings)
    
    for c_id, prompts in clusters.items():
        for query_type in ["B", "C", "D"]:
            query_text = prompts[query_type]
            query_vec = get_embedding(query_text)
            
            # Compute cosine similarities manually to bypass the 0.5 filter
            dot_prods = np.dot(base_embs, query_vec)
            norms = np.linalg.norm(base_embs, axis=1) * np.linalg.norm(query_vec)
            norms = np.where(norms == 0, 1e-10, norms)
            similarities = dot_prods / norms
            
            # Find the rank of the target cluster A-prompt
            # The A-prompts were inserted in order: 1, 2, 3, 4, 5
            # So index corresponding to c_id is int(c_id) - 1
            target_idx = int(c_id) - 1
            target_score = float(similarities[target_idx])
            
            # Find rank by sorting
            sorted_indices = np.argsort(similarities)[::-1]
            rank = list(sorted_indices).index(target_idx) + 1
            
            # Also find the absolute best match (Top 1)
            top1_idx = sorted_indices[0]
            top1_score = similarities[top1_idx]
            top1_cluster = hippo.metadata[top1_idx]["cluster"]
            
            # Cross-retrieval check: if Top 1 is NOT the target cluster, we note it.
            cross_retrieval = f"No"
            if top1_cluster != c_id:
                cross_retrieval = f"Yes (Cluster {top1_cluster} @ {top1_score:.2f})"
                
            results_table.append({
                "Cluster": c_id,
                "Query Type": query_type,
                "Query Text": query_text,
                "Target A Score": target_score,
                "Target Rank": rank,
                "Cross-Retrieval?": cross_retrieval
            })
            
    print("\n=== RESULTS TABLE ===")
    print(f"{'Cluster':<8} | {'Type':<5} | {'Target Score':<12} | {'Rank':<5} | {'Cross-Retrieval?':<25} | {'Query'}")
    print("-" * 120)
    for r in results_table:
        score_str = f"{r['Target A Score']:.3f}"
        print(f"{r['Cluster']:<8} | {r['Query Type']:<5} | {score_str:<12} | {r['Target Rank']:<5} | {r['Cross-Retrieval?']:<25} | {r['Query Text'][:50]}...")
        
    print("\n=== CALIBRATION SUMMARY ===")
    b_scores = [r["Target A Score"] for r in results_table if r["Query Type"] == "B"]
    c_scores = [r["Target A Score"] for r in results_table if r["Query Type"] == "C"]
    d_scores = [r["Target A Score"] for r in results_table if r["Query Type"] == "D"]
    
    print(f"Average B Score (Near Duplicates): {sum(b_scores)/len(b_scores):.3f}")
    print(f"Average C Score (Same-Topic, Diff-Intent): {sum(c_scores)/len(c_scores):.3f}")
    print(f"Average D Score (Lexical Overlap Hard Negative): {sum(d_scores)/len(d_scores):.3f}")
    
    res.shutdown()
    
    # Save the table for the walkthrough
    import pandas as pd
    df = pd.DataFrame(results_table)
    df.to_csv("phase_e_results.csv", index=False)
    print("\nResults saved to phase_e_results.csv")

if __name__ == "__main__":
    test_semantic_retrieval()
