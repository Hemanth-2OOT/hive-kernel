import sys
import json
import os
import urllib.request

def query_ollama(model_name, prompt, keep_alive_sec: int):
    # keep_alive_sec is passed on every request to Ollama so the idle-timeout is refreshed
    # with each inference call, not just at boot. Ollama resets the timer per-request, so
    # omitting this field on live calls would silently revert to Ollama's 5m default.
    req = urllib.request.Request("http://127.0.0.1:11434/api/generate", method="POST")
    req.add_header('Content-Type', 'application/json')
    data = json.dumps({
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "keep_alive": keep_alive_sec,
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

    # keep_alive_sec is passed from Reservoir via argv[2], sourced from HiveConfig.
    # Default matches HiveConfig.ollama_keep_alive_sec (idle_ttl_sec + 60s headroom).
    try:
        keep_alive_sec = int(sys.argv[2]) if len(sys.argv) > 2 else 360
    except ValueError:
        keep_alive_sec = 360

    try:
        # Boot ping: loads the model into Ollama and sets its idle-timeout.
        # keep_alive_sec is the hard VRAM-reclamation backstop that survives any kill
        # scenario (SIGKILL, power loss, docker kill) where the finally block below
        # cannot run. Must be > HiveConfig.idle_ttl_sec to avoid cold-start thrashing
        # on legitimate calls within Hive's own warm window.
        query_ollama(model_name, "", keep_alive_sec)
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
                
                gen_text = query_ollama(model_name, payload, keep_alive_sec)
                
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
        # Best-effort fast path: explicitly unload the model on clean shutdown (EOF from
        # parent death or SIGINT). This reclaims VRAM immediately rather than waiting for
        # the keep_alive_sec backstop. The backstop handles the cases where this block
        # cannot run (SIGKILL, power loss).
        try:
            req = urllib.request.Request("http://127.0.0.1:11434/api/generate", method="POST")
            req.add_header('Content-Type', 'application/json')
            data = json.dumps({"model": model_name, "keep_alive": 0}).encode()
            urllib.request.urlopen(req, data=data)
        except:
            pass

if __name__ == "__main__":
    main()
