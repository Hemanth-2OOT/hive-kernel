import atexit
from hive.config import HiveConfig
from hive.runtime.reservoir import Reservoir
from hive.core.nucleus import Nucleus
from hive.core.cortex import CortexRouter
from hive.core.context import ExecutionContext

class HiveResult:
    """Wrapper around ExecutionContext defining the public contract."""
    def __init__(self, context: ExecutionContext):
        self._context = context
        
    @property
    def execution_id(self):
        return self._context.execution_id
        
    @property
    def results(self):
        return self._context.results
        
    @property
    def trace(self):
        return self._context.serialize_trace()

    def wait_for_consolidation(self, timeout=None):
        """Must be called before checking consolidation_error to avoid a race condition."""
        self._context.wait_for_consolidation(timeout=timeout)
        
    @property
    def consolidation_error(self):
        """
        Returns the error from the async consolidation thread, if any.
        Raises RuntimeError if accessed before calling wait_for_consolidation().
        """
        return self._context.consolidation_error

class HiveEngine:
    def __init__(self, config: HiveConfig = None):
        import threading
        self.config = config or HiveConfig()
        self.reservoir = Reservoir(self.config)
        self.nucleus = Nucleus(self.reservoir, self.config)
        self.cortex = CortexRouter()
        self.active_contexts = []
        self.active_contexts_lock = threading.Lock()
        
    def run(self, prompt: str) -> HiveResult:
        # Prune completed contexts to prevent memory leak in long-running processes
        # Wrapped in a lock to prevent concurrent runs from corrupting the active_contexts list
        with self.active_contexts_lock:
            self.active_contexts = [
                ctx for ctx in self.active_contexts
                if ctx.consolidation_thread and ctx.consolidation_thread.is_alive()
            ]
        
        graph = self.cortex.route(prompt)
        context = self.nucleus.execute(graph, prompt)
        
        with self.active_contexts_lock:
            self.active_contexts.append(context)
            
        return HiveResult(context)
        
    def shutdown(self):
        print("[HIVE] Shutting down... waiting for background tasks to complete (max 15s)")
        with self.active_contexts_lock:
            contexts_to_wait = list(self.active_contexts)
        for ctx in contexts_to_wait:
            ctx.wait_for_consolidation(timeout=15.0)
        self.reservoir.shutdown()

_default_engine = None

def run(prompt: str, config: HiveConfig = None) -> HiveResult:
    """
    Primary public entry point for Hive.
    Lazily initializes the default engine on first call.
    """
    global _default_engine
    if _default_engine is None:
        _default_engine = HiveEngine(config)
    return _default_engine.run(prompt)

def shutdown():
    """Manually shutdown the default engine and free VRAM."""
    global _default_engine
    if _default_engine is not None:
        _default_engine.shutdown()
        _default_engine = None

# Register an atexit handler for clean shutdowns.
# NOTE: This handler only runs on normal interpreter exit. It does NOT run on os._exit(),
# unhandled process crashes, or SIGKILL/SIGINT (unless SIGINT is unhandled and raises KeyboardInterrupt naturally).
# The *true* crash safety net for VRAM is the EOF cleanup hook inside the child llm_server.py processes.
# This atexit handler is merely a nice-to-have for clean exits, not a replacement for the child-side hook!
atexit.register(shutdown)
