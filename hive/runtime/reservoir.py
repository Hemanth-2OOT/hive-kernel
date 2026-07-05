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
        
        self._warm_pool = {}  # {proc: Popen}
        self._warm_pool_lock = threading.Lock()
        
        self.topology_lock = threading.Lock()
        self.vram_condition = threading.Condition(self.topology_lock)
        
        # INVARIANT: Callers must NEVER hold a `cell_lock` across a call into another cell
        # (e.g. holding sentiment and calling infer() for qwen). Doing so violates the global
        # CELL_LOCK_ORDER and will trigger a true OS-style circular deadlock, which is currently
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
            with self._warm_pool_lock:
                for cell_type, proc in self._warm_pool.items():
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
            
        with self._warm_pool_lock:
            to_evict_warm = []
            for cell_type, last_t in self.last_used.items():
                if cell_type in self._warm_pool and (now - last_t) > self.idle_ttl_sec:
                    to_evict_warm.append(cell_type)
            for c in to_evict_warm:
                proc = self._warm_pool.pop(c)
                print(f"[{c.upper()}] Warm Pool process terminated due to Idle TTL", flush=True)
                proc.terminate()


    def select_victim(self):
        with self.topology_lock:
            return self._select_victim_unsafe()

    def _select_victim_unsafe(self, ignore_locks=False, evictor_type: str = "unknown"):
        now = time.time()
        best_victim = None
        max_score = -1.0
        
        evictor_priority = self.priority.get(evictor_type, 1)
        
        for cell_type, proc in self.cells.items():
            if not proc or proc.poll() is not None:
                continue
            
            victim_priority = self.priority.get(cell_type, 1)
            
            # Strict priority enforcement: lower/equal priority evictors can NEVER evict higher priority cells.
            if victim_priority < evictor_priority:
                continue
                
            # Violent eviction (ignore_locks=True) is ONLY allowed if the evictor is STRICTLY higher priority.
            if ignore_locks and victim_priority <= evictor_priority:
                continue
            
            if not ignore_locks and self.cell_locks[cell_type].locked():
                continue
            
            vram = self._get_vram(cell_type)
            idle_seconds = now - self.last_used.get(cell_type, now)
            
            score = (vram * idle_seconds) / victim_priority
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
            attempts += 1
            if attempts >= 20:
                active_locks = [c for c in self.cells if self.cell_locks[c].locked()]
                raise ReservoirContentionTimeout(
                    f"Could not acquire VRAM for {cell_type} (needed {required_mb}MB). Locked cells: {active_locks}"
                )
                
            victim = self._select_victim_unsafe(ignore_locks=False, evictor_type=cell_type)
            if not victim:
                victim = self._select_victim_unsafe(ignore_locks=True, evictor_type=cell_type)
                if not victim:
                    raise ReservoirContentionTimeout(f"No cells available to evict for {cell_type} (all higher or equal priority)")
                
                print(f"[{victim.upper()}] Violently evicted due to VRAM Budget (Total would exceed {self.max_vram_mb}MB)", flush=True)
                self._kill_cell_unsafe(victim)
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
            del self.cells[cell_type]
        else:
            with self._warm_pool_lock:
                proc = self._warm_pool.get(cell_type)
                if proc:
                    del self._warm_pool[cell_type]
                    
        if proc:
            # Fast-path VRAM unload
            if cell_type in ["hermes3:8b", "qwen2.5-coder:7b", "llm"]:
                try:
                    req = urllib.request.Request("http://127.0.0.1:11434/api/generate", method="POST")
                    req.add_header('Content-Type', 'application/json')
                    urllib.request.urlopen(req, data=json.dumps({"model": cell_type, "keep_alive": 0}).encode())
                    
                    # VRAM unload latency guard: wait for async deallocation
                    start_time = time.time()
                    cleared = False
                    while time.time() - start_time < 5.0:
                        ps_req = urllib.request.Request("http://127.0.0.1:11434/api/ps", method="GET")
                        ps_resp = urllib.request.urlopen(ps_req)
                        ps_data = json.loads(ps_resp.read().decode())
                        if not any(m.get("name", "").startswith(cell_type) for m in ps_data.get("models", [])):
                            cleared = True
                            break
                        time.sleep(0.1)
                    
                    if not cleared:
                        raise ReservoirContentionTimeout(f"Ollama failed to async-unload {cell_type} VRAM within 5.0s timeout.")
                except ReservoirContentionTimeout:
                    raise
                except Exception as e:
                    print(f"Error unloading {cell_type} from Ollama: {e}", flush=True)

            # Move to warm pool if safe, else terminate
            safe_to_pool = False
            # Check if cell is dirty (abandoned request / torn write)
            is_dirty = getattr(proc, 'is_dirty', False)
            
            # Check if cell_lock is acquired by ANY thread (if so, it's mid-request)
            if not is_dirty and self.cell_locks[cell_type].acquire(blocking=False):
                safe_to_pool = True
                self.cell_locks[cell_type].release()

            if safe_to_pool:
                with self._warm_pool_lock:
                    # Enforce single slot: kill existing occupant if different
                    existing_cells = list(self._warm_pool.keys())
                    for ex_c in existing_cells:
                        if ex_c != cell_type:
                            ex_proc = self._warm_pool.pop(ex_c)
                            ex_proc.terminate()
                    self._warm_pool[cell_type] = proc
            else:
                proc.terminate()

    def start_cell(self, cell_type: str) -> None:
        with self.topology_lock:
            self._start_cell_unsafe(cell_type)
            
    def _start_cell_unsafe(self, cell_type: str) -> None:
        if cell_type in self.cells and self.cells[cell_type].poll() is None:
            return 
            
        required_mb = self.cell_profiles.get(cell_type, 500)
        
        recovered_proc = None
        with self._warm_pool_lock:
            if cell_type in self._warm_pool:
                proc = self._warm_pool.pop(cell_type)
                if proc.poll() is None:
                    recovered_proc = proc
                    
        if recovered_proc:
            # Must ensure capacity even when recovering, so we can evict lower-priority cells
            # that took our VRAM while we were idle!
            self._ensure_capacity_unsafe(required_mb, cell_type=cell_type)
            self.cells[cell_type] = recovered_proc
            self.last_used[cell_type] = time.time()
            print(f"[{cell_type.upper()}] Recovered from warm pool", flush=True)
            return
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

        # LLM cells receive keep_alive_sec as argv[2] so Ollama's idle-timeout is sourced
        # from HiveConfig on every /api/generate call (boot + inference), not just at boot.
        if cell_type in ["hermes3:8b", "qwen2.5-coder:7b", "llm"]:
            cmd = ["python", script, cell_type, str(self.config.ollama_keep_alive_sec)]
        else:
            cmd = ["python", script, cell_type]
            
        proc = subprocess.Popen(
            cmd,
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
        
        with self.cell_locks[cell_type]:
            retries_outer = 0
            max_outer_retries_outer = 60
            with self.topology_lock:
                while retries_outer < max_outer_retries_outer:
                    if cell_type not in self.cells or self.cells[cell_type].poll() is not None:
                        # Before we declare it a cold start, check if it's in the warm pool
                        with self._warm_pool_lock:
                            in_warm_pool = cell_type in self._warm_pool
                        
                        if not in_warm_pool:
                            print(f"[{cell_type.upper()}] Cold start triggered by infer()...", flush=True)
                            
                        try:
                            self._start_cell_unsafe(cell_type)
                            cold_started = True
                            break
                        except ReservoirContentionTimeout as e:
                            # We failed to get VRAM. The topology lock is released while waiting!
                            pass
                    else:
                        break
                        
                    print(f"[{cell_type.upper()}] VRAM Budget too tight to start. Blocking...", flush=True)
                    self.vram_condition.wait(1.0)
                    retries_outer += 1
                
            if retries_outer >= max_outer_retries_outer:
                raise RuntimeError(f"Deadlock or unresolvable VRAM contention for {cell_type} after 5 retries.")
                
            proc = self.cells.get(cell_type)
            if not proc or proc.poll() is not None:
                raise RuntimeError(f"Cell {cell_type} closed unexpectedly before generation")
                
            self.last_used[cell_type] = time.time()
            
            # CRITICAL ORDERING: is_dirty must be set to True BEFORE the write() call.
            # This ensures that if the thread crashes at any point during or after the write,
            # the flag is reliably set and _kill_cell_unsafe will not pool the dirty process.
            proc.is_dirty = True

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
            
            proc.is_dirty = False
            
            with self._warm_pool_lock:
                if cell_type in self.cells:
                    self._warm_pool[cell_type] = self.cells.pop(cell_type)
                    self.last_used[cell_type] = time.time()
            with self.topology_lock:
                self.vram_condition.notify_all()
                
            return resp

    def shutdown(self) -> None:
        with self.topology_lock:
            cell_types = list(self.cells.keys())
            for c in cell_types:
                self._kill_cell_unsafe(c)
