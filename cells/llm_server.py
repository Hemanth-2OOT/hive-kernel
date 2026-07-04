import sys
import json
import os
import urllib.request

def query_ollama(model_name, prompt):
    req = urllib.request.Request("http://localhost:11434/api/generate", method="POST")
    req.add_header('Content-Type', 'application/json')
    data = json.dumps({
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.0}
    }).encode()
    with urllib.request.urlopen(req, data=data) as response:
        result = json.loads(response.read().decode())
        return result.get("response", "").strip()

def main():
    sys.stdout.write('{"status":"booting"}\n')
    sys.stdout.flush()

    if len(sys.argv) > 1:
        model_name = sys.argv[1]
    else:
        model_name = "qwen2.5-coder:7b"

    try:
        # Ping Ollama to ensure it's alive and loaded
        query_ollama(model_name, "")
    except Exception as e:
        sys.stderr.write(f"LLM Server failed to boot model {model_name}: {e}\n")
        sys.exit(1)

    sys.stdout.write('{"status":"ready"}\n')
    sys.stdout.flush()

    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
                
            try:
                req = json.loads(line)
                task_id = req.get("task_id")
                payload = req.get("payload")
                
                if not isinstance(payload, str):
                    raise ValueError("Payload must be a string")
                
                gen_text = query_ollama(model_name, payload)
                
                resp = {
                    "task_id": task_id,
                    "status": "done",
                    "result": {
                        "text": gen_text
                    }
                }
            except Exception as e:
                t_id = None
                try:
                    t_id = json.loads(line).get("task_id")
                except:
                    pass
                resp = {
                    "task_id": t_id,
                    "status": "error",
                    "error": str(e)
                }
                
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
    finally:
        # Reached EOF (parent died or closed stdin), or child caught a signal (SIGINT)
        # Unload the model from Ollama's VRAM
        try:
            req = urllib.request.Request("http://localhost:11434/api/generate", method="POST")
            req.add_header('Content-Type', 'application/json')
            data = json.dumps({"model": model_name, "keep_alive": 0}).encode()
            urllib.request.urlopen(req, data=data)
        except:
            pass

if __name__ == "__main__":
    main()
