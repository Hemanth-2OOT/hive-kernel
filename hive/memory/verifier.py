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
import os
import hashlib
import threading
from hive.config import HiveConfig

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
    # TRIPWIRE: This field holds raw, opaque text directly from the LLM. 
    # It must NEVER be executed, eval'd, JSON-parsed, or rendered directly in an untrusted UI without sanitization.
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

    MAX_CACHE_ENTRIES = 1000

    VERIFY_PROMPT_TEMPLATE = """Task: Compare the underlying intent and specific parameters/entities between the QUERY and the CANDIDATE.

Before judging semantic equivalence, first extract the primary subject/data-structure/entity each query operates on (e.g. "string", "linked list", "array", "salary", "employee record").

Two queries are equivalent ONLY IF:
1. The primary subject/entity matches exactly or is a clear synonym, AND
2. The action/intent matches.

If the subject/entity differs (e.g. "string" vs "linked list", "lowest" vs "second highest" as distinct target values), the queries are NOT equivalent, even if the surrounding task structure or phrasing is very similar. Similarity of approach or algorithm is not sufficient for equivalence — the operated-on object and the specific target must both match.

When entities differ in name, ask: do they refer to the same underlying mechanism or class of thing (e.g. "tarball" and "backup" — a tarball IS a backup mechanism, or "reverse proxy" and "forward requests" — forwarding requests IS the function of a reverse proxy), or are they genuinely different sub-types/targets within the same category (e.g. "haiku" IS A poem, but a different specific kind — treat sub-types and distinct targets as non-equivalent)? Only merge in the former case.

Respond with your reasoning: first state the extracted subject/entity for each query, then state the extracted action, then give your final equivalence judgment on a new line exactly as "FINAL_JUDGMENT: YES" or "FINAL_JUDGMENT: NO".

QUERY: {query}
CANDIDATE: {candidate_content}

OUTPUT:"""

    def __init__(self, reservoir, cell_name: str = "hermes3:8b", config: HiveConfig = None):
        self._reservoir = reservoir
        self._cell_name = cell_name
        self.config = config or HiveConfig()
        
        self._io_lock = threading.Lock()
        self._judgment_cache: Dict[str, dict] = {}
        
        data_dir = self.config.data_dir if hasattr(self.config, 'data_dir') else "data"
        os.makedirs(data_dir, exist_ok=True)
        self._cache_file = os.path.join(data_dir, "verifier_cache.json")
        self._prompt_hash = hashlib.md5(self.VERIFY_PROMPT_TEMPLATE.encode()).hexdigest()
        
        self._load_cache()

    def _load_cache(self):
        with self._io_lock:
            if os.path.exists(self._cache_file):
                try:
                    with open(self._cache_file, "r") as f:
                        self._judgment_cache = json.load(f)
                except Exception as e:
                    print(f"[VERIFIER] Failed to load cache: {e}")

    def _save_cache(self):
        with self._io_lock:
            cache_copy = self._judgment_cache.copy()
            
        try:
            tmp_path = self._cache_file + ".tmp"
            with open(tmp_path, "w") as f:
                json.dump(cache_copy, f, indent=2)
            os.replace(tmp_path, self._cache_file)
        except Exception as e:
            print(f"[VERIFIER] Failed to save cache: {e}")

    def get_cached_result(self, query: str, memory_id: str) -> Optional[dict]:
        """Expose cache check for Hippocampus async logic."""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        cache_key = f"{self._cell_name}_{self._prompt_hash}_{query_hash}_{memory_id}"
        with self._io_lock:
            return self._judgment_cache.get(cache_key)

    def verify(self, query: str, candidates: List[MemoryCandidate],
               task_id: Optional[int] = 0) -> List[VerifiedMemory]:
        """
        Legacy synchronous path - unused by Phase L background verifier, kept for compatibility if needed.
        """
        if not candidates:
            return []

        verified: List[VerifiedMemory] = []

        query_hash = hashlib.md5(query.encode()).hexdigest()
        dirty_cache = False

        for c in candidates:
            cache_key = f"{self._cell_name}_{self._prompt_hash}_{query_hash}_{c.memory_id}"
            
            with self._io_lock:
                cached_result = self._judgment_cache.get(cache_key)
                
            if cached_result is not None:
                print(f"[VERIFIER] Cache hit for {c.memory_id[:8]}", flush=True)
                if cached_result.get("relevant"):
                    verified.append(VerifiedMemory(
                        memory_id=c.memory_id,
                        content=c.content,
                        embedding_score=c.embedding_score,
                        verified_relevant=True,
                        verifier_confidence=1.0,
                        verifier_reason=cached_result.get("reason", "Cached hit"),
                        raw_memory=c.raw_memory
                    ))
                continue
                
            print(f"[VERIFIER] Cache miss for {c.memory_id[:8]}! Running synchronous LLM verification...", flush=True)
                
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
                    
                text_resp = raw_response["result"]["text"].strip()
                
                match = re.search(r"FINAL_JUDGMENT:\s*(YES|NO)", text_resp, re.IGNORECASE)
                if match:
                    relevant = (match.group(1).upper() == "YES")
                else:
                    relevant = False
                    
                if relevant:
                    verified.append(VerifiedMemory(
                        memory_id=c.memory_id,
                        content=c.content,
                        embedding_score=c.embedding_score,
                        verified_relevant=True,
                        verifier_confidence=1.0,
                        verifier_reason=text_resp,
                        raw_memory=c.raw_memory
                    ))
                
                with self._io_lock:
                    self._judgment_cache[cache_key] = {
                        "relevant": relevant,
                        "reason": text_resp
                    }
                    if len(self._judgment_cache) > self.MAX_CACHE_ENTRIES:
                        keys_to_remove = list(self._judgment_cache.keys())[:200]
                        for k in keys_to_remove:
                            self._judgment_cache.pop(k, None)
                dirty_cache = True
                    
            except Exception as e:
                # If a single candidate verification fails, fail the whole batch closed
                raise VerificationError(f"LLM cell failed or returned malformed output during verification: {e}") from e

        if dirty_cache:
            self._save_cache()
            

        return verified

    def verify_single(self, query: str, c: MemoryCandidate, task_id: Optional[int] = 0) -> Optional[VerifiedMemory]:
        """
        Verify a single candidate (used by the background worker).
        Does not catch VerificationError so the worker can track retries.
        """
        query_hash = hashlib.md5(query.encode()).hexdigest()
        cache_key = f"{self._cell_name}_{self._prompt_hash}_{query_hash}_{c.memory_id}"
        
        with self._io_lock:
            cached_result = self._judgment_cache.get(cache_key)
            
        if cached_result is not None:
            if cached_result.get("relevant"):
                return VerifiedMemory(
                    memory_id=c.memory_id,
                    content=c.content,
                    embedding_score=c.embedding_score,
                    verified_relevant=True,
                    verifier_confidence=1.0,
                    verifier_reason=cached_result.get("reason", "Cached hit"),
                    raw_memory=c.raw_memory
                )
            return None
            
        print(f"[VERIFIER] Background verify for {c.memory_id[:8]}...", flush=True)
            
        prompt = self.VERIFY_PROMPT_TEMPLATE.format(
            query=query, candidate_content=c.content
        )

        raw_response = self._reservoir.infer(
            cell_type=self._cell_name,
            task_id=task_id,
            payload=prompt
        )
        
        if raw_response.get("status") == "error":
            raise VerificationError(f"LLM cell returned error status: {raw_response.get('error')}")
            
        text_resp = raw_response["result"]["text"].strip()
        
        match = re.search(r"FINAL_JUDGMENT:\s*(YES|NO)", text_resp, re.IGNORECASE)
        if match:
            relevant = (match.group(1).upper() == "YES")
        else:
            relevant = False
            
        with self._io_lock:
            self._judgment_cache[cache_key] = {
                "relevant": relevant,
                "reason": text_resp
            }
            if len(self._judgment_cache) > self.MAX_CACHE_ENTRIES:
                keys_to_remove = list(self._judgment_cache.keys())[:200]
                for k in keys_to_remove:
                    self._judgment_cache.pop(k, None)
        self._save_cache()
            
        if relevant:
            return VerifiedMemory(
                memory_id=c.memory_id,
                content=c.content,
                embedding_score=c.embedding_score,
                verified_relevant=True,
                verifier_confidence=1.0,
                verifier_reason=text_resp,
                raw_memory=c.raw_memory
            )
        return None
