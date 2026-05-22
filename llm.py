import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()  # loads your API key from .env file

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_mcqs(section_text: str, section_ids: list, num_questions: int = 5, weak_areas: list = []) -> list:
    """
    Sends section text to Groq LLM and gets back MCQ questions.
    If weak_areas is provided, LLM will focus on those topics.
    Returns a list of question dicts.
    """

    # Build adaptive context if weak areas exist
    if weak_areas:
        adaptive_note = f"""
The user has studied these sections before and struggled with these topics:
{chr(10).join(f'- {w}' for w in weak_areas)}

Please focus MORE questions on these weak areas while still covering other topics.
Also avoid repeating these exact questions.
"""
    else:
        adaptive_note = "This is the user's first time studying these sections."

    prompt = f"""
You are a study assistant. Your job is to generate multiple choice questions (MCQs) from the study material below.

{adaptive_note}

Study Material:
{section_text[:6000]}

Generate exactly {num_questions} MCQ questions based on this material.

Rules:
- Each question must have exactly 4 options: A, B, C, D
- Only one option is correct
- Include a brief explanation for the correct answer
- Questions should test understanding, not just memory
- Return ONLY a valid JSON array, no extra text, no markdown

Return this exact format:
[
  {{
    "section_id": "1",
    "question_text": "Your question here?",
    "option_a": "First option",
    "option_b": "Second option",
    "option_c": "Third option",
    "option_d": "Fourth option",
    "correct_answer": "A",
    "explanation": "Brief explanation of why A is correct"
  }}
]
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    raw = response.choices[0].message.content.strip()

    # Clean up response in case LLM adds markdown
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        questions = json.loads(raw)
        # Make sure section_id is set correctly
        for q in questions:
            q["section_id"] = section_ids[0] if section_ids else "1"
        return questions
    except json.JSONDecodeError:
        print("LLM returned invalid JSON. Raw response:")
        print(raw)
        return []


# Quick test
if __name__ == "__main__":
    from pdf_parser import extract_sections, get_section_text

    print("Extracting sections from PDF...")
    sections = extract_sections()

    print("Getting text for section 1...")
    text = get_section_text(["1"], sections)

    print("Sending to Groq LLM...")
    questions = generate_mcqs(text, ["1"], num_questions=3)

    if questions:
        print(f"\nGenerated {len(questions)} questions:\n")
        for i, q in enumerate(questions, 1):
            print(f"Q{i}: {q['question_text']}")
            print(f"  A: {q['option_a']}")
            print(f"  B: {q['option_b']}")
            print(f"  C: {q['option_c']}")
            print(f"  D: {q['option_d']}")
            print(f"  Correct: {q['correct_answer']}")
            print(f"  Explanation: {q['explanation']}")
            print()
    else:
        print("No questions generated.")