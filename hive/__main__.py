import time
from hive.runtime.reservoir import Reservoir
from hive.core.nucleus import Nucleus
from hive.memory.verifier import SemanticVerifier
from hive.core.dag import TaskGraph, Task

def main():
    print("Initializing Hive Kernel...")
    reservoir = Reservoir(max_ram_mb=4096)
    verifier = SemanticVerifier(reservoir)
    nucleus = Nucleus(reservoir)
    nucleus.hippocampus._verifier = verifier

    print("Building DAG...")
    g = TaskGraph()
    g.add_task(Task(1, "generate", [], "raw_input"))
    g.add_task(Task(2, "classify", [1], "dependency"))
    g.add_task(Task(3, "summarize", [2], "dependency"))

    print("Executing DAG...")
    start = time.time()
    nucleus.execute(g, "What is the capital of France? Analyze this text.")
    print(f"Execution complete in {time.time() - start:.2f}s")
    
    print("Shutting down...")
    reservoir.shutdown()

if __name__ == "__main__":
    main()
