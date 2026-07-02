import subprocess, json, time
import psutil, os

class SentimentHardCell:
    def run(self, payload: str) -> dict:
        t_start = time.perf_counter()
        proc = subprocess.run(
            ["python", "sentiment_process.py"],
            input=json.dumps({"text": payload}),
            capture_output=True, text=True, timeout=60
        )
        t_end = time.perf_counter()
        
        try:
            data = json.loads(proc.stdout)
            # Compute OS overhead (subprocess creation + Python interpreter boot)
            if "timing" in data:
                total_inner = data["timing"]["import"] + data["timing"]["model_load"] + data["timing"]["inference"]
                data["timing"]["os_overhead"] = round((t_end - t_start) - total_inner, 3)
                data["timing"]["total_wall_time"] = round(t_end - t_start, 3)
            return data
        except json.JSONDecodeError:
            print("Error parsing stdout:", proc.stdout)
            print("stderr:", proc.stderr)
            return {"status": "error", "error": proc.stderr}

def main():
    proc = psutil.Process(os.getpid())
    print("=== Swarm Architecture: Experiment 002 (Hard Cell) - N=5 ===")
    
    before = proc.memory_info().rss / 1e6
    print(f"Before any execution: {before:.1f} MB\n")
    
    cell = SentimentHardCell()
    
    texts = [
        "I'm sad and tired of everything.",
        "I feel amazing today. Everything is working.",
        "This architecture might actually work perfectly.",
        "Wait, is there a memory leak in the parent process?",
        "Nope, memory stays absolutely flat. Beautiful."
    ]
    
    for i, text in enumerate(texts):
        print(f"--- Run {i+1} ---")
        result = cell.run(text)
        after = proc.memory_info().rss / 1e6
        
        print(f"Result: {result.get('result')}")
        if "timing" in result:
            t = result["timing"]
            print(f"Timing Breakdown:")
            print(f"  OS Interpreter Overhead: {t.get('os_overhead')}s")
            print(f"  Transformers Import:     {t.get('import')}s")
            print(f"  Model Load (Disk->RAM):  {t.get('model_load')}s")
            print(f"  Inference:               {t.get('inference')}s")
            print(f"  Total Wall Time:         {t.get('total_wall_time')}s")
            
        print(f"Parent RAM After Run {i+1}: {after:.1f} MB\n")

if __name__ == "__main__":
    main()
