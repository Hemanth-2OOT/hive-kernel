import subprocess
import json
import time
import psutil
import threading
from collections import defaultdict

CELL_PROFILES = {
    "sentiment": 550,
    "embedding": 400,
    "llm": 1500
}

PRIORITY = {
    "embedding": 3,
    "sentiment": 2,
    "llm": 1
}

class Reservoir:
    def __init__(self, max_ram_mb=4096, idle_ttl_sec=300):
        self.cells = {}
        self.last_used = {}
        self.max_ram_mb = max_ram_mb
        self.idle_ttl_sec = idle_ttl_sec
        
        self.topology_lock = threading.Lock()
        self.cell_locks = defaultdict(threading.Lock)

    def _get_rss(self, pid):
        try:
            return psutil.Process(pid).memory_info().rss / 1e6
        except psutil.NoSuchProcess:
            return 0.0

    def get_total_rss(self):
        with self.topology_lock:
            total = 0.0
            for cell_type, proc in self.cells.items():
                if proc and proc.poll() is None:
                    total += self._get_rss(proc.pid)
            return total

    def cleanup_idle(self):
        with self.topology_lock:
            self._cleanup_idle_unsafe()
            
    def _cleanup_idle_unsafe(self):
        now = time.time()
        to_evict = []
        for cell_type, last_t in self.last_used.items():
            if cell_type in self.cells and (now - last_t) > self.idle_ttl_sec:
                to_evict.append(cell_type)
        for c in to_evict:
            print(f"[{c.upper()}] Evicted due to Idle TTL (> {self.idle_ttl_sec}s)", flush=True)
            self._kill_cell_unsafe(c)

    def select_victim(self):
        with self.topology_lock:
            return self._select_victim_unsafe()

    def _select_victim_unsafe(self):
        now = time.time()
        best_victim = None
        max_score = -1.0
        
        for cell_type, proc in self.cells.items():
            if not proc or proc.poll() is not None:
                continue
            
            rss = self._get_rss(proc.pid)
            idle_seconds = now - self.last_used.get(cell_type, now)
            priority = PRIORITY.get(cell_type, 1)
            
            score = (rss * idle_seconds) / priority
            if score > max_score:
                max_score = score
                best_victim = cell_type
                
        return best_victim

    def ensure_capacity(self, required_mb):
        with self.topology_lock:
            self._ensure_capacity_unsafe(required_mb)
            
    def _ensure_capacity_unsafe(self, required_mb):
        self._cleanup_idle_unsafe()
        
        def _current_rss():
            t = 0.0
            for ct, proc in self.cells.items():
                if proc and proc.poll() is None:
                    t += self._get_rss(proc.pid)
            return t
            
        while _current_rss() + required_mb > self.max_ram_mb:
            victim = self._select_victim_unsafe()
            if not victim:
                raise RuntimeError(f"Cannot free enough RAM for {required_mb}MB. Budget too tight.")
            
            print(f"[{victim.upper()}] Evicted due to RAM Budget (Total would exceed {self.max_ram_mb}MB)", flush=True)
            self._kill_cell_unsafe(victim)

    def evict_cell(self, cell_type):
        with self.topology_lock:
            self._kill_cell_unsafe(cell_type)

    def _kill_cell_unsafe(self, cell_type):
        proc = self.cells.get(cell_type)
        if proc:
            try:
                proc.stdin.close()
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.terminate()
            del self.cells[cell_type]
            if cell_type in self.last_used:
                del self.last_used[cell_type]

    def start_cell(self, cell_type: str) -> None:
        with self.topology_lock:
            self._start_cell_unsafe(cell_type)
            
    def _start_cell_unsafe(self, cell_type: str) -> None:
        if cell_type in self.cells and self.cells[cell_type].poll() is None:
            return 
            
        required_mb = CELL_PROFILES.get(cell_type, 500)
        self._ensure_capacity_unsafe(required_mb)
        
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if cell_type == "sentiment":
            script = os.path.join(base_dir, "cells", "sentiment_server.py")
        elif cell_type == "embedding":
            script = os.path.join(base_dir, "cells", "embedding_server.py")
        elif cell_type == "llm":
            script = os.path.join(base_dir, "cells", "llm_server.py")
        else:
            raise ValueError(f"Unknown cell type: {cell_type}")
            
        proc = subprocess.Popen(
            ["python", script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        self.cells[cell_type] = proc
        self.last_used[cell_type] = time.time()

        try:
            boot = json.loads(proc.stdout.readline())
            print(f"Child ({cell_type}): {boot}", flush=True)
            ready = json.loads(proc.stdout.readline())
            print(f"Child ({cell_type}): {ready}", flush=True)
        except Exception as e:
            raise RuntimeError(f"Cell {cell_type} failed handshake: {e}")

    def get_child_pid(self, cell_type: str):
        with self.topology_lock:
            proc = self.cells.get(cell_type)
            return proc.pid if proc else None

    def infer(self, cell_type: str, task_id: int, payload: str) -> dict:
        cold_started = False
        
        with self.topology_lock:
            if cell_type not in self.cells or self.cells[cell_type].poll() is not None:
                print(f"[{cell_type.upper()}] Cold start triggered by infer()...", flush=True)
                self._start_cell_unsafe(cell_type)
                cold_started = True

        # ARCHITECTURAL INVARIANT: Write + Read MUST remain atomic inside cell_locks.
        # If writing and reading are split into separate locks "for performance", 
        # a thread crash mid-flight will leave unpredictable orphaned lines stacking up in the pipe.
        # This atomic lock guarantees at most one orphaned line can ever exist at a time,
        # which is safely drained by the task_id matching loop below.
        with self.cell_locks[cell_type]:
            proc = self.cells.get(cell_type)
            if not proc or proc.poll() is not None:
                with self.topology_lock:
                    self._start_cell_unsafe(cell_type)
                    cold_started = True
                proc = self.cells.get(cell_type)
                
            self.last_used[cell_type] = time.time()

            req = {"task_id": task_id, "payload": payload}
            proc.stdin.write(json.dumps(req) + "\n")
            proc.stdin.flush()

            if "CRASH_CLIENT_MIDFLIGHT" in payload and task_id == 1:
                print(f"[RESERVOIR] DELIBERATE CRASH mid-flight for Task {task_id} after flush()!", flush=True)
                raise RuntimeError("Mid-flight thread crash simulated")

            while True:
                line = proc.stdout.readline()
                if not line:
                    raise RuntimeError(f"Cell {cell_type} closed stdout unexpectedly")
                    
                resp = json.loads(line)
                resp_task_id = resp.get("task_id")
                
                if resp_task_id == task_id:
                    break
                else:
                    print(f"[{cell_type.upper()}] DRAINED ORPHANED LINE (Expected {task_id}, Got {resp_task_id}): {line.strip()}", flush=True)
            
            self.last_used[cell_type] = time.time()
            total_rss = self.get_total_rss()
            memory_pressure = min(1.0, total_rss / self.max_ram_mb)
            active_cells = len([c for c in self.cells.values() if c and c.poll() is None])
            congestion = min(1.0, active_cells / 3.0) 
            
            if "telemetry" not in resp:
                resp["telemetry"] = {}
            
            resp["telemetry"]["cold_start"] = cold_started
                
            if "system_signals" not in resp["telemetry"]:
                resp["telemetry"]["system_signals"] = []
                
            resp["telemetry"]["system_signals"].append({
                "signal_type": "memory_pressure",
                "strength": round(memory_pressure, 4)
            })
            resp["telemetry"]["system_signals"].append({
                "signal_type": "congestion",
                "strength": round(congestion, 4)
            })
            
            if hasattr(self, "debug_barrier") and self.debug_barrier:
                if not hasattr(self, "debug_barrier_tasks") or task_id in self.debug_barrier_tasks:
                    self.debug_barrier.wait()
            
            return resp

    def shutdown(self) -> None:
        with self.topology_lock:
            cell_types = list(self.cells.keys())
            for c in cell_types:
                self._kill_cell_unsafe(c)
