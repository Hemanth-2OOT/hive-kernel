import gc
import os
import psutil
from typing import Any, List
from worker import Worker

def get_memory_mb():
    """Helper to track memory footprint of the current process."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)

class SentimentCell(Worker):
    """
    First real AI cell for Hive.
    Loads a tiny sentiment model (distilbert), predicts, and explicitly cleans up.
    """
    def __init__(self, worker_id: str):
        super().__init__(worker_id)
        # 1. Ephemeral State
        # We don't load the model in __init__. We only hold a placeholder
        # so it only consumes RAM when the cell is explicitly RUNNING.
        self.model_pipeline = None

    def run(self, task: dict) -> dict:
        try:
            payload = task["payload"]
            
            # Record RAM before load
            print(f"  [Memory] SentimentCell created (Before model load): {get_memory_mb():.2f} MB")
            
            # 2. Local Model Loading
            # Using HuggingFace pipeline for Phase 1 simplicity as requested.
            # (In Phase 2, this could be ONNX Runtime directly for even less overhead)
            from transformers import pipeline
            self.model_pipeline = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
            
            # Record RAM after load
            print(f"  [Memory] SentimentCell loaded model (Peak RAM): {get_memory_mb():.2f} MB")
            
            # 3. Execution
            result = self.model_pipeline(payload)
            # pipeline returns [{'label': 'POSITIVE', 'score': 0.999}]
            
            # 4. Structured Output
            structured_result = {
                "label": result[0]["label"],
                "confidence": round(result[0]["score"], 4)
            }
            
            return {"task_id": task["task_id"], "status": "done", "result": structured_result}
            
        except Exception as e:
            return {"task_id": task["task_id"], "status": "error", "error": str(e)}

    def cleanup(self) -> None:
        """
        Explicitly removes the model from memory.
        Called by Alpha's Garbage Collector.
        """
        # Delete the pipeline reference
        del self.model_pipeline
        self.model_pipeline = None
        
        # Force Python's Garbage Collector to reclaim the orphaned model weights
        gc.collect()
        
        print(f"  [Memory] SentimentCell destroyed (After cleanup): {get_memory_mb():.2f} MB")

    def chunk_payload(self, payload: Any) -> List[Any]:
        # For simplicity in Phase 1, we don't chunk sentiment.
        # It takes the full text paragraph directly.
        return [payload]

    def process_chunk(self, chunk: Any) -> Any:
        pass

    def aggregate_results(self, results: List[Any]) -> Any:
        pass
