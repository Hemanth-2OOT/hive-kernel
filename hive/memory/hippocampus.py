import os
import json
import numpy as np
from typing import List, Optional
from hive.memory.verifier import SemanticVerifier, MemoryCandidate, VerifiedMemory, VerificationError
from hive.config import HiveConfig
import hashlib

class Hippocampus:
    def __init__(self, reservoir, verifier: Optional[SemanticVerifier] = None, config: HiveConfig = None):
        self.reservoir = reservoir
        self.config = config or HiveConfig()
        self._verifier = verifier
        self.data_dir = "data"
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.episodic_path = os.path.join(self.data_dir, "episodic.jsonl")
        self.semantic_vecs_path = os.path.join(self.data_dir, "semantic.npy")
        self.semantic_meta_path = os.path.join(self.data_dir, "semantic_meta.json")
        
        self.embeddings = []
        self.metadata = []
        
        self._load_semantic()

    def _load_semantic(self):
        if os.path.exists(self.semantic_vecs_path) and os.path.exists(self.semantic_meta_path):
            self.embeddings = list(np.load(self.semantic_vecs_path))
            with open(self.semantic_meta_path, "r") as f:
                self.metadata = json.load(f)

    def _save_semantic(self):
        if self.embeddings:
            np.save(self.semantic_vecs_path, np.array(self.embeddings))
            with open(self.semantic_meta_path, "w") as f:
                json.dump(self.metadata, f, indent=2)

    def append_episode(self, trace: dict):
        with open(self.episodic_path, "a") as f:
            f.write(json.dumps(trace) + "\n")

    def store_semantic(self, text: str, metadata: dict):
        """Internal embedding call, keeping vectorization abstract from Nucleus."""
        metadata["_decay_factor"] = 1.0
        metadata["_memory_id"] = metadata.get("_memory_id", hashlib.md5(text.encode()).hexdigest()[:8])
        metadata["_content"] = text
        resp = self.reservoir.infer("embedding", 0, text)
        if resp["status"] == "error":
            print(f"[HIPPOCAMPUS] Embedding failed for storage: {resp.get('error')}")
            return
            
        vector = resp["result"]["vector"]
        
        self.embeddings.append(vector)
        self.metadata.append(metadata)
        self._save_semantic()

    def recall_from_text(self, text: str, top_k: int = None, task_id: int = 0):
        if top_k is None:
            top_k = self.config.top_k_recall
            
        if not self.embeddings:
            return []
            
        resp = self.reservoir.infer("embedding", 0, text)
        if resp["status"] == "error":
            print(f"[HIPPOCAMPUS] Embedding failed for recall: {resp.get('error')}")
            return []
            
        query_vec = np.array(resp["result"]["vector"])
        if not hasattr(self, '_query_vectors_by_task'):
            self._query_vectors_by_task = {}
        self._query_vectors_by_task[task_id] = query_vec
        
        embs = np.array(self.embeddings)
        dot_prods = np.dot(embs, query_vec)
        norms = np.linalg.norm(embs, axis=1) * np.linalg.norm(query_vec)
        norms = np.where(norms == 0, 1e-10, norms)
        # Apply weighted decay
        decay_factors = np.array([m.get("_decay_factor", 1.0) for m in self.metadata])
        similarities = (dot_prods / norms) * decay_factors
        
        # Sort and take top_k
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            # Threshold to prevent completely unrelated matches from returning
            if similarities[idx] > self.config.similarity_threshold:
                results.append({
                    "score": float(similarities[idx]),
                    "memory": self.metadata[idx]
                })
            
        return results

    def query(self, query_text: str, task_id: Optional[int] = 0) -> List[MemoryCandidate]:
        results = self.recall_from_text(query_text, top_k=self.config.top_k_recall + 2, task_id=task_id)
        candidates = []
        for r in results:
            candidates.append(MemoryCandidate(
                memory_id=r["memory"].get("_memory_id", ""),
                content=r["memory"].get("_content", ""),
                embedding_score=r["score"],
                raw_memory=r["memory"]
            ))
        return candidates

    def query_verified(self, query_text: str, task_id: Optional[int] = 0) -> List[VerifiedMemory]:
        candidates = self.query(query_text, task_id=task_id)
        if self._verifier is None:
            return []

        if not hasattr(self, '_verified_memory_ids_by_task'):
            self._verified_memory_ids_by_task = {}

        try:
            verified = self._verifier.verify(query_text, candidates, task_id=task_id)
            self._verified_memory_ids_by_task[task_id] = {v.memory_id for v in verified}
            return verified
        except VerificationError as e:
            print(f"[HIPPOCAMPUS] Verification failed, failing closed: {e}")
            self._verified_memory_ids_by_task[task_id] = set()
            return []

    def penalize_memory(self, text: str, penalty: float = 0.5, task_id: int = 0):
        if not self.embeddings: return
        
        # Only penalize memories that were actually verified and used, not rejected ones!
        # Use task_id as the cycle stamp to prevent cross-cycle staleness and pop to prevent memory leak
        allowed_ids_map = getattr(self, '_verified_memory_ids_by_task', {})
        allowed_ids = allowed_ids_map.pop(task_id, set())
        
        if not allowed_ids:
            print("[HIPPOCAMPUS] Apoptosis skipped: No verified memories were applied this cycle.")
            return

        # Use cached vector if available to avoid fatal OOM loops during apoptosis, popping to prevent leak
        query_vectors_map = getattr(self, '_query_vectors_by_task', {})
        if task_id in query_vectors_map:
            query_vec = query_vectors_map.pop(task_id)
        else:
            try:
                resp = self.reservoir.infer("embedding", 0, text)
                if resp["status"] == "error": return
                query_vec = np.array(resp["result"]["vector"])
            except Exception as e:
                print(f"[HIPPOCAMPUS] Apoptosis embedding failed due to system strain: {e}")
                return
                
        embs = np.array(self.embeddings)
        dot_prods = np.dot(embs, query_vec)
        norms = np.linalg.norm(embs, axis=1) * np.linalg.norm(query_vec)
        norms = np.where(norms == 0, 1e-10, norms)
        similarities = dot_prods / norms
        
        if len(similarities) > 0:
            top_idx = np.argmax(similarities)
            mem_id = self.metadata[top_idx].get("_memory_id", "")
            
            if similarities[top_idx] > 0.7 and mem_id in allowed_ids:
                old_val = self.metadata[top_idx].get("_decay_factor", 1.0)
                self.metadata[top_idx]["_decay_factor"] = old_val * penalty
                print(f"[HIPPOCAMPUS] Penalized memory {top_idx}. New decay factor: {self.metadata[top_idx]['_decay_factor']:.2f}")
                self._save_semantic()
            elif similarities[top_idx] > 0.7:
                print(f"[HIPPOCAMPUS] Apoptosis skipped: Top memory {top_idx} was not among the verified memories.")

    def clear_cycle(self, task_id: int = 0):
        """Guaranteed cleanup to prevent memory leaks on successful paths."""
        if hasattr(self, '_verified_memory_ids_by_task'):
            self._verified_memory_ids_by_task.pop(task_id, None)
        if hasattr(self, '_query_vectors_by_task'):
            self._query_vectors_by_task.pop(task_id, None)
