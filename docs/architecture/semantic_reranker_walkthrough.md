# Phase E Structural Fix: Two-Stage Semantic Retrieval Pipeline

This document details the implementation of the structural fix for the Phase E semantic retrieval calibration flaw. 

## The Flaw
The `0.5` cosine similarity threshold failed drastically on Lexical Overlap Hard Negatives (e.g. queries sharing heavily overlapping vocabulary but differing on intent).

## The Fix: `SemanticVerifier`
Instead of tuning the impossible scalar threshold, we implemented a **Two-Stage Retrieval Pipeline**:
1. **Stage 1 (Fast)**: Retrieve the top K candidates using the existing embedding similarity.
2. **Stage 2 (Strict)**: Pass those candidates to a dedicated `SemanticVerifier` which wraps an LLM Hard Cell to explicitly verify semantic relevance.

### Design Principles:
- **Separation of Concerns**: The `SemanticVerifier` is a standalone class, making it independently testable and swappable.
- **Fail Closed**: If the LLM cell crashes or returns malformed output, the verifier fails gracefully by returning zero candidates (`VerificationError`), rather than blindly trusting the flawed Stage-1 embeddings. This prevents bad mutations from crashing the DAG.
- **Invariant Preserved**: The `SemanticVerifier` interacts with the LLM cell strictly via `reservoir.infer()`, flawlessly preserving the atomic `write`/`read` lock invariant established in Phase G1.

## Validation
We ran a dedicated test (`test_e_verified.py`) specifically targeting the sharpest known failure: the Cluster 3 Translation hard negative.
- **Query**: "Translate this text into Spanish."
- **Seeded Memory**: "Translate this text into French."
- **Stage 1 Result**: Rank 1 match, Score: `0.747` (False Positive).
- **Stage 1 + Stage 2 Result**: The `SemanticVerifier` intercepted the candidate, correctly identified the lexical overlap false positive, and rejected it. `Verified Results count: 0`.

The pipeline is now active and integrated into `PolicyValidator.validate_and_mutate()`, ensuring only strictly verified semantic precedents can trigger DAG mutations.
