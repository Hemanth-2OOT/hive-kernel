import re
from typing import Any, List
from worker import Worker

class DateDetector(Worker):
    """
    Extracts dates (e.g. YYYY-MM-DD or MM/DD/YYYY) from a text payload.
    """
    def run(self, task: dict) -> dict:
        try:
            payload = task["payload"]
            dates = re.findall(r'\b\d{2,4}[-/]\d{2}[-/]\d{2,4}\b', payload)
            return {"task_id": task["task_id"], "status": "done", "result": dates}
        except Exception as e:
            return {"task_id": task["task_id"], "status": "error", "error": str(e)}

    def chunk_payload(self, payload: str) -> List[List[str]]:
        words = payload.split()
        return [words[i:i+50] for i in range(0, len(words), 50)]

    def process_chunk(self, chunk: List[str]) -> List[str]:
        text = " ".join(chunk)
        return re.findall(r'\b\d{2,4}[-/]\d{2}[-/]\d{2,4}\b', text)

    def aggregate_results(self, results: List[List[str]]) -> List[str]:
        return [date for sublist in results for date in sublist]
