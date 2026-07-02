from typing import Callable, Any

class Labour:
    """
    A scheduler-level primitive.
    A short-lived execution unit for processing a single chunk of work.
    Alpha spawns these for oversized payloads.
    """
    def __init__(self, chunk_id: int):
        self.chunk_id = chunk_id

    def run(self, chunk: Any, process_func: Callable[[Any], Any]) -> dict:
        """
        Process a single chunk using the provided stateless function.
        Output contract: {"chunk_id": int, "status": "done"|"error", "result": Any}
        """
        try:
            result = process_func(chunk)
            return {"chunk_id": self.chunk_id, "status": "done", "result": result}
        except Exception as e:
            return {"chunk_id": self.chunk_id, "status": "error", "error": str(e)}
