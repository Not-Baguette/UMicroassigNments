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
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        # response.text might contain markdown code blocks if not careful, 
        # but with response_mime_type="application/json", it should be clean.
        return json.loads(response.text)
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
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"Error compiling assignment: {e}")
        return "Failed to compile assignment."
