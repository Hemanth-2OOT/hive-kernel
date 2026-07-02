import abc
from typing import Any, List

class Worker(abc.ABC):
    """
    Stateless, single-purpose base worker.
    Holds domain logic but absolutely no resource or scheduling logic.
    """
    def __init__(self, worker_id: str):
        self.worker_id = worker_id

    @abc.abstractmethod
    def run(self, task: dict) -> dict:
        """
        Executes the task directly for small payloads.
        Output contract: {"task_id": int, "status": "done"|"error", "result": any}
        """
        pass

    @abc.abstractmethod
    def chunk_payload(self, payload: Any) -> List[Any]:
        """
        Splits the payload into logical pieces for Labour processing.
        """
        pass

    @abc.abstractmethod
    def process_chunk(self, chunk: Any) -> Any:
        """
        Processes a single chunk. This function will be given to Labours by Alpha.
        """
        pass

    @abc.abstractmethod
    def aggregate_results(self, results: List[Any]) -> Any:
        """
        Combines Labour results into a final result.
        """
        pass

    def cleanup(self) -> None:
        """
        Explicit memory reclamation hook.
        Called by Alpha before destroying the worker.
        Crucial for Phase 2 when workers might hold heavy models (e.g. freeing VRAM).
        """
        pass
