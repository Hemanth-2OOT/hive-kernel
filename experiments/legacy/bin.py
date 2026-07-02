class Bin:
    """
    In-memory storage for worker results.
    Enforces append-only writes and no direct dictionary access.
    """
    def __init__(self):
        # Prefix with underscore to discourage direct access from outside
        self._data = {}

    def write(self, task_id: int, worker_id: str, task_type: str, status: str, result: any) -> None:
        """
        Write a result and metadata to the bin for a specific task.
        Enforces that a task_id can only be written to once (append-only style).
        """
        if task_id in self._data:
            raise ValueError(f"Task ID {task_id} already exists in Bin. Overwrites are not allowed.")
        self._data[task_id] = {
            "worker_id": worker_id,
            "task_type": task_type,
            "status": status,
            "result": result
        }

    def task_complete(self, task_id: int) -> bool:
        """
        Check if a task has been completed and written to the bin.
        Alpha uses this for monitoring worker progress and lifecycle management.
        """
        return task_id in self._data

    def read_all(self) -> dict:
        """
        Returns all entries in the bin. Used by the Gatherer.
        Returns a shallow copy to prevent external mutation of the internal state.
        """
        return dict(self._data)
