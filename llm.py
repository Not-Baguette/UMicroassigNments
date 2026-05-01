import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
import json

load_dotenv()

# Initialize the client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def get_gemini_json(prompt):
    try:
        res = client.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt,
            config=types.GenerateContentConfig(
                res_mime_type="application/json"
            )
        )
        # res.text might contain markdown code blocks if not careful, 
        # but with res_mime_type="application/json", it should be clean.
        return json.loads(res.text)
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return None

def decompose_assignment(title, description):
    prompt = f"""
    You are an expert academic project manager. 
    Take the following material titled '{title}' and its content:
    ---
    {description}
    ---
    Break this content into 3 to 7 small, bite-sized 'micro-tasks' or study questions. 
    Each task should be a specific prompt that a student can answer in a few sentences or a paragraph.
    The goal is that by answering all prompts, the student will have processed and summarized the entire material.

    Return JSON format:
    {{
        "tasks": [
            "Specific prompt 1...",
            "Specific prompt 2...",
            ...
        ]
    }}
    """
    return get_gemini_json(prompt)

def get_feedback(task, answer):
    prompt = f"""
    You are a supportive academic tutor. 
    The student was given this micro-task: "{task}"
    Their answer was: "{answer}"
    
    Provide brief, constructive feedback. If the answer is correct or on the right track, acknowledge it. 
    If there are gaps, gently point them out. 
    Keep it concise (2-3 sentences).
    """
    try:
        res = client.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt
        )
        return res.text
    except Exception as e:
        print(f"Error getting feedback: {e}")
        return "Good job! Keep going."

def chat_with_agent(task, original_answer, chat_history):
    # chat_history is a list of {"role": "user/model", "parts": [{"text": "..."}]}
    prompt = f"""
    You are a supportive academic tutor. 
    The original task was: "{task}"
    The student's initial answer was: "{original_answer}"
    
    The student wants to 'argue' or discuss their answer further. 
    Be encouraging but maintain academic rigor. 
    Discuss the topic with them based on the provided history.
    """
    
    # We'll use the chat session feature of the SDK
    try:
        res = client.models.generate_content(
            model='gemini-flash-latest',
            contents=chat_history,
            config=types.GenerateContentConfig(system_instruction=prompt)
        )
        return res.text
    except Exception as e:
        print(f"Error in chat: {e}")
        return "I'm having trouble connecting right now, but I hear your point!"

def compile_assignment(title, completed_tasks):
    tasks_text = json.dumps(completed_tasks, indent=2)
    prompt = f"""
    You are an academic editor. 
    Below are a series of prompts and the student's answers for the material titled '{title}'.
    
    Prompts and Answers:
    {tasks_text}
    
    Your task is to weave these disjointed answers into one cohesive, formal, and well-structured academic summary or document. 
    Remove any conversational tone, 'I think', or references to the prompts themselves. 
    The output should look like a finished essay or report.
    Use appropriate headings if necessary.
    """
    try:
        res = client.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt
        )
        return res.text
    except Exception as e:
        print(f"Error compiling assignment: {e}")
        return "Failed to compile assignment."
