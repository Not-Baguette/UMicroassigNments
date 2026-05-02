import json
import os
from datetime import datetime

STATE_FILE = "student_state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "active_assignments": {}
    }

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

def add_task_answer(material_id, task_text, answer, feedback=None):
    """Store a task answer with feedback and timestamp."""
    state = load_state()
    if material_id in state["active_assignments"]:
        assignment = state["active_assignments"][material_id]
        if "completed_tasks" not in assignment:
            assignment["completed_tasks"] = []
        
        assignment["completed_tasks"].append({
            "task": task_text,
            "answer": answer,
            "feedback": feedback,
            "completed_at": datetime.now().isoformat()
        })
        save_state(state)

def get_assignment_progress(material_id):
    """Get completion stats for an assignment."""
    state = load_state()
    if material_id not in state["active_assignments"]:
        return None
    
    assignment = state["active_assignments"][material_id]
    pending = len(assignment.get("pending_tasks", []))
    completed = len(assignment.get("completed_tasks", []))
    total = pending + completed
    
    return {
        "pending": pending,
        "completed": completed,
        "total": total,
        "progress_percent": (completed / total * 100) if total > 0 else 0
    }
