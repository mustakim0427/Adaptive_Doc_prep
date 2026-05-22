import json
import random
from pdf_parser import extract_sections, get_section_text
from database import (
    create_session,
    save_questions,
    save_answers,
    get_weak_areas,
    get_kb_snapshot
)
from llm import generate_mcqs

# Load sections once when module is imported
SECTIONS = extract_sections()


def run_prep_session(section_ids: list, num_questions: int = 5, simulate: bool = True) -> dict:
    """
    Runs a full prep session:
    1. Check KB for prior history (weak areas)
    2. Generate MCQs using LLM
    3. Simulate or collect user answers
    4. Score the session
    5. Save everything to KB
    6. Return questions + kb snapshot

    If simulate=True, answers are auto-generated (mix of right/wrong)
    """

    print(f"\n{'='*50}")
    print(f"Starting prep session for sections: {section_ids}")
    print(f"{'='*50}")

    # ─── STEP 1: Check KB for prior history ───
    print("\n[Step 1] Checking knowledge base for prior history...")
    weak_areas = get_weak_areas(section_ids)

    if weak_areas:
        print(f"Found {len(weak_areas)} weak areas from previous sessions:")
        for w in weak_areas:
            print(f"  - {w[:80]}...")
    else:
        print("No prior history found. This is a fresh session.")

    # ─── STEP 2: Generate MCQs ───
    print(f"\n[Step 2] Generating {num_questions} MCQs per section using LLM...")
    all_questions = []

    for sid in section_ids:
        print(f"  Generating questions for section {sid}...")
        text = get_section_text([sid], SECTIONS)

        if not text:
            print(f"  Section {sid} not found in PDF, skipping.")
            continue

        questions = generate_mcqs(
            section_text=text,
            section_ids=[sid],
            num_questions=num_questions,
            weak_areas=weak_areas
        )

        for q in questions:
            q["section_id"] = sid

        all_questions.extend(questions)
        print(f"  Generated {len(questions)} questions for section {sid}")

    if not all_questions:
        print("No questions generated. Exiting.")
        return {}

    print(f"\nTotal questions generated: {len(all_questions)}")

    # ─── STEP 3: Create session and save questions ───
    print("\n[Step 3] Saving session and questions to KB...")
    session_id = create_session(section_ids)
    save_questions(session_id, all_questions)
    print(f"Session {session_id} created and questions saved.")

    # ─── STEP 4: Simulate or collect answers ───
    print("\n[Step 4] Collecting answers...")
    answers = {}

    # We need question IDs from DB
    # Since we just inserted them, get them by session
    import sqlite3
    from database import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, correct_answer FROM questions WHERE session_id = ?", (session_id,))
    rows = cursor.fetchall()
    conn.close()

    if simulate:
        print("Simulating user answers (mix of correct and incorrect)...")
        for row in rows:
            qid = row["id"]
            correct = row["correct_answer"]
            options = ["A", "B", "C", "D"]

            # Simulate: 60% chance of correct answer
            if random.random() < 0.6:
                answers[qid] = correct
            else:
                wrong_options = [o for o in options if o != correct]
                answers[qid] = random.choice(wrong_options)
    else:
        # Real user input via CLI
        for i, (row, q) in enumerate(zip(rows, all_questions), 1):
            print(f"\nQ{i}: {q['question_text']}")
            print(f"  A: {q['option_a']}")
            print(f"  B: {q['option_b']}")
            print(f"  C: {q['option_c']}")
            print(f"  D: {q['option_d']}")
            while True:
                ans = input("Your answer (A/B/C/D): ").strip().upper()
                if ans in ["A", "B", "C", "D"]:
                    answers[row["id"]] = ans
                    break
                print("Invalid input. Please enter A, B, C or D.")

    # ─── STEP 5: Score and save answers ───
    print("\n[Step 5] Scoring session...")
    score = save_answers(session_id, answers)
    print(f"Results: {score['correct']} correct, {score['wrong']} wrong out of {len(all_questions)}")

    # Show wrong answers with explanations
    print("\nReview:")
    for row, q in zip(rows, all_questions):
        qid = row["id"]
        user_ans = answers.get(qid, "?")
        correct = row["correct_answer"]
        if user_ans != correct:
            print(f"\n❌ WRONG: {q['question_text']}")
            print(f"   Your answer: {user_ans}")
            print(f"   Correct answer: {correct}")
            print(f"   Explanation: {q['explanation']}")
        else:
            print(f"✅ CORRECT: {q['question_text'][:60]}...")

    # ─── STEP 6: Get KB snapshot ───
    print("\n[Step 6] Saving KB snapshot...")
    snapshot = get_kb_snapshot(session_id)

    return {
        "session_id": session_id,
        "section_ids": section_ids,
        "questions": all_questions,
        "score": score,
        "kb_snapshot": snapshot
    }


def save_output(result: dict, output_dir: str):
    """
    Saves questions and kb_snapshot as JSON files
    into the given output directory.
    """
    import os
    os.makedirs(output_dir, exist_ok=True)

    # Save questions
    questions_path = os.path.join(output_dir, "questions.json")
    with open(questions_path, "w", encoding="utf-8") as f:
        json.dump(result["questions"], f, indent=2, ensure_ascii=False)
    print(f"Questions saved to {questions_path}")

    # Save KB snapshot
    snapshot_path = os.path.join(output_dir, "kb_snapshot.json")
    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(result["kb_snapshot"], f, indent=2, ensure_ascii=False)
    print(f"KB snapshot saved to {snapshot_path}")


# Quick test
if __name__ == "__main__":
    result = run_prep_session(
        section_ids=["1", "2"],
        num_questions=3,
        simulate=True
    )
    print(f"\nSession {result['session_id']} completed!")
    print(f"Score: {result['score']}")