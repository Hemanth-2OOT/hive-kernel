import json

class Task:
    def __init__(self, task_id: int, task_type: str, depends_on: list[int], input_source: str, source: str = "user"):
        self.id = task_id
        self.type = task_type
        self.depends_on = depends_on
        self.input_source = input_source
        self.source = source

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "depends_on": self.depends_on,
            "input_source": self.input_source,
            "source": self.source
        }

class TaskGraph:
    def __init__(self):
        self.tasks = []

    def add_task(self, task: Task):
        self.tasks.append(task)
        
    def get_next_task_id(self):
        if not self.tasks:
            return 1
        return max(t.id for t in self.tasks) + 1

    def to_json(self):
        return json.dumps({"tasks": [t.to_dict() for t in self.tasks]}, indent=2)
