import sys
import json
import os
import warnings

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["HF_HUB_OFFLINE"] = "1"
warnings.filterwarnings("ignore")

def main():
    sys.stdout.write('{"status":"booting"}\n')
    sys.stdout.flush()

    try:
        from transformers import logging as hf_logging
        hf_logging.set_verbosity_error()
        from transformers import pipeline
        clf = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
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
                
            if payload.endswith("FORCE_AMBIGUITY"):
                result = {"label": "POSITIVE", "score": 0.55}
            else:
                result = clf(payload)[0]
            
            # Phase D1: Ambiguity Pheromone
            score = result["score"]
            uncertainty = 1.0 - abs(score - 0.5) * 2.0
            
            telemetry = {}
            if uncertainty > 0.3:
                telemetry["signals"] = [{
                    "signal_type": "ambiguity",
                    "strength": round(uncertainty, 4),
                    "metadata": {"score": round(score, 4)}
                }]
            
            resp = {
                "task_id": task_id,
                "status": "done",
                "result": {
                    "label": result["label"],
                    "confidence": round(score, 4)
                },
                "telemetry": telemetry
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
