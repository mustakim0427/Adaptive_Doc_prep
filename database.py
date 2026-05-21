import sqlite3
import json
from datetime import datetime

DB_PATH = "knowledge_base.db"

def get_connection():
    """Create and return a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    return conn


def init_db():
    """
    Create all tables if they don't exist yet.
    Run this once at the start of the app.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Table 1: Sessions
    # Each time a user studies sections, that's one session
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_ids TEXT NOT NULL,        -- e.g. "5,8"
            created_at TEXT NOT NULL,
            total_questions INTEGER DEFAULT 0,
            correct_count INTEGER DEFAULT 0,
            wrong_count INTEGER DEFAULT 0
        )
    """)

    # Table 2: Questions
    # Each MCQ generated in a session
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            section_id TEXT NOT NULL,
            question_text TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_answer TEXT NOT NULL,     -- "A", "B", "C", or "D"
            explanation TEXT NOT NULL,
            user_answer TEXT,                 -- filled after user answers
            is_correct INTEGER DEFAULT 0,     -- 0 = wrong, 1 = correct
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)

    conn.commit()
    conn.close()
    print("Database initialized successfully!")


def create_session(section_ids: list) -> int:
    """
    Create a new session for the given section IDs.
    Returns the new session ID.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sessions (section_ids, created_at)
        VALUES (?, ?)
    """, (",".join(section_ids), datetime.now().isoformat()))
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return session_id


def save_questions(session_id: int, questions: list):
    """
    Save a list of MCQ questions to the database.
    Each question is a dict with keys:
    section_id, question_text, option_a/b/c/d, correct_answer, explanation
    """
    conn = get_connection()
    cursor = conn.cursor()
    for q in questions:
        cursor.execute("""
            INSERT INTO questions (
                session_id, section_id, question_text,
                option_a, option_b, option_c, option_d,
                correct_answer, explanation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            q["section_id"],
            q["question_text"],
            q["option_a"],
            q["option_b"],
            q["option_c"],
            q["option_d"],
            q["correct_answer"],
            q["explanation"]
        ))
    conn.commit()
    conn.close()


def save_answers(session_id: int, answers: dict):
    """
    Save user answers and update session scores.
    answers = { question_id: "A" or "B" or "C" or "D" }
    """
    conn = get_connection()
    cursor = conn.cursor()

    correct_count = 0
    wrong_count = 0

    for question_id, user_answer in answers.items():
        # Get the correct answer
        cursor.execute("SELECT correct_answer FROM questions WHERE id = ?", (question_id,))
        row = cursor.fetchone()
        if row:
            is_correct = 1 if user_answer == row["correct_answer"] else 0
            if is_correct:
                correct_count += 1
            else:
                wrong_count += 1

            # Save user answer
            cursor.execute("""
                UPDATE questions
                SET user_answer = ?, is_correct = ?
                WHERE id = ?
            """, (user_answer, is_correct, question_id))

    # Update session scores
    cursor.execute("""
        UPDATE sessions
        SET total_questions = ?, correct_count = ?, wrong_count = ?
        WHERE id = ?
    """, (correct_count + wrong_count, correct_count, wrong_count, session_id))

    conn.commit()
    conn.close()
    return {"correct": correct_count, "wrong": wrong_count}


def get_weak_areas(section_ids: list) -> list:
    """
    Look at past sessions for these sections and find
    questions that were answered WRONG more than once.
    Returns a list of question texts that are weak areas.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Build a query for any session that includes these sections
    section_filter = " OR ".join([f"section_ids LIKE '%{sid}%'" for sid in section_ids])

    cursor.execute(f"""
        SELECT q.question_text, COUNT(*) as wrong_count
        FROM questions q
        JOIN sessions s ON q.session_id = s.id
        WHERE ({section_filter})
        AND q.is_correct = 0
        AND q.user_answer IS NOT NULL
        GROUP BY q.question_text
        ORDER BY wrong_count DESC
        LIMIT 10
    """)

    rows = cursor.fetchall()
    conn.close()
    return [row["question_text"] for row in rows]


def get_kb_snapshot(session_id: int) -> dict:
    """
    Export a snapshot of the KB at the end of a session.
    Shows the top 5 most recent sessions with their questions.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Get 5 most recent sessions
    cursor.execute("""
        SELECT * FROM sessions
        ORDER BY created_at DESC
        LIMIT 5
    """)
    sessions = cursor.fetchall()

    snapshot = []
    for s in sessions:
        # Get questions for this session
        cursor.execute("""
            SELECT * FROM questions WHERE session_id = ?
        """, (s["id"],))
        questions = cursor.fetchall()

        snapshot.append({
            "session_id": s["id"],
            "section_ids": s["section_ids"],
            "created_at": s["created_at"],
            "total_questions": s["total_questions"],
            "correct_count": s["correct_count"],
            "wrong_count": s["wrong_count"],
            "questions": [
                {
                    "id": q["id"],
                    "section_id": q["section_id"],
                    "question_text": q["question_text"],
                    "correct_answer": q["correct_answer"],
                    "user_answer": q["user_answer"],
                    "is_correct": bool(q["is_correct"])
                }
                for q in questions
            ]
        })

    conn.close()
    return {"snapshot_at_session": session_id, "recent_sessions": snapshot}


# Quick test
if __name__ == "__main__":
    init_db()

    # Test: create a session
    session_id = create_session(["5", "8"])
    print(f"Created session: {session_id}")

    # Test: save a dummy question
    save_questions(session_id, [{
        "section_id": "5",
        "question_text": "What is the operational range of SLATEFALL?",
        "option_a": "10 meters",
        "option_b": "22 meters",
        "option_c": "41 meters",
        "option_d": "5 meters",
        "correct_answer": "B",
        "explanation": "The effective operational range is 22 meters."
    }])
    print("Question saved!")

    # Test: save an answer
    result = save_answers(session_id, {1: "A"})  # wrong answer
    print(f"Score: {result}")

    # Test: get weak areas
    weak = get_weak_areas(["5", "8"])
    print(f"Weak areas: {weak}")

    # Test: get snapshot
    snapshot = get_kb_snapshot(session_id)
    print(f"Snapshot: {json.dumps(snapshot, indent=2)}")