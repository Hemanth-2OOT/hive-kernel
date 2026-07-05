from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class HiveConfig:
    max_vram_mb: int = 6144
    idle_ttl_sec: int = 300
    # Ollama's internal keep_alive per request. Must be > idle_ttl_sec so Ollama never
    # evicts a model Hive still considers warm, causing unnecessary cold-start reloads.
    # TRADEOFF: 360s bounds worst-case orphaned VRAM to 6 minutes (hard-kill path where
    # the explicit keep_alive:0 unload cannot run) in exchange for avoiding reload
    # thrashing on inter-call gaps under 5 minutes (idle_ttl_sec). Reducing this value
    # tightens VRAM reclamation but risks cold-start penalties on slower DAG paths.
    ollama_keep_alive_sec: int = 360   # idle_ttl_sec (300) + 60s headroom
    exploration_rate: float = 0.1
    similarity_threshold: float = 0.5
    top_k_recall: int = 3
    
    cell_profiles: Dict[str, int] = field(default_factory=lambda: {
        "sentiment": 550,
        "embedding": 400,
        "hermes3:8b": 5300,
        "qwen2.5-coder:7b": 4900
    })
    
    cell_priorities: Dict[str, int] = field(default_factory=lambda: {
        "embedding": 3,
        "sentiment": 2,
        "hermes3:8b": 1,
        "qwen2.5-coder:7b": 1
    })
    
    cell_lock_order: List[str] = field(default_factory=lambda: [
        "embedding", "hermes3:8b", "qwen2.5-coder:7b", "sentiment"
    ])
    
    task_to_cell: Dict[str, str] = field(default_factory=lambda: {
        "generate": "qwen2.5-coder:7b",
        "summarize": "hermes3:8b",
        "classify": "sentiment",
        "sentiment": "sentiment",
        "embed": "embedding",
        "llm_verify": "hermes3:8b"
    })
