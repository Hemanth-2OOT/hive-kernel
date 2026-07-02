from typing import Any, List
from worker import Worker

class WordCounter(Worker):
    """
    Counts words in a text payload.
    """
    def run(self, task: dict) -> dict:
        try:
            payload = task["payload"]
            count = len(payload.split())
            return {"task_id": task["task_id"], "status": "done", "result": count}
        except Exception as e:
            return {"task_id": task["task_id"], "status": "error", "error": str(e)}

    def chunk_payload(self, payload: str) -> List[List[str]]:
        words = payload.split()
        # Chunking by 50 words
        return [words[i:i+50] for i in range(0, len(words), 50)]

    def process_chunk(self, chunk: List[str]) -> int:
        return len(chunk)

    def aggregate_results(self, results: List[int]) -> int:
        return sum(results)
