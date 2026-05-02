import os
import logging
import tkinter as tk
from tkinter import scrolledtext, messagebox
from pypdf import PdfReader
import llm
import speech_recognition as sr

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
        self.root.geometry("700x400")
        self.root.attributes("-topmost", True)
        
        self.task = task
        self.final_answer = ""
        self.chat_history = []
        
        # UI Elements
        tk.Label(self.root, text="YOUR MICRO-TASK:", font=("Arial", 10, "bold")).pack(pady=5)
        
        # Task frame with label and voice button
        task_frame = tk.Frame(self.root)
        task_frame.pack(pady=5, padx=20)
        
        self.task_label = tk.Label(task_frame, text=task, wraplength=500, justify="left", font=("Arial", 10))
        self.task_label.pack(side=tk.LEFT)
        
        tk.Label(self.root, text="YOUR ANSWER:", font=("Arial", 10, "bold")).pack(pady=5)
        
        # Answer frame with text area and voice button
        answer_frame = tk.Frame(self.root)
        answer_frame.pack(pady=5, padx=20)
        
        self.answer_text = scrolledtext.ScrolledText(answer_frame, height=5, width=50)
        self.answer_text.pack(side=tk.LEFT)
        
        self.voice_input_btn = tk.Button(answer_frame, text="🎤 Voice Input", command=self.listen_and_transcribe,
                                       bg="#2196F3", fg="white", width=12, height=1)
        self.voice_input_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        self.btn_frame = tk.Frame(self.root)
        self.btn_frame.pack(pady=10)
        
        self.submit_btn = tk.Button(self.btn_frame, text="Submit Answer", command=self.submit_answer, bg="#2196F3", fg="white", width=15, height=2)
        self.submit_btn.pack(side=tk.LEFT, padx=5)
        
        self.feedback_label = tk.Label(self.root, text="", wraplength=550, font=("Arial", 10, "italic"), fg="blue")
        self.feedback_label.pack(pady=10, padx=20)
        
        self.interaction_frame = tk.Frame(self.root)
        # Hidden initially
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def speak_text(self, text):
        """Text-to-speech function"""
        def speak():
            try:
                engine = pyttsx3.init()
                engine.setProperty('rate', 180)  # Speed of speech
                engine.setProperty('volume', 0.8)  # Volume level (0.0 to 1.0)
                engine.say(text)
                engine.runAndWait()
            except Exception as e:
                logger.error(f"TTS error: {e}")
                messagebox.showerror("TTS Error", f"Could not speak text: {e}")
        
        # Run in separate thread to avoid blocking UI
        threading.Thread(target=speak, daemon=True).start()

    def listen_and_transcribe(self):
        """Speech-to-text function"""
        try:
            recognizer = sr.Recognizer()
            with sr.Microphone() as source:
                self.feedback_label.config(text="Listening... Speak your answer now.")
                self.root.update()
                
                # Adjust for ambient noise
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                # Listen for audio
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=30)
                
                self.feedback_label.config(text="Processing speech...")
                self.root.update()
                
                # Recognize speech
                text = recognizer.recognize_google(audio)
                
                # Insert recognized text into answer field
                current_text = self.answer_text.get("1.0", tk.END).strip()
                if current_text:
                    new_text = current_text + " " + text
                else:
                    new_text = text
                
                self.answer_text.delete("1.0", tk.END)
                self.answer_text.insert("1.0", new_text)
                
                self.feedback_label.config(text="Speech transcribed successfully!")
                
        except sr.WaitTimeoutError:
            self.feedback_label.config(text="No speech detected. Try again.")
        except sr.UnknownValueError:
            self.feedback_label.config(text="Could not understand speech. Try again.")
        except sr.RequestError as e:
            self.feedback_label.config(text=f"Speech recognition error: {e}")
            messagebox.showerror("Speech Recognition Error", f"Could not connect to speech service: {e}")
        except Exception as e:
            logger.error(f"Speech recognition error: {e}")
            self.feedback_label.config(text=f"Error: {e}")

    def listen_and_transcribe_chat(self):
        """Speech-to-text function for chat input"""
        try:
            recognizer = sr.Recognizer()
            with sr.Microphone() as source:
                self.feedback_label.config(text="Listening for chat message... Speak now.")
                self.root.update()
                
                # Adjust for ambient noise
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                # Listen for audio
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=20)
                
                self.feedback_label.config(text="Processing speech...")
                self.root.update()
                
                # Recognize speech
                text = recognizer.recognize_google(audio)
                
                # Insert recognized text into chat input field
                self.chat_input.delete(0, tk.END)
                self.chat_input.insert(0, text)
                
                self.feedback_label.config(text="Speech transcribed! Press Send or Enter.")
                
        except sr.WaitTimeoutError:
            self.feedback_label.config(text="No speech detected. Try again.")
        except sr.UnknownValueError:
            self.feedback_label.config(text="Could not understand speech. Try again.")
        except sr.RequestError as e:
            self.feedback_label.config(text=f"Speech recognition error: {e}")
            messagebox.showerror("Speech Recognition Error", f"Could not connect to speech service: {e}")
        except Exception as e:
            logger.error(f"Speech recognition error: {e}")
            self.feedback_label.config(text=f"Error: {e}")

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
        self.ok_btn = tk.Button(self.interaction_frame, text="Ok (Accept)", command=self.finish, bg="#2196F3", fg="white", width=12, height=2)
        self.ok_btn.pack(side=tk.LEFT, padx=5)
        
        self.argue_btn = tk.Button(self.interaction_frame, text="Argue (Chat)", command=self.start_argue, bg="#FF9800", fg="white", width=12, height=2)
        self.argue_btn.pack(side=tk.LEFT, padx=5)

    def start_argue(self):
        self.interaction_frame.pack_forget()
        
        # Create Chat UI
        self.chat_frame = tk.Frame(self.root)
        self.chat_frame.pack(pady=5, fill=tk.BOTH, expand=True)
        
        self.chat_display = scrolledtext.ScrolledText(self.chat_frame, height=8, width=60, state=tk.DISABLED)
        self.chat_display.pack(pady=5, padx=20)
        
        # Chat input frame
        input_frame = tk.Frame(self.chat_frame)
        input_frame.pack(pady=5, padx=20)
        
        self.chat_input = tk.Entry(input_frame, width=40)
        self.chat_input.pack(side=tk.LEFT)
        self.chat_input.bind("<Return>", lambda e: self.send_chat())
        
        self.chat_voice_btn = tk.Button(input_frame, text="🎤", command=self.listen_and_transcribe_chat,
                                     bg="#FF5722", fg="white", width=3, height=1)
        self.chat_voice_btn.pack(side=tk.LEFT, padx=(5, 0))
        
        self.send_btn = tk.Button(input_frame, text="Send", command=self.send_chat, bg="#4CAF50", fg="white", width=8, height=1)
        self.send_btn.pack(side=tk.LEFT, padx=(5, 0))
        
        self.done_btn = tk.Button(self.root, text="Done", command=self.finish, bg="#4CAF50", fg="white", width=10, height=2)
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
