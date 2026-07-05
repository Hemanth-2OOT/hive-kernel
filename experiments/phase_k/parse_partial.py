import statistics
import re

def parse_log(log_file):
    workload_a = []
    workload_b = []
    
    with open(log_file, "r") as f:
        for line in f:
            # Match lines like "  [A 12/30] 24.78s"
            m_a = re.search(r'\[A \d+/\d+\] ([\d\.]+)s', line)
            if m_a:
                workload_a.append(float(m_a.group(1)))
                
            m_b = re.search(r'\[B \d+/\d+\] ([\d\.]+)s', line)
            if m_b:
                workload_b.append(float(m_b.group(1)))
                
    def print_stats(name, data):
        if not data:
            print(f"{name}: No data")
            return
        data.sort()
        mean = statistics.mean(data)
        p50 = data[len(data)//2]
        p95 = data[int(len(data)*0.95)] if len(data) >= 20 else data[-1]
        stdev = statistics.stdev(data) if len(data) > 1 else 0
        print(f"\nStats for {name} (N={len(data)}):")
        print(f"  Mean:  {mean:.2f}s")
        print(f"  p50:   {p50:.2f}s")
        print(f"  p95:   {p95:.2f}s")
        print(f"  Stdev: {stdev:.2f}s")
        
    print_stats("Workload A", workload_a)
    print_stats("Workload B", workload_b)

if __name__ == "__main__":
    parse_log(r"C:\Users\HEMANTH\.gemini\antigravity\brain\55965be3-3215-478e-9c77-b5511b8ef3ca\.system_generated\tasks\task-1921.log")
