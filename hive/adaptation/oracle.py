from hive.core.dag import TaskGraph

class Oracle:
    def __init__(self):
        pass
        
    def analyze(self, trace: dict, graph: TaskGraph) -> list[dict]:
        recommendations = []
        
        if trace.get("cold_starts", 0) >= 2:
            recommendations.append({"description": f"Repeated cold starts detected ({trace.get('cold_starts')}). Suggest prewarming frequently used cells."})
            
        if trace.get("evictions", 0) > 0:
            recommendations.append({"description": f"System memory budget too tight (Peak RAM: {trace.get('peak_ram_mb', 0):.1f}MB, Evictions: {trace.get('evictions')}). Suggest increasing max_ram_mb or moving to larger host."})
            
        for t_id, res in trace.get("results", {}).items():
            if res["task_type"] == "llm_verify":
                t_node = next((t for t in graph.tasks if t.id == t_id), None)
                if t_node:
                    for dep in t_node.depends_on:
                        dep_res = trace["results"].get(dep)
                        if dep_res and dep_res["task_type"] == "classify":
                            conf = dep_res["output"].get("confidence", 0.0)
                            if conf > 0.90:
                                recommendations.append({"description": f"Task {t_id} (llm_verify) is redundant. Upstream sentiment already had high confidence ({conf}). Suggest removing."})

        all_deps = set()
        for t in graph.tasks:
            all_deps.update(t.depends_on)
            
        for t in graph.tasks:
            if t.id not in all_deps and t.type == "embed" and len(graph.tasks) > 1:
                recommendations.append({
                    "action": "remove_task",
                    "target_task": t.type,
                    "reason": "unused_downstream",
                    "description": f"Task {t.id} ({t.type}) output is never used downstream. Suggest removal."
                })
                
        cell_map = {"generate": "llm", "summarize": "llm", "classify": "sentiment", "sentiment": "sentiment", "embed": "embedding", "llm_verify": "llm"}
        for t in graph.tasks:
            for dep in t.depends_on:
                dep_node = next((n for n in graph.tasks if n.id == dep), None)
                if dep_node and cell_map.get(t.type) == cell_map.get(dep_node.type):
                    recommendations.append({"description": f"Tasks {dep_node.id} ({dep_node.type}) and {t.id} ({t.type}) route to the same physical cell ({cell_map.get(t.type)}). Suggest merging into a single prompt."})
                    
        return recommendations
