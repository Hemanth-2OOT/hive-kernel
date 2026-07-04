import subprocess
import json
import os
import sys
import time
import threading
import random
import urllib.request
from collections import defaultdict
from hive.config import HiveConfig

class ReservoirContentionTimeout(Exception):
    pass

class Reservoir:
    def __init__(self, config: HiveConfig = None):
        self.config = config or HiveConfig()
        self.max_vram_mb = self.config.max_vram_mb
        self.idle_ttl_sec = self.config.idle_ttl_sec
        self.cell_profiles = self.config.cell_profiles
        self.priority = self.config.cell_priorities
        self.cell_lock_order = self.config.cell_lock_order

        self.cells = {}
        self.last_used = {}
        
        self.topology_lock = threading.Lock()
        
        # INVARIANT: Callers must NEVER hold a `cell_lock` across a call into another cell
        # (e.g. holding sentiment and calling infer() for qwen). Doing so violates the global
        # CELL_LOCK_ORDER and will trigger a true OS-style circular deadlock, which is currently
        # caught and aborted by the ReservoirContentionTimeout bounded wait.
        # `cell_locks` should be treated as INTERNAL to Reservoir, NOT a public API.
        self.cell_locks = defaultdict(threading.Lock)

    def _get_vram(self, cell_type):
        return self.cell_profiles.get(cell_type, 500)

    def get_total_vram(self):
        with self.topology_lock:
            total = 0.0
            for cell_type, proc in self.cells.items():
                if proc and proc.poll() is None:
                    total += self._get_vram(cell_type)
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

    def _select_victim_unsafe(self, ignore_locks=False):
        now = time.time()
        best_victim = None
        max_score = -1.0
        
        for cell_type, proc in self.cells.items():
            if not proc or proc.poll() is not None:
                continue
            
            if not ignore_locks and self.cell_locks[cell_type].locked():
                continue
            
            vram = self._get_vram(cell_type)
            idle_seconds = now - self.last_used.get(cell_type, now)
            priority = self.priority.get(cell_type, 1)
            
            score = (vram * idle_seconds) / priority
            if score > max_score:
                max_score = score
                best_victim = cell_type
                
        return best_victim

    def ensure_capacity(self, required_mb):
        with self.topology_lock:
            self._ensure_capacity_unsafe(required_mb, cell_type="unknown")
            
    def _current_vram(self):
        t = 0.0
        for ct, proc in self.cells.items():
            if proc and proc.poll() is None:
                t += self._get_vram(ct)
        return t

    def _ensure_capacity_unsafe(self, required_mb: float, cell_type: str):
        dead_cells = [c for c, p in self.cells.items() if p and p.poll() is not None]
        for c in dead_cells:
            print(f"[RESERVOIR] Automatically cleaning up dead ghost cell: {c}", flush=True)
            del self.cells[c]
            
        self._cleanup_idle_unsafe()
        
        attempts = 0
        
        if required_mb > self.max_vram_mb:
            raise MemoryError(f"Cell {cell_type} requires {required_mb}MB but max budget is {self.max_vram_mb}MB.")
            
        while self._current_vram() + required_mb > self.max_vram_mb:
            if attempts >= 20:
                active_locks = [c for c in self.cells if self.cell_locks[c].locked()]
                raise ReservoirContentionTimeout(
                    f"Could not acquire VRAM for {cell_type} (needed {required_mb}MB). Locked cells: {active_locks}"
                )
                
            victim = self._select_victim_unsafe(ignore_locks=False)
            if not victim:
                # If we can't find an unlocked victim, we MUST evict a locked victim to prevent deadlock.
                # But we must acquire its lock in CELL_LOCK_ORDER!
                victim = self._select_victim_unsafe(ignore_locks=True)
                if not victim:
                    raise MemoryError(f"No cells available to evict for {cell_type}")
                
                # Sort acquisition attempts by CELL_LOCK_ORDER
                locks_to_acquire = [cell_type, victim]
                locks_to_acquire.sort(key=lambda c: self.cell_lock_order.index(c) if c in self.cell_lock_order else 99)
                
                # We need to temporarily release topology lock to avoid deadlocking with threads 
                # that hold cell locks and need topology lock.
                self.topology_lock.release()
                
                acquired = []
                success = True
                import random
                jitter = random.uniform(0.5, 1.5)
                for c in locks_to_acquire:
                    if self.cell_locks[c].acquire(timeout=jitter):
                        acquired.append(c)
                    else:
                        success = False
                        break
                
                # Re-acquire topology lock
                self.topology_lock.acquire()
                
                if success:
                    # We hold both locks! Kill victim.
                    print(f"[{victim.upper()}] Evicted due to VRAM Budget (Total would exceed {self.max_vram_mb}MB)", flush=True)
                    self._kill_cell_unsafe(victim)
                    for c in reversed(acquired):
                        self.cell_locks[c].release()
                else:
                    for c in reversed(acquired):
                        self.cell_locks[c].release()
                    attempts += 1
                    continue
            else:
                print(f"[{victim.upper()}] Evicted due to VRAM Budget (Total would exceed {self.max_vram_mb}MB)", flush=True)
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
                
            if cell_type in ["hermes3:8b", "qwen2.5-coder:7b", "llm"]:
                try:
                    req = urllib.request.Request("http://localhost:11434/api/generate", method="POST")
                    req.add_header('Content-Type', 'application/json')
                    urllib.request.urlopen(req, data=json.dumps({"model": cell_type, "keep_alive": 0}).encode())
                    # Synchronous verify
                    for _ in range(10):
                        req_ps = urllib.request.Request("http://localhost:11434/api/ps")
                        with urllib.request.urlopen(req_ps) as response:
                            data = json.loads(response.read().decode())
                            models = [m["name"] for m in data.get("models", [])]
                            if not any(m.startswith(cell_type) for m in models):
                                break
                        time.sleep(1)
                except Exception as e:
                    print(f"Error unloading {cell_type} from Ollama: {e}", flush=True)

    def start_cell(self, cell_type: str) -> None:
        with self.topology_lock:
            self._start_cell_unsafe(cell_type)
            
    def _start_cell_unsafe(self, cell_type: str) -> None:
        if cell_type in self.cells and self.cells[cell_type].poll() is None:
            return 
            
        required_mb = self.cell_profiles.get(cell_type, 500)
        self._ensure_capacity_unsafe(required_mb, cell_type=cell_type)
        
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if cell_type == "sentiment":
            script = os.path.join(base_dir, "cells", "sentiment_server.py")
        elif cell_type == "embedding":
            script = os.path.join(base_dir, "cells", "embedding_server.py")
        elif cell_type in ["hermes3:8b", "qwen2.5-coder:7b", "llm"]:
            script = os.path.join(base_dir, "cells", "llm_server.py")
        else:
            raise ValueError(f"Unknown cell type: {cell_type}")
            
        proc = subprocess.Popen(
            ["python", script, cell_type],
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
        
        while True:
            with self.topology_lock:
                if cell_type not in self.cells or self.cells[cell_type].poll() is not None:
                    print(f"[{cell_type.upper()}] Cold start triggered by infer()...", flush=True)
                    self._start_cell_unsafe(cell_type)
                    cold_started = True
                    break
                else:
                    break
            print(f"[{cell_type.upper()}] VRAM Budget too tight to start. Blocking...", flush=True)
            time.sleep(1.0)

        with self.cell_locks[cell_type]:
            proc = self.cells.get(cell_type)
            if not proc or proc.poll() is not None:
                while True:
                    with self.topology_lock:
                        self._start_cell_unsafe(cell_type)
                        cold_started = True
                        break
                    print(f"[{cell_type.upper()}] VRAM Budget too tight to start inside lock. Blocking...", flush=True)
                    time.sleep(1.0)
                proc = self.cells.get(cell_type)
                
            self.last_used[cell_type] = time.time()

            req = {"task_id": task_id, "payload": payload}
            if "CRASH_CLIENT_TORN_WRITE" in payload and task_id == 1:
                # Write partial JSON without a newline
                proc.stdin.write(json.dumps(req)[:10])
                proc.stdin.flush()
                print(f"[RESERVOIR] DELIBERATE CRASH mid-write for Task {task_id}!", flush=True)
                raise RuntimeError("Mid-write thread crash simulated")

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
                    if resp.get("status") == "error" and resp_task_id is None:
                        raise RuntimeError(f"Cell {cell_type} consumed request in a malformed payload (torn write). Failing fast to prevent deadlock. Error: {resp.get('error')}")
            
            self.last_used[cell_type] = time.time()
            total_vram = self.get_total_vram()
            memory_pressure = min(1.0, total_vram / self.max_vram_mb)
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
            
            return resp

    def shutdown(self) -> None:
        with self.topology_lock:
            cell_types = list(self.cells.keys())
            for c in cell_types:
                self._kill_cell_unsafe(c)
