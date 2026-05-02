import os
import google.genai as genai
from google.genai import types
from dotenv import load_dotenv
import json
import re

load_dotenv()

# Initialize the client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def get_gemini_json(prompt):
    try:
        res = client.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt
        )
        text = getattr(res, "text", "") or ""

        # Try direct JSON parse
        try:
            return json.loads(text)
        except Exception:
            pass

        # if that doesnt workTry fenced code block extraction (```json or ```)
        m = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.S | re.I)
        if m:
            candidate = m.group(1)
            try:
                return json.loads(candidate)
            except Exception:
                pass

        # try locate the first JSON object/array by brace/bracket matching
        def find_json_by_braces(s: str):
            for i, ch in enumerate(s):
                if ch in "[{":
                    open_ch = ch
                    close_ch = "]" if ch == "[" else "}"
                    depth = 1
                    j = i + 1
                    while j < len(s) and depth > 0:
                        if s[j] == open_ch:
                            depth += 1
                        elif s[j] == close_ch:
                            depth -= 1
                        j += 1
                    if depth == 0:
                        return s[i:j]
            return None

        candidate = find_json_by_braces(text)
        if candidate:
            try:
                return json.loads(candidate)
            except Exception:
                pass

        matches = re.findall(r"\{.*?\}|\[.*?\]", text, re.S)
        # prefer longer matches
        matches.sort(key=len, reverse=True)
        for m2 in matches:
            try:
                return json.loads(m2)
            except Exception:
                continue

        # If none of the above worked, raise to caller so they can handle it
        raise ValueError("Could not parse JSON from Gemini response")
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
    
    # Format chat history into a single string and prepend system instruction
    try:
        if isinstance(chat_history, list):
            parts = []
            for entry in chat_history:
                role = entry.get('role', 'user')
                # entry may have 'parts' which is a list of {'text': ...}
                text = ''
                if isinstance(entry.get('parts'), list):
                    text = ' '.join(p.get('text', '') for p in entry.get('parts'))
                else:
                    text = str(entry)
                parts.append(f"[{role}] {text}")
            history_text = "\n".join(parts)
        else:
            history_text = str(chat_history)

        full_prompt = prompt + "\n\nChat history:\n" + history_text
        res = client.models.generate_content(
            model='gemini-flash-latest',
            contents=full_prompt
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
    
    Your task is to weave these disjointed answers into one cohesive, personalized, and well-structured academic summary or document. 
    Remove any conversational tone, 'I think', or references to the prompts themselves. 
    The output should be a personalized, polished piece of writing that maximizes the use of the student's own words while covering their weaknesses without mentioning it.
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
