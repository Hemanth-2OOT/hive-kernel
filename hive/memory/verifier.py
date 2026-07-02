"""
Phase E Fix: Two-Stage Semantic Retrieval Pipeline.

Stage 1 (existing): Hippocampus.recall_from_text() returns top-K candidates by
cosine similarity. This stage is known to admit lexical-overlap
hard negatives at rank #1 (see Phase E audit, 3D scoring 0.747 vs
true-positive 3B at 0.718).

Stage 2 (this module): Each Stage-1 candidate is passed to an LLM
Hard Cell for an explicit relevance verification before
PolicyValidator is allowed to use it for DAG mutation.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import json
import re


@dataclass
class MemoryCandidate:
    memory_id: str
    content: str
    embedding_score: float
    raw_memory: dict


@dataclass
class VerifiedMemory:
    memory_id: str
    content: str
    embedding_score: float
    verified_relevant: bool
    verifier_confidence: float
    verifier_reason: str
    raw_memory: dict


class VerificationError(Exception):
    """Raised when the LLM cell fails or returns malformed output.
    Callers MUST treat this as 'no verified memories available',
    never as 'fall back to raw embedding scores'."""
    pass


class SemanticVerifier:
    """
    Wraps an LLM Hard Cell to re-rank/filter Stage-1 embedding
    candidates before they reach PolicyValidator.

    Fails closed: any cell error or parse failure returns zero
    verified candidates rather than silently trusting Stage 1.
    """

    VERIFY_PROMPT_TEMPLATE = """Task: Determine if the candidate memory is EXACTLY the same underlying task/intent as the QUERY.
Lexical overlap (e.g. translating to different languages) means NO.

QUERY: {query}
CANDIDATE: {candidate_content}

Output EXACTLY one word: YES or NO.
OUTPUT:"""

    def __init__(self, reservoir, cell_name: str = "llm"):
        self._reservoir = reservoir
        self._cell_name = cell_name

    def verify(self, query: str, candidates: List[MemoryCandidate],
               task_id: Optional[int] = 0) -> List[VerifiedMemory]:
        """
        Send candidates to the LLM cell one by one.
        (A 0.5B model degrades on batch lists, so we iterate K times).
        """
        if not candidates:
            return []

        verified: List[VerifiedMemory] = []

        for c in candidates:
            prompt = self.VERIFY_PROMPT_TEMPLATE.format(
                query=query, candidate_content=c.content
            )

            try:
                raw_response = self._reservoir.infer(
                    cell_type=self._cell_name,
                    task_id=task_id,
                    payload=prompt
                )
                
                if raw_response.get("status") == "error":
                    raise VerificationError(f"LLM cell returned error status: {raw_response.get('error')}")
                    
                text_resp = raw_response["result"]["text"].strip().upper()
                
                # Match YES or NO in the response
                is_yes = "YES" in text_resp
                is_no = "NO" in text_resp
                
                if is_yes and not is_no:
                    relevant = True
                elif is_no and not is_yes:
                    relevant = False
                else:
                    # Ambiguous or malformed
                    relevant = False
                    
                if relevant:
                    verified.append(VerifiedMemory(
                        memory_id=c.memory_id,
                        content=c.content,
                        embedding_score=c.embedding_score,
                        verified_relevant=True,
                        verifier_confidence=1.0,
                        verifier_reason="Extracted YES",
                        raw_memory=c.raw_memory
                    ))
                    
            except Exception as e:
                # If a single candidate verification fails, fail the whole batch closed
                raise VerificationError(f"LLM cell failed or returned malformed output during verification: {e}") from e

        return verified
