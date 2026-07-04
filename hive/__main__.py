import time
import hive

def main():
    print("Initializing Hive Kernel and executing Swarm...")
    start = time.time()
    
    # Use the new single entry point public API
    result = hive.run("What is the capital of France? Analyze this text.")
    
    print(f"Execution complete in {time.time() - start:.2f}s")
    
    # Display the final execution trace
    import json
    print("Trace output:")
    print(json.dumps(result.trace, indent=2)[:500] + "...\n(truncated)")

if __name__ == "__main__":
    main()
