from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import json
import os

from prep_flow import run_prep_session, save_output
from database import init_db, get_weak_areas, get_kb_snapshot

# Initialize app and database
app = FastAPI(title="Adaptive Document Preparation System")
init_db()


# ─── Request Models ───

class PrepRequest(BaseModel):
    section_ids: List[str]
    num_questions: int = 5
    simulate: bool = True


class ScenarioBRequest(BaseModel):
    num_questions: int = 5


# ─── Routes ───

@app.get("/")
def root():
    return {"message": "Adaptive Document Preparation System is running!"}


@app.post("/prep/start")
def start_prep_session(request: PrepRequest):
    """
    Start a prep session for given sections.
    If simulate=True, answers are auto-simulated.
    """
    try:
        result = run_prep_session(
            section_ids=request.section_ids,
            num_questions=request.num_questions,
            simulate=request.simulate
        )
        return {
            "session_id": result["session_id"],
            "section_ids": result["section_ids"],
            "score": result["score"],
            "total_questions": len(result["questions"]),
            "questions": result["questions"],
            "kb_snapshot": result["kb_snapshot"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/prep/weak-areas/{section_ids}")
def get_weak_areas_endpoint(section_ids: str):
    """
    Get weak areas for given section IDs.
    section_ids should be comma separated e.g. "5,8"
    """
    try:
        ids = section_ids.split(",")
        weak = get_weak_areas(ids)
        return {"section_ids": ids, "weak_areas": weak}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/prep/snapshot/{session_id}")
def get_snapshot(session_id: int):
    """
    Get KB snapshot for a given session.
    """
    try:
        snapshot = get_kb_snapshot(session_id)
        return snapshot
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scenario-b")
def run_scenario_b(request: ScenarioBRequest):
    """
    Runs the full Scenario B evaluation:
    Iter 1: sections 5, 8
    Iter 2: sections 6, 8, 9
    Iter 3: section 8
    Saves outputs to outputs/ folder.
    """
    try:
        results = {}

        iterations = [
            {"iter": 1, "sections": ["5", "8"],    "dir": "outputs/scenario_b_iter1"},
            {"iter": 2, "sections": ["6", "8", "9"],"dir": "outputs/scenario_b_iter2"},
            {"iter": 3, "sections": ["8"],          "dir": "outputs/scenario_b_iter3"},
        ]

        for item in iterations:
            print(f"\n{'='*50}")
            print(f"Running Scenario B - Iteration {item['iter']}")
            print(f"{'='*50}")

            result = run_prep_session(
                section_ids=item["sections"],
                num_questions=request.num_questions,
                simulate=True
            )

            # Save outputs
            save_output(result, item["dir"])
            results[f"iter_{item['iter']}"] = {
                "session_id": result["session_id"],
                "section_ids": result["section_ids"],
                "score": result["score"]
            }

        return {
            "message": "Scenario B completed successfully!",
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))