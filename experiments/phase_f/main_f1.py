from cortex import CortexRouter
from reservoir import Reservoir
from nucleus_executor import NucleusExecutor
from task_graph import TaskGraph, Task

def main():
    print("=== Hive Phase F1: Meta-Cognition Engine (Oracle) ===")
    
    # Highly constrained RAM to force evictions and thrashing (repeated cold starts)
    res = Reservoir(max_ram_mb=1600, idle_ttl_sec=300) 
    cortex = CortexRouter()
    nucleus = NucleusExecutor(res)
    
    # We explicitly construct a highly inefficient DAG to trigger all Oracle rules
    graph = TaskGraph()
    # Task 1: Generate (LLM)
    graph.add_task(Task(1, "generate", [], "raw"))
    # Task 2: Classify (Sentiment)
    graph.add_task(Task(2, "classify", [], "raw"))
    # Task 3: Summarize (LLM) - Same cell as Task 1 (Merge rule)
    graph.add_task(Task(3, "summarize", [1], "dependency"))
    # Task 4: LLM Verify (LLM) - Redundant because Classify is highly confident on normal strings
    graph.add_task(Task(4, "llm_verify", [2], "dependency"))
    # Task 5: Embed - Unused output
    graph.add_task(Task(5, "embed", [], "raw"))
    
    user_request = "This is a brilliantly clear and positive day!"
    print(f"\n[USER REQUEST]: {user_request}\n")
    print("[NUCLEUS] Executing highly inefficient DAG to test Oracle...\n")
    
    context = nucleus.execute(graph, user_request)
    
    res.shutdown()

if __name__ == "__main__":
    main()
