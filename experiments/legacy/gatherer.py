import urllib.parse
from datetime import datetime
from bin import Bin

class Gatherer:
    """
    The Active Gatherer (Consciousness / Speech Output / Immune System).
    Reads the Bin, validates the truth/integrity of worker outputs, 
    and assembles the final structured report.
    """
    def __init__(self, memory_bin: Bin):
        self.bin = memory_bin

    def validate_result(self, task_type: str, result: any) -> bool:
        """
        Immune system behavior: verifies the output actually makes sense.
        Prevents hallucinated or corrupted data from entering the final report.
        """
        if task_type == "count_words":
            # Word count must be a non-negative integer
            return isinstance(result, int) and result >= 0
            
        elif task_type == "extract_urls":
            # Must be a list of strings starting with http/https
            if not isinstance(result, list):
                return False
            for url in result:
                if not isinstance(url, str):
                    return False
                parsed = urllib.parse.urlparse(url)
                if parsed.scheme not in ["http", "https"] or not parsed.netloc:
                    return False
            return True
            
        elif task_type == "detect_dates":
            # Must be a list of strings
            if not isinstance(result, list):
                return False
            for date_str in result:
                if not isinstance(date_str, str):
                    return False
                # Layer 2 Semantic Validation
                valid = False
                for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%m-%d-%Y", "%m/%d/%Y"]:
                    try:
                        datetime.strptime(date_str, fmt)
                        valid = True
                        break
                    except ValueError:
                        pass
                if not valid:
                    return False
            return True
            
        elif task_type == "sentiment_analysis":
            return (
                isinstance(result, dict)
                and "label" in result
                and "confidence" in result
                and result["label"] in ["POSITIVE", "NEGATIVE"]
            )
            
        # Default strict: if we don't know how to validate it, we reject it
        return False

    def assemble(self, plan: dict) -> dict:
        """
        Reads from Bin, validates against the plan, computes confidence,
        and assembles the final report.
        """
        raw_data = self.bin.read_all()
        total_tasks = len(plan.get("tasks", []))
        valid_tasks = 0
        
        report = {
            "status": "success",
            "confidence": 0.0,
            "results": {},
            "rejected": {}
        }
        
        if total_tasks == 0:
            return report
        
        for task_id, entry in raw_data.items():
            # 1. Check if the worker actually succeeded
            if entry["status"] != "done":
                report["rejected"][task_id] = {
                    "reason": f"Worker failed or incomplete. Status: {entry['status']}",
                    "entry": entry
                }
                continue
                
            task_type = entry["task_type"]
            result = entry["result"]
            
            # 2. Immune System: Validate output integrity
            is_valid = self.validate_result(task_type, result)
            
            if is_valid:
                report["results"][task_type] = result
                valid_tasks += 1
            else:
                report["rejected"][task_id] = {
                    "reason": "Failed integrity validation (immune system rejection)",
                    "entry": entry
                }
                
        # 3. Calculate Confidence Score
        report["confidence"] = round(valid_tasks / total_tasks, 2)
                
        # If any rejections occurred, mark overall status as partial
        if report["rejected"]:
            report["status"] = "partial_success"
        if valid_tasks == 0:
            report["status"] = "failed"
            
        return report
