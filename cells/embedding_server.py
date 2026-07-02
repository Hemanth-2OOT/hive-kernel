import sys
import json
import os
import warnings

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
# Embedding model doesn't need HF_HUB_OFFLINE if already cached, but adding it for safety
os.environ["HF_HUB_OFFLINE"] = "1"
warnings.filterwarnings("ignore")

def main():
    sys.stdout.write('{"status":"booting"}\n')
    sys.stdout.flush()

    try:
        from transformers import logging as hf_logging
        hf_logging.set_verbosity_error()
        from transformers import pipeline
        clf = pipeline("feature-extraction", model="sentence-transformers/all-MiniLM-L6-v2")
    except Exception as e:
        sys.exit(1)

    sys.stdout.write('{"status":"ready"}\n')
    sys.stdout.flush()

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
                
            result = clf(payload)
            seq = result[0]
            emb = [sum(col)/len(seq) for col in zip(*seq)]
            
            resp = {
                "task_id": task_id,
                "status": "done",
                "result": {
                    "vector": [round(v, 4) for v in emb]
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

if __name__ == "__main__":
    main()
