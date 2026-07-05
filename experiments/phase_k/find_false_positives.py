import json
from hive.runtime.reservoir import Reservoir
from hive.memory.hippocampus import Hippocampus
from hive.memory.verifier import SemanticVerifier
from hive.config import HiveConfig

config = HiveConfig(max_vram_mb=6000)
res = Reservoir(config)
verifier = SemanticVerifier(res, cell_name="hermes3:8b") 
hippo = Hippocampus(res, verifier=verifier, config=config)

clusters = {
    "1": {"A": "How do I fix a CUDA OutOfMemoryError in PyTorch?", "D": "How do I convert a PyTorch tensor to a NumPy array?"},
    "2": {"A": "Write a python script to scrape data from a website.", "D": "Write a python script to scrape rust off metal."},
    "3": {"A": "Translate this text into French.", "D": "Translate this text into Spanish."},
    "4": {"A": "Create a React component for a dropdown menu.", "D": "Create a React component for a date picker."},
    "5": {"A": "Write a short poem about the rain.", "D": "Write a short poem about the sun."},
    "6": {"A": "How do I reverse a linked list in C++?", "D": "How do I reverse a string in C++?"},
    "7": {"A": "Explain quantum entanglement to a 5 year old.", "D": "Explain quantum computing to a college student."},
    "8": {"A": "What are the health benefits of green tea?", "D": "What are the health benefits of black coffee?"},
    "9": {"A": "How do I bake a chocolate cake from scratch?", "D": "How do I bake chocolate chip cookies?"},
    "10": {"A": "Write a SQL query to find the second highest salary.", "D": "Write a SQL query to find the lowest salary."},
    "11": {"A": "What is the capital of Australia?", "D": "What is the capital of Austria?"},
    "12": {"A": "How do I tie a Windsor knot?", "D": "How do I tie my shoelaces?"},
    "13": {"A": "Explain the difference between TCP and UDP.", "D": "Explain the difference between IPv4 and IPv6."},
    "14": {"A": "Write a bash script to backup a directory.", "D": "Write a bash script to delete a directory."},
    "15": {"A": "What are the rules of chess?", "D": "What are the rules of checkers?"},
    "16": {"A": "How do I plant tomatoes in a garden?", "D": "How do I plant potatoes in a garden?"},
    "17": {"A": "Explain the theory of relativity.", "D": "Explain the theory of evolution."},
    "18": {"A": "How do I configure Nginx as a reverse proxy?", "D": "How do I configure Apache as a web server?"},
    "19": {"A": "What is the plot of The Great Gatsby?", "D": "What is the plot of To Kill a Mockingbird?"},
    "20": {"A": "How do I resolve a git merge conflict?", "D": "How do I undo a git commit?"}
}

for cid, prompts in clusters.items():
    hippo.store_semantic(prompts["A"], {"cluster": cid, "type": "A"})

for cid, prompts in clusters.items():
    query_d = prompts["D"]
    verified = hippo.query_verified(query_d, task_id=int(cid))
    passed = not any(v.raw_memory.get("cluster") == cid for v in verified)
    if not passed:
        print(f"[FAIL] False Positive! Herms thought '{query_d}' was a paraphrase of '{prompts['A']}'")
        
res.shutdown()
