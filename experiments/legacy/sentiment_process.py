import sys, json, time

t0 = time.perf_counter()

from transformers import pipeline
t1 = time.perf_counter()  # import cost

def run(text: str) -> dict:
    import os
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
    
    clf = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
    t2 = time.perf_counter()  # model load cost
    
    result = clf(text)[0]
    t3 = time.perf_counter()  # inference cost
    
    return {
        "status": "done",
        "result": result,
        "timing": {
            "import": round(t1 - t0, 3),
            "model_load": round(t2 - t1, 3),
            "inference": round(t3 - t2, 3),
        }
    }

if __name__ == "__main__":
    payload = json.loads(sys.stdin.read())
    print(json.dumps(run(payload["text"])))
