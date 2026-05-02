import os
import logging
import tkinter as tk
from tkinter import scrolledtext, messagebox
from pypdf import PdfReader
import llm
import platform
import subprocess

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def send_notification(title, message, timeout=10000):
    """
    Cross-platform notification system.
    Works on Windows, macOS, and Linux.
    Falls back to logging if notification fails.
    """
    system = platform.system()
    
    try:
        if system == "Windows":
            # Try using plyer first (cross-platform)
            try:
                from plyer import notification
                notification.notify(
                    title=title,
                    message=message,
                    timeout=timeout // 1000  # plyer uses seconds
                )
                logger.info(f"Notification sent: {title}")
                return True
            except Exception:
                # Fallback to Windows native
                try:
                    from win10toast import ToastNotifier
                    ToastNotifier().show_toast(title, message, duration=timeout // 1000)
                    logger.info(f"Notification sent (win10toast): {title}")
                    return True
                except Exception as e:
                    logger.warning(f"Failed to send Windows notification: {e}")
        
        elif system == "Darwin":  # macOS
            script = f'display notification "{message}" with title "{title}"'
            subprocess.run(["osascript", "-e", script], check=False)
            logger.info(f"Notification sent (macOS): {title}")
            return True
        
        elif system == "Linux":
            # Try notify-send (most Linux systems)
            subprocess.run(["notify-send", title, message], check=False)
            logger.info(f"Notification sent (Linux): {title}")
            return True
    
    except Exception as e:
        logger.warning(f"Notification failed: {e}")
    
    # Fallback: Log to console
    logger.info(f"NOTIFICATION: {title} - {message}")
    return False

def check_local_materials(materials_dir="materials"):
    materials = []
    if not os.path.exists(materials_dir):
        os.makedirs(materials_dir)
        return materials

    for filename in os.listdir(materials_dir):
        file_path = os.path.join(materials_dir, filename)
        if os.path.isfile(file_path):
            try:
                content = ""
                if filename.lower().endswith(".pdf"):
                    reader = PdfReader(file_path)
                    for page in reader.pages:
                        content += (page.extract_text() or "") + "\n"
                else:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                
                if content.strip():
                    materials.append({
                        "id": filename,
                        "title": filename,
                        "description": content
                    })
            except Exception as e:
                logger.error(f"Error reading file {filename}: {e}")
    return materials

class InteractivePopup:
    def __init__(self, title, task):
        self.root = tk.Tk()
        self.root.title(f"Micro-Task: {title}")
        self.root.geometry("600x500")
        self.root.attributes("-topmost", True)
        
        self.task = task
        self.final_answer = ""
        self.chat_history = []
        
        # UI Elements
        tk.Label(self.root, text="YOUR MICRO-TASK:", font=("Arial", 10, "bold")).pack(pady=5)
        self.task_label = tk.Label(self.root, text=task, wraplength=550, justify="left", font=("Arial", 10))
        self.task_label.pack(pady=10, padx=20)
        
        tk.Label(self.root, text="YOUR ANSWER:", font=("Arial", 10, "bold")).pack(pady=5)
        self.answer_text = scrolledtext.ScrolledText(self.root, height=5, width=60)
        self.answer_text.pack(pady=5, padx=20)
        
        self.btn_frame = tk.Frame(self.root)
        self.btn_frame.pack(pady=10)
        
        self.submit_btn = tk.Button(self.btn_frame, text="Submit Answer", command=self.submit_answer)
        self.submit_btn.pack(side=tk.LEFT, padx=5)
        
        self.feedback_label = tk.Label(self.root, text="", wraplength=550, font=("Arial", 10, "italic"), fg="blue")
        self.feedback_label.pack(pady=10, padx=20)
        
        self.interaction_frame = tk.Frame(self.root)
        # Hidden initially
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def submit_answer(self):
        answer = self.answer_text.get("1.0", tk.END).strip()
        if not answer:
            messagebox.showwarning("Warning", "Please provide an answer first.")
            return
        
        self.final_answer = answer
        self.submit_btn.config(state=tk.DISABLED)
        
        # Get Feedback
        feedback = llm.get_feedback(self.task, answer)
        self.feedback_label.config(text=f"Agent Feedback: {feedback}")
        
        # Show Ok / Argue buttons
        self.interaction_frame.pack(pady=5)
        self.ok_btn = tk.Button(self.interaction_frame, text="Ok (Accept)", command=self.finish)
        self.ok_btn.pack(side=tk.LEFT, padx=5)
        
        self.argue_btn = tk.Button(self.interaction_frame, text="Argue (Chat)", command=self.start_argue)
        self.argue_btn.pack(side=tk.LEFT, padx=5)

    def start_argue(self):
        self.interaction_frame.pack_forget()
        
        # Create Chat UI
        self.chat_frame = tk.Frame(self.root)
        self.chat_frame.pack(pady=5, fill=tk.BOTH, expand=True)
        
        self.chat_display = scrolledtext.ScrolledText(self.chat_frame, height=8, width=60, state=tk.DISABLED)
        self.chat_display.pack(pady=5, padx=20)
        
        self.chat_input = tk.Entry(self.chat_frame, width=50)
        self.chat_input.pack(side=tk.LEFT, padx=(20, 5), pady=5)
        self.chat_input.bind("<Return>", lambda e: self.send_chat())
        
        self.send_btn = tk.Button(self.chat_frame, text="Send", command=self.send_chat)
        self.send_btn.pack(side=tk.LEFT, padx=5)
        
        self.done_btn = tk.Button(self.root, text="Done", command=self.finish, bg="green", fg="white")
        self.done_btn.pack(pady=10)
        
        # Initial History
        self.chat_history = [
            {"role": "user", "parts": [{"text": f"Micro-task: {self.task}\nMy answer: {self.final_answer}"}]},
            {"role": "model", "parts": [{"text": self.feedback_label.cget("text")}]}
        ]
        self.update_chat_display("System", "Chat started. Explain why you think your answer is correct or ask for clarification.")

    def send_chat(self):
        msg = self.chat_input.get().strip()
        if not msg: return
        
        self.chat_input.delete(0, tk.END)
        self.update_chat_display("You", msg)
        
        self.chat_history.append({"role": "user", "parts": [{"text": msg}]})
        
        # Get AI response
        ai_resp = llm.chat_with_agent(self.task, self.final_answer, self.chat_history)
        self.update_chat_display("Agent", ai_resp)
        self.chat_history.append({"role": "model", "parts": [{"text": ai_resp}]})

    def update_chat_display(self, sender, text):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"{sender}: {text}\n\n")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def finish(self):
        self.root.destroy()

    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to skip this task? It will remain pending."):
            self.final_answer = None
            self.root.destroy()

    def run(self):
        self.root.mainloop()
        return self.final_answer

def show_interactive_popup(title, task):
    popup = InteractivePopup(title, task)
    return popup.run()
