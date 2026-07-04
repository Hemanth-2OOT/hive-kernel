import time
import uuid
import threading
from hive.core.dag import Task
from hive.runtime.signals import Signal

class ExecutionContext:
    def __init__(self, raw_input: str):
        self.execution_id = str(uuid.uuid4())
        self.start_time = time.time()
        self.end_time = None
        self.raw_input = raw_input
        self.results = {}
        self.signals = []
        self.peak_ram_mb = 0.0
        self.cold_starts = 0
        self.evictions = 0
        self._consolidation_error = None
        self.consolidation_thread = None
        self._consolidation_waited = False
        
        # Fine-grained locks for thread safety
        self.results_lock = threading.Lock()
        self.signals_lock = threading.Lock()
        self.metrics_lock = threading.Lock()
        
    @property
    def consolidation_error(self):
        if not self._consolidation_waited and self.consolidation_thread and self.consolidation_thread.is_alive():
            raise RuntimeError("Race Condition: Cannot access consolidation_error before calling wait_for_consolidation().")
        return self._consolidation_error
        
    @consolidation_error.setter
    def consolidation_error(self, value):
        self._consolidation_error = value

    def wait_for_consolidation(self, timeout=None):
        if self.consolidation_thread:
            self.consolidation_thread.join(timeout=timeout)
        self._consolidation_waited = True

    def serialize_trace(self) -> dict:
        self.end_time = time.time()
        self.total_latency = self.end_time - self.start_time
        with self.results_lock, self.signals_lock, self.metrics_lock:
            return {
                "execution_id": self.execution_id,
                "start_time": self.start_time,
                "end_time": self.end_time,
                "total_latency": self.total_latency,
                "peak_ram_mb": self.peak_ram_mb,
                "cold_starts": self.cold_starts,
                "evictions": self.evictions,
                "raw_input": self.raw_input,
                "results": dict(self.results),
                "signals": [s.to_dict() for s in self.signals],
                "aggregates": self.aggregate_signals() # internal method doesn't relock because it is only called here, wait it does relock
            }

    def add_result(self, task_id: int, task_type: str, result: dict):
        with self.results_lock:
            self.results[task_id] = {
                "status": "done",
                "task_type": task_type,
                "output": result,
                "timestamp": time.time()
            }

    def add_failed_task(self, task_id: int, task_type: str, error: str):
        with self.results_lock:
            self.results[task_id] = {
                "status": "failed",
                "task_type": task_type,
                "error": error,
                "timestamp": time.time()
            }

    def add_signal(self, signal: Signal):
        with self.signals_lock:
            self.signals.append(signal)
            
    def update_metrics(self, cold_started: bool, current_ram: float):
        with self.metrics_lock:
            if cold_started:
                self.cold_starts += 1
            if current_ram > self.peak_ram_mb:
                self.peak_ram_mb = current_ram
                
    def increment_evictions(self):
        with self.metrics_lock:
            self.evictions += 1

    def get_signals(self):
        with self.signals_lock:
            return list(self.signals)

    def aggregate_signals(self):
        # We must avoid deadlock if called inside serialize_trace which already holds signals_lock
        # Python's Lock is not RLock. So we compute without acquiring lock, assuming caller holds it.
        # But if called externally, it needs the lock. We use an RLock just in case.
        pass

    def _merge_payloads(self, outputs: list[str]) -> str:
        return "\n".join(outputs)

    def resolve_payload(self, task: Task) -> str:
        if task.input_source == "raw":
            return self.raw_input
            
        upstream_outputs = []
        with self.results_lock:
            for dep_id in task.depends_on:
                if dep_id not in self.results:
                    raise RuntimeError(f"Missing dependency result for Task {dep_id}")
                
                res_dict = self.results[dep_id]["output"]
                
                if "text" in res_dict:
                    upstream_outputs.append(res_dict["text"])
                elif "label" in res_dict:
                    upstream_outputs.append(res_dict["label"])
                elif "vector" in res_dict:
                    upstream_outputs.append("[VECTOR_DATA]")
                else:
                    upstream_outputs.append(str(res_dict))
                
        return self._merge_payloads(upstream_outputs)

# Fix RLock issue in ExecutionContext by overriding methods carefully
ExecutionContext.results_lock = property(lambda self: getattr(self, '_results_lock'))
ExecutionContext.signals_lock = property(lambda self: getattr(self, '_signals_lock'))
ExecutionContext.metrics_lock = property(lambda self: getattr(self, '_metrics_lock'))

def __init__(self, raw_input: str):
    self.execution_id = str(uuid.uuid4())
    self.start_time = time.time()
    self.end_time = None
    self.raw_input = raw_input
    self.results = {}
    self.signals = []
    self.peak_ram_mb = 0.0
    self.cold_starts = 0
    self.evictions = 0
    
    self._consolidation_error = None
    self.consolidation_thread = None
    self._consolidation_waited = False
    
    self._results_lock = threading.RLock()
    self._signals_lock = threading.RLock()
    self._metrics_lock = threading.RLock()
    
ExecutionContext.__init__ = __init__

def aggregate_signals(self):
    totals = {}
    with self._signals_lock:
        for sig in self.signals:
            if sig.signal_type not in totals:
                totals[sig.signal_type] = 0.0
            totals[sig.signal_type] += sig.strength
    return totals
ExecutionContext.aggregate_signals = aggregate_signals
