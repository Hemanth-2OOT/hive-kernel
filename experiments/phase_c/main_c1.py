from cortex import CortexRouter

def main():
    router = CortexRouter()
    
    examples = [
        "Summarize this article and tell sentiment",
        "Summarize and classify this article",
        "Generate story and embed it",
        "Generate article, summarize it, then classify and embed it",
        "Just embed this raw text."
    ]
    
    print("=== Hive Phase C1: Cortex Router DAG Resolution ===\n")
    
    for i, ex in enumerate(examples, 1):
        print(f"Example {i}:")
        print(f"Input: \"{ex}\"")
        
        graph = router.route(ex)
        
        print("Graph:")
        print(graph.to_json())
        print("-" * 50 + "\n")

if __name__ == "__main__":
    main()
