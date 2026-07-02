class Consolidator:
    def __init__(self):
        pass
        
    def consolidate(self, trace: dict) -> dict:
        """Transforms an episodic execution trace into a compressed semantic lesson."""
        
        # Extract the key insights from the outputs
        outcomes = []
        for t_id, data in trace["results"].items():
            if "output" in data:
                outcomes.append(f"Task {t_id} ({data['task_type']}): {data['output']}")
                
        lesson_text = f"Input: {trace['raw_input']}\nOutcomes:\n  " + "\n  ".join(outcomes)
        
        if trace.get("oracle_recommendations"):
            descriptions = [r.get("description", str(r)) for r in trace["oracle_recommendations"]]
            lesson_text += f"\nOracle Recommendations:\n  " + "\n  ".join(descriptions)
            
        res = {
            "lesson": lesson_text,
            "resource_cost": f"Time: {trace['end_time'] - trace['start_time']:.2f}s",
            "outcome": "Success" if trace["results"] else "Empty",
            "execution_id": trace["execution_id"]
        }
        
        # Inject the structured suggestions directly into the semantic metadata
        if trace.get("oracle_recommendations"):
            res["optimization_suggestions"] = trace["oracle_recommendations"]
            
        return res
