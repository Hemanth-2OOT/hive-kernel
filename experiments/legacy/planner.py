class Planner:
    """
    Translates raw user text into a structured task list.
    Phase 1: Deterministic mapping with no AI/LLM calls.
    Output provides only task types; Alpha handles payload injection and assignment.
    """
    def plan(self, user_text: str) -> dict:
        """
        Input: raw user text.
        Output: task list only (never solves tasks or attaches payloads).
        Includes priority and cost to future-proof for Alpha's intelligent scheduling.
        """
        return {
            "tasks": [
                {
                    "id": 1, 
                    "type": "count_words",
                    "priority": 1,
                    "cost": "low"
                },
                {
                    "id": 2, 
                    "type": "extract_urls",
                    "priority": 2,
                    "cost": "medium"
                },
                {
                    "id": 3, 
                    "type": "detect_dates",
                    "priority": 2,
                    "cost": "medium"
                },
                {
                    "id": 4,
                    "type": "sentiment_analysis",
                    "priority": 2,
                    "cost": "medium"
                }
            ]
        }
