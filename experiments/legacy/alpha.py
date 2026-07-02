import time
from enum import Enum
from typing import Dict, Any, Type, List
import uuid

# Import our system components
from bin import Bin
from worker import Worker
from labour import Labour
from workers.word_counter import WordCounter
from workers.url_extractor import UrlExtractor
from workers.date_detector import DateDetector
from workers.sentiment_cell import SentimentCell

class WorkerState(Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"
    DESTROYED = "DESTROYED"

class Alpha:
    """
    The core operating-system kernel of swarm_ai.
    Manages resource allocation, worker lifecycle, chunking, and memory.
    """
    def __init__(self, memory_bin: Bin):
        self.bin = memory_bin
        self.registry: Dict[str, Type[Worker]] = {}
        self.worker_states: Dict[str, WorkerState] = {}
        self.performance_metrics: List[Dict[str, Any]] = []
        
        # Resource constraint: if payload is > 100 characters, use labours
        self.CHUNK_THRESHOLD = 100 
        
        self.register_workers()

    def register_workers(self) -> None:
        """
        Maps task types to specific worker classes.
        Makes workers plug-and-play.
        """
        self.registry = {
            "count_words": WordCounter,
            "extract_urls": UrlExtractor,
            "detect_dates": DateDetector,
            "sentiment_analysis": SentimentCell
        }

    def create_worker(self, task_type: str, worker_id: str) -> Worker:
        """
        Dynamically instantiates a worker based on the registry.
        """
        worker_class = self.registry.get(task_type)
        if not worker_class:
            raise ValueError(f"Unknown task type: {task_type}")
            
        worker = worker_class(worker_id)
        self.worker_states[worker_id] = WorkerState.CREATED
        return worker

    def spawn_labours(self, worker: Worker, payload: str) -> Any:
        """
        Alpha decides to use Labours for memory management and chunking.
        Workers provide the logic hooks, Alpha executes the resource division.
        """
        chunks = worker.chunk_payload(payload)
        chunk_results = []
        
        for i, chunk in enumerate(chunks):
            labour = Labour(chunk_id=i)
            # Pass the worker's stateless processing function to the labour
            res = labour.run(chunk, worker.process_chunk)
            if res["status"] == "error":
                raise Exception(f"Labour {i} failed: {res.get('error')}")
            chunk_results.append(res["result"])
            
        # Worker provides the aggregation logic, Alpha executes it
        return worker.aggregate_results(chunk_results)

    def destroy_worker(self, worker: Worker) -> None:
        """
        Explicit garbage collection. Reclaims resources and updates state.
        Calls the worker's cleanup hook before deleting the Python reference
        to guarantee actual memory (e.g., VRAM) is freed.
        """
        worker_id = worker.worker_id
        
        # 1. Clean up heavy resources (models, file handles, etc.)
        worker.cleanup()
        
        # 2. Update OS state
        self.worker_states[worker_id] = WorkerState.DESTROYED
        print(f"Garbage Collector: Worker {worker_id} destroyed. Resources reclaimed.")
        
        # 3. Remove Python reference
        del worker

    def execute_plan(self, plan: dict, payload: str) -> None:
        """
        The main OS loop. Takes a plan, injects payloads, assigns workers,
        monitors lifecycle, and writes outputs to the Bin.
        """
        for task in plan.get("tasks", []):
            task_id = task["id"]
            task_type = task["type"]
            worker_id = f"{task_type}_{uuid.uuid4().hex[:6]}"
            
            # 1. Create
            worker = self.create_worker(task_type, worker_id)
            
            # 2. Run & Monitor
            self.worker_states[worker_id] = WorkerState.RUNNING
            start_time = time.time()
            
            try:
                if len(payload) > self.CHUNK_THRESHOLD:
                    # Alpha owns resource allocation: spawn labours
                    result = self.spawn_labours(worker, payload)
                    final_status = "done"
                    labours_used = True
                else:
                    # Direct execution for small payloads
                    task_with_payload = {"task_id": task_id, "task_type": task_type, "payload": payload}
                    res = worker.run(task_with_payload)
                    if res["status"] == "error":
                        raise Exception(res.get("error"))
                    result = res["result"]
                    final_status = "done"
                    labours_used = False
                    
                self.worker_states[worker_id] = WorkerState.DONE
                
            except Exception as e:
                result = str(e)
                final_status = "error"
                self.worker_states[worker_id] = WorkerState.FAILED
                labours_used = False
                
            end_time = time.time()
            execution_time = end_time - start_time
            
            # 3. Validate and Write to Bin
            # Alpha acts as the gatekeeper; Workers do not know Bin exists
            if final_status in ["done", "error"]:
                self.bin.write(
                    task_id=task_id,
                    worker_id=worker_id,
                    task_type=task_type,
                    status=final_status,
                    result=result
                )
                
            # 4. Experimental: Efficiency Scorer
            complexity_proxy = len(payload) if len(payload) > 0 else 1
            score = execution_time / complexity_proxy
            self.performance_metrics.append({
                "worker_id": worker_id,
                "task_type": task_type,
                "execution_time": execution_time,
                "labours_used": labours_used,
                "efficiency_score": score
            })
            
            # 5. Destroy
            self.destroy_worker(worker)
