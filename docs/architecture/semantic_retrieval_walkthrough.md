# Phase E Audit: Semantic Retrieval Calibration

This document covers the empirical testing and verification of Phase E's semantic retrieval accuracy within the Hippocampus. We explicitly focused on whether the `0.5` similarity threshold was properly calibrated to admit true near-duplicates (Recall) while suppressing same-topic-different-intent queries and lexical overlaps (Precision).

## Methodology
We seeded the Hippocampus with 5 "A" prompts acting as baseline semantic memories. We then queried it with three variants per cluster:
- **B (Near Duplicate)**: Same intent, different phrasing. (Should score > 0.5)
- **C (Same-Topic / Diff-Intent)**: e.g., debugging vs architecture. (Should score < 0.5)
- **D (Lexical Overlap / Hard Negative)**: e.g., "Translate to French" vs "Translate to Spanish". (Should score < 0.5)

## Results

> [!WARNING]
> The audit exposes a severe limitation in the embedding model's ability to distinguish intent when surface lexical overlap is high. The True Positive scores and Hard Negative scores completely overlap, making the `0.5` threshold impossible to simply "tune."

| Cluster | Type | Query (Truncated) | Target A Score | Rank |
| :--- | :--- | :--- | :--- | :--- |
| **1 (PyTorch)** | B | My PyTorch model is running out of GPU memory duri... | 0.670 | 1 |
| 1 | C | Explain the architecture of a PyTorch Transformer ... | 0.312 | 1 |
| 1 | D | How do I convert a PyTorch tensor to a NumPy array... | **0.513** | 1 |
| **2 (Scraping)** | B | How can I use BeautifulSoup in Python to extract d... | 0.575 | 1 |
| 2 | C | How do I build a REST API in Python using FastAPI?... | 0.291 | 1 |
| 2 | D | Write a Python script to calculate the Fibonacci s... | 0.180 | 1 |
| **3 (Translation)** | B | Can you convert the following English sentence to ... | 0.718 | 1 |
| 3 | C | What is the history of the French language?... | 0.393 | 1 |
| 3 | D | Translate this text into Spanish.... | **0.747** | 1 |
| **4 (React)**| B | How do I build a custom select component in React?... | 0.713 | 1 |
| 4 | C | What are the performance differences between React... | 0.240 | 1 |
| 4 | D | Create a React component for a date picker.... | **0.545** | 1 |
| **5 (Creative)**| B | Compose a haiku about a rainy day.... | 0.719 | 1 |
| 5 | C | What is the average annual rainfall in the Amazon ... | 0.329 | 1 |
| 5 | D | Write a short poem about the sun.... | **0.668** | 1 |

### Summary Averages
- **B (Near Duplicates):** 0.679
- **C (Same-Topic, Diff-Intent):** 0.313
- **D (Lexical Overlap Hard Negative):** 0.531

## Analysis & Conclusion

**1. The `0.5` threshold correctly separates B and C prompts.**
The embedding model successfully distinguishes between debugging an OOM error (1A) and explaining transformer architecture (1C). All B prompts scored above 0.5, and all C prompts scored comfortably below 0.5.

**2. The embedding model is severely vulnerable to Lexical Overlaps (D prompts).**
When prompts share heavy surface vocabulary but diverge on a critical semantic detail (e.g., "dropdown menu" vs "date picker", "rain" vs "sun", "French" vs "Spanish"), the model fails to capture the divergence. 
- Prompt 3D ("Spanish") scored **0.747** against 3A ("French"), which is *higher* than the True Positive 3B ("English to French" at 0.718).
- 4 out of 5 Hard Negatives crossed the `0.5` threshold, resulting in **False Positives**.

**3. We cannot fix this by tuning the threshold.**
Even though N=15 is a small sample, the mathematical reality of the embedding space is exposed:
- If we raise the threshold to `0.7` to block 5D (`0.668`), we will incorrectly block True Positives 1B (`0.670`) and 2B (`0.575`).
- The scores for True Positives and Hard Negatives are not linearly separable by a simple cosine similarity scalar. 

**Recommendation:** Phase E is functional for basic retrieval, but it is architecturally prone to retrieving false-positive memories if the user's intent pivots slightly while using the same vocabulary. To fix this, we would need either a heavier semantic embedding model, or a two-stage retrieval pipeline (e.g., retrieve top 5 via embeddings, then use an LLM cell to explicitly verify relevance before application).
