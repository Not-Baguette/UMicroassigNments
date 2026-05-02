import state
import llm
import tools
import time
import logging
import random
import os
from tkinter import messagebox
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurable limits (in seconds)
MIN_SLEEP = 15 * 60  # 15 minutes
MAX_SLEEP = 2 * 60 * 60  # 2 hours
MATERIALS_DIR = "materials"

class MaterialFileHandler(FileSystemEventHandler):
    """Watches for new material files and processes them."""
    
    def __init__(self, callback):
        self.callback = callback
        self.processed_files = set()
    
    def on_created(self, event):
        if event.is_directory:
            return
        
        # Skip hidden files and already processed files
        if os.path.basename(event.src_path).startswith('.'):
            return
        
        if event.src_path in self.processed_files:
            return
        
        # Wait a moment for the file to be fully written
        time.sleep(1)
        
        self.processed_files.add(event.src_path)
        logger.info(f"New material detected: {event.src_path}")
        self.callback(event.src_path)

def process_new_material(file_path):
    """Process a newly detected material file."""
    try:
        filename = os.path.basename(file_path)
        current_state = state.load_state()
        material_id = filename
        
        # Skip if already processed
        if material_id in current_state["active_assignments"]:
            logger.info(f"Material {filename} already in queue.")
            return
        
        # Read the file content
        try:
            content = ""
            if filename.lower().endswith(".pdf"):
                from pypdf import PdfReader
                reader = PdfReader(file_path)
                for page in reader.pages:
                    content += (page.extract_text() or "") + "\n"
            else:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            
            if not content.strip():
                logger.warning(f"File {filename} is empty.")
                return
            
            logger.info(f"Decomposing material: {filename}...")
            decomposition = llm.decompose_assignment(filename, content)
            
            if decomposition and "tasks" in decomposition:
                current_state["active_assignments"][material_id] = {
                    "title": filename,
                    "description": content[:500],  # Store preview
                    "pending_tasks": decomposition["tasks"],
                    "completed_tasks": []
                }
                state.save_state(current_state)
                
                num_tasks = len(decomposition['tasks'])
                logger.info(f"Added {num_tasks} micro-tasks for '{filename}'")
                tools.send_notification(
                    "New Study Material",
                    f"Loaded '{filename}' with {num_tasks} micro-tasks. Get ready!",
                    timeout=5000
                )
        
        except Exception as e:
            logger.error(f"Error processing file {filename}: {e}")
    
    except Exception as e:
        logger.error(f"Error in process_new_material: {e}")

def main():
    logger.info("Starting UMNMicroassigNment Agent...")
    
    # Create materials folder if it doesn't exist
    if not os.path.exists(MATERIALS_DIR):
        os.makedirs(MATERIALS_DIR)
        logger.info(f"Created '{MATERIALS_DIR}' folder.")
    
    # Set up file watcher
    event_handler = MaterialFileHandler(process_new_material)
    observer = Observer()
    observer.schedule(event_handler, path=MATERIALS_DIR, recursive=False)
    observer.start()
    logger.info(f"File watcher started for '{MATERIALS_DIR}' folder.")
    
    # Initial scan for existing materials
    logger.info("Scanning for existing materials...")
    for filename in os.listdir(MATERIALS_DIR):
        file_path = os.path.join(MATERIALS_DIR, filename)
        if os.path.isfile(file_path) and not filename.startswith('.'):
            process_new_material(file_path)
    
    try:
        while True:
            current_state = state.load_state()
            
            # Check for pending tasks
            task_found = False
            for material_id, data in current_state["active_assignments"].items():
                if data["pending_tasks"]:
                    task = data["pending_tasks"].pop(0)
                    
                    # Show Interactive Popup
                    logger.info(f"Presenting micro-task for '{data['title']}'")
                    tools.send_notification(
                        f"Micro-Task Ready",
                        f"New task from '{data['title']}'. Click to answer.",
                        timeout=5000
                    )
                    
                    user_answer = tools.show_interactive_popup(data['title'], task)
                    
                    if user_answer is not None:
                        # Get feedback from LLM
                        logger.info("Getting feedback...")
                        feedback = llm.get_feedback(task, user_answer)
                        
                        # Store answer with feedback and timestamp
                        data["completed_tasks"].append({
                            "task": task,
                            "answer": user_answer,
                            "feedback": feedback
                        })
                        
                        state.save_state(current_state)
                        task_found = True
                        
                        # Check if this was the last task
                        if not data["pending_tasks"]:
                            logger.info(f"All tasks complete for '{data['title']}'. Compiling final document...")
                            final_doc = llm.compile_assignment(data['title'], data['completed_tasks'])
                            
                            filename = f"final_{material_id}.md"
                            filename = filename.replace(".txt", "").replace(".md", "")
                            if not filename.endswith(".md"):
                                filename += ".md"
                            
                            with open(filename, "w", encoding="utf-8") as f:
                                f.write(final_doc)
                            
                            logger.info(f"Final document saved to {filename}")
                            tools.send_notification(
                                "Assignment Complete!",
                                f"Your final notes are ready: {filename}",
                                timeout=10000
                            )
                            messagebox.showinfo("Success", f"Session complete! Final notes saved to {filename}")
                    else:
                        # User skipped/cancelled, put task back
                        data["pending_tasks"].insert(0, task)
                    
                    state.save_state(current_state)
                    break  # Only one task per loop iteration
            
            # Wait for next task
            if task_found:
                sleep_time = random.randint(MIN_SLEEP, MAX_SLEEP)
                logger.info(f"Task completed. Sleeping for {sleep_time // 60} minutes before next task...")
                time.sleep(sleep_time)
            else:
                logger.info("No pending tasks. Checking again in 1 minute...")
                time.sleep(60)
    
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        observer.stop()
    finally:
        observer.join()

if __name__ == "__main__":
    main()
