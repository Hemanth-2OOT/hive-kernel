import re
from typing import Any, List
from worker import Worker

class UrlExtractor(Worker):
    """
    Extracts URLs from a text payload.
    """
    def run(self, task: dict) -> dict:
        try:
            payload = task["payload"]
            urls = re.findall(r'https?://[^\s]+', payload)
            return {"task_id": task["task_id"], "status": "done", "result": urls}
        except Exception as e:
            return {"task_id": task["task_id"], "status": "error", "error": str(e)}

    def chunk_payload(self, payload: str) -> List[List[str]]:
        words = payload.split()
        return [words[i:i+50] for i in range(0, len(words), 50)]

    def process_chunk(self, chunk: List[str]) -> List[str]:
        text = " ".join(chunk)
        return re.findall(r'https?://[^\s]+', text)

    def aggregate_results(self, results: List[List[str]]) -> List[str]:
        return [url for sublist in results for url in sublist]
