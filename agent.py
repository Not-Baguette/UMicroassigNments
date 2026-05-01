import state
import llm
import tools
import time
import logging
import random
import os
from tkinter import messagebox

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurable limits (in seconds)
MIN_SLEEP = 15 * 60  # 15 minutes
MAX_SLEEP = 2 * 60 * 60  # 2 hours
MATERIAL_SYNC_INTERVAL = 1200  # 20 minutes

def main():
    logger.info("Starting UMNMicroassigNment Agent...")
    
    last_material_sync = 0
    
    while True:
        current_state = state.load_state()
        now = time.time()
        
        # Material Sync
        if now - last_material_sync > MATERIAL_SYNC_INTERVAL:
            logger.info("Checking for new materials in 'materials/' folder...")
            local_materials = tools.check_local_materials()
            
            for material in local_materials:
                material_id = material["id"]
                if material_id not in current_state["active_assignments"]:
                    logger.info(f"New material found: {material['title']}. Decomposing...")
                    decomposition = llm.decompose_assignment(material['title'], material['description'])
                    
                    if decomposition and "tasks" in decomposition:
                        current_state["active_assignments"][material_id] = {
                            "title": material["title"],
                            "description": material["description"],
                            "pending_tasks": decomposition["tasks"],
                            "completed_tasks": []
                        }
                        logger.info(f"Added {len(decomposition['tasks'])} micro-tasks for '{material['title']}'")
            
            state.save_state(current_state)
            last_material_sync = now

        # Micro-Task
        task_found = False
        for material_id, data in current_state["active_assignments"].items():
            if data["pending_tasks"]:
                task = data["pending_tasks"].pop(0)
                
                # Show Interactive Popup (Pinned on Top to incentivize completion)
                logger.info(f"Triggering interactive micro-task for '{data['title']}'")
                user_answer = tools.show_interactive_popup(data['title'], task)
                
                if user_answer is not None:
                    data["completed_tasks"].append({
                        "task": task,
                        "answer": user_answer
                    })
                    
                    state.save_state(current_state)
                    task_found = True
                    
                    # Check if this was the last task
                    if not data["pending_tasks"]:
                        logger.info(f"Material '{data['title']}' complete! Compiling...")
                        final_doc = llm.compile_assignment(data['title'], data['completed_tasks'])
                        
                        filename = f"final_{material_id}.md"
                        filename = filename.replace(".txt", "").replace(".md", "")
                        if not filename.endswith(".md"):
                            filename += ".md"
                            
                        with open(filename, "w", encoding="utf-8") as f:
                            f.write(final_doc)
                        
                        logger.info(f"Final document saved to {filename}")
                        messagebox.showinfo("Success", f"Session complete! Final notes saved to {filename}")
                else:
                    # User skipped/cancelled, put task back
                    data["pending_tasks"].insert(0, task)
                
                break # Only one task per loop iteration

        # wait for next task or material sync
        if task_found:
            sleep_time = random.randint(MIN_SLEEP, MAX_SLEEP)
            logger.info(f"Task completed. Sleeping for {sleep_time // 60} minutes...")
            time.sleep(sleep_time)
        else:
            logger.info("No pending tasks. Checking again in 1 minute...")
            time.sleep(60)

if __name__ == "__main__":
    main()
