# Adaptive Document Preparation System

An AI-powered study assistant that generates adaptive MCQ questions from a PDF document, tracks user performance, and focuses on weak areas in subsequent sessions.

---

## Project Overview

This system:
- Ingests a multi-section PDF document
- Allows users to select sections to study
- Generates MCQ questions using an LLM (Groq)
- Scores user answers and explains wrong answers
- Persists session history in a Knowledge Base (SQLite)
- Adapts future questions based on past weak areas

---

## Tech Stack & Reasoning

| Component | Choice | Reason |
|---|---|---|
| Backend | FastAPI (Python) | Modern, fast, auto-generates API docs, stays in Python ecosystem |
| LLM | Groq (llama-3.3-70b-versatile) | Free tier, extremely fast, no GPU needed |
| PDF Parsing | PyMuPDF (fitz) | Fast, reliable, lightweight, direct library |
| Database | SQLite | Zero setup, file-based, perfect for local project |
| Orchestration | Raw API calls | Simple and direct, no unnecessary abstraction |
| UI | Streamlit | Simple, fast to build, interactive web interface |

---

## Project Structure

```
adaptive_doc_prep/
├── data/
│   └── SLATEFALL_DOSSIER.pdf
├── outputs/
│   ├── scenario_b_iter1/
│   ├── scenario_b_iter2/
│   └── scenario_b_iter3/
├── pdf_parser.py
├── database.py
├── llm.py
├── prep_flow.py
├── main.py
├── app.py
├── Dockerfile
├── docker-compose.yml
├── .env
├── .gitignore
└── README.md
```

---

## Prerequisites

- Python 3.10+
- A free Groq API key from https://console.groq.com
- Docker Desktop (optional, for running with Docker)

---

## Setup — Add Your API Key

Create a `.env` file in the project root:
```
GROQ_API_KEY=your_groq_api_key_here
```

## Setup — Add The PDF

Place `SLATEFALL_DOSSIER.pdf` inside the `data/` folder.

---

## Option 1 — Run With Docker (Recommended)

### 1. Make sure Docker Desktop is running
Download from https://www.docker.com/products/docker-desktop if needed.
Wait until you see "Engine Running" in Docker Desktop.

### 2. Create an empty database file
```bash
New-Item -Path "knowledge_base.db" -ItemType File -Force
```

### 3. Start the server
```bash
docker-compose up --build
```

Wait for:
```
app-1  | INFO:     Application startup complete.
```

Your API is now running at `http://127.0.0.1:8000` ✅

### 4. To stop Docker
Press `Ctrl+C` in the terminal.

---

## Option 2 — Run Without Docker (Manual Setup)

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/adaptive-doc-prep.git
cd adaptive-doc-prep
```

### 2. Create and activate virtual environment
```bash
python -m venv venv
```
Windows:
```bash
venv\Scripts\activate
```
Mac/Linux:
```bash
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install fastapi uvicorn pymupdf groq python-dotenv requests streamlit
```

### 4. Start the server
```bash
uvicorn main:app --reload
```

Your API is now running at `http://127.0.0.1:8000` ✅

---

## Using The Streamlit UI (Optional)

Once the server is running (via Docker or uvicorn), open a new terminal and run:

```bash
streamlit run app.py
```

This opens a visual interface at `http://localhost:8501` where you can:
- Select sections to study
- Set number of questions
- Start a study session with one click
- View questions, scores and explanations
- Check your weak areas
- Run Scenario B with one click

---

## Using The API Directly (Without UI)

Once the server is running, visit:
```
http://127.0.0.1:8000/docs
```
This gives you an interactive API explorer to test all endpoints.

---

## Running Evaluation Scenarios

### Fresh Start (Required Before Running Scenarios)

To ensure a clean run with no prior history:

**With Docker:**
```bash
New-Item -Path "knowledge_base.db" -ItemType File -Force
docker-compose up --build
```

**Without Docker:**
```bash
del knowledge_base.db
uvicorn main:app --reload
```

---

### Scenario A — Cold start prep over two sections

Via UI: Select sections 3 and 7 → click Start Study Session

Via terminal:
```bash
python -c "import requests; response = requests.post('http://127.0.0.1:8000/prep/start', json={'section_ids': ['3', '7'], 'num_questions': 5, 'simulate': True}); print(response.json())"
```

### Scenario B — Three consecutive iterations

Via UI: Click ▶️ Run Scenario B button

Via terminal:
```bash
python -c "import requests; response = requests.post('http://127.0.0.1:8000/scenario-b', json={'num_questions': 5}); print(response.json())"
```

Outputs saved to:
```
outputs/scenario_b_iter1/   → questions.json + kb_snapshot.json
outputs/scenario_b_iter2/   → questions.json + kb_snapshot.json
outputs/scenario_b_iter3/   → questions.json + kb_snapshot.json
```

---

## Knowledge Base Schema

### Table: `sessions`
| Column | Type | Description |
|---|---|---|
| id | INTEGER | Primary key |
| section_ids | TEXT | Comma separated section IDs e.g. "5,8" |
| created_at | TEXT | ISO timestamp |
| total_questions | INTEGER | Total questions in session |
| correct_count | INTEGER | Number of correct answers |
| wrong_count | INTEGER | Number of wrong answers |

### Table: `questions`
| Column | Type | Description |
|---|---|---|
| id | INTEGER | Primary key |
| session_id | INTEGER | Foreign key to sessions |
| section_id | TEXT | Which section this question is from |
| question_text | TEXT | The MCQ question |
| option_a/b/c/d | TEXT | Four answer choices |
| correct_answer | TEXT | Correct option (A/B/C/D) |
| explanation | TEXT | Why the answer is correct |
| user_answer | TEXT | What the user answered |
| is_correct | INTEGER | 1 = correct, 0 = wrong |

---

## Adaptive Logic

The system adapts questions across sessions by:

1. At the start of each session, `get_weak_areas()` queries the KB for questions answered incorrectly in previous sessions for the same sections.
2. These weak areas are injected into the LLM prompt as context.
3. The LLM generates new questions with extra focus on those weak topics.
4. Each subsequent session over the same sections becomes more targeted.

---

## Known Limitations

- LLM outputs are non-deterministic due to temperature settings.
- Section detection relies on the pattern `Section N.` in the PDF.
- Simulated answers use a 60% correct rate for demonstration.
- Single user only — no authentication system.

---

## Assumptions

- The PDF is machine-readable (no scanned images).
- Section numbering follows the pattern `Section 1.` through `Section 10.`
- Groq free tier is used — rate limits may apply for very large PDFs.
