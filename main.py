from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import json
import os
import logging

from prep_flow import run_prep_session, save_output
from database import init_db, get_weak_areas, get_kb_snapshot

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize app and database
app = FastAPI(title="Adaptive Document Preparation System")

@app.on_event("startup")
def startup_event():
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


# ─── Request Models ───

class PrepRequest(BaseModel):
    section_ids: List[str]
    num_questions: int = 5
    simulate: bool = True


class ScenarioBRequest(BaseModel):
    num_questions: int = 5


# ─── Validation Helper ───

VALID_SECTIONS = [str(i) for i in range(1, 11)]  # "1" to "10"

def validate_sections(section_ids: List[str]):
    invalid = [s for s in section_ids if s not in VALID_SECTIONS]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid section IDs: {invalid}. Valid sections are 1-10."
        )
    if len(section_ids) == 0:
        raise HTTPException(
            status_code=400,
            detail="At least one section ID is required."
        )


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
    # Validate section IDs
    validate_sections(request.section_ids)

    # Validate num_questions
    if request.num_questions < 1 or request.num_questions > 20:
        raise HTTPException(
            status_code=400,
            detail="num_questions must be between 1 and 20."
        )

    try:
        logger.info(f"Starting prep session for sections: {request.section_ids}")
        result = run_prep_session(
            section_ids=request.section_ids,
            num_questions=request.num_questions,
            simulate=request.simulate
        )

        if not result:
            raise HTTPException(
                status_code=500,
                detail="Session failed — no questions were generated. Check your PDF and LLM connection."
            )

        logger.info(f"Session {result['session_id']} completed successfully")
        return {
            "session_id": result["session_id"],
            "section_ids": result["section_ids"],
            "score": result["score"],
            "total_questions": len(result["questions"]),
            "questions": result["questions"],
            "kb_snapshot": result["kb_snapshot"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prep session failed: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get("/prep/weak-areas/{section_ids}")
def get_weak_areas_endpoint(section_ids: str):
    """
    Get weak areas for given section IDs.
    section_ids should be comma separated e.g. "5,8"
    """
    try:
        ids = section_ids.split(",")
        validate_sections(ids)
        weak = get_weak_areas(ids)
        logger.info(f"Retrieved {len(weak)} weak areas for sections {ids}")
        return {"section_ids": ids, "weak_areas": weak}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get weak areas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/prep/snapshot/{session_id}")
def get_snapshot(session_id: int):
    """
    Get KB snapshot for a given session.
    """
    if session_id < 1:
        raise HTTPException(
            status_code=400,
            detail="session_id must be a positive integer."
        )
    try:
        snapshot = get_kb_snapshot(session_id)
        if not snapshot:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found."
            )
        logger.info(f"Retrieved snapshot for session {session_id}")
        return snapshot
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get snapshot: {e}")
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
    if request.num_questions < 1 or request.num_questions > 20:
        raise HTTPException(
            status_code=400,
            detail="num_questions must be between 1 and 20."
        )

    try:
        results = {}

        iterations = [
            {"iter": 1, "sections": ["5", "8"],     "dir": "outputs/scenario_b_iter1"},
            {"iter": 2, "sections": ["6", "8", "9"],"dir": "outputs/scenario_b_iter2"},
            {"iter": 3, "sections": ["8"],           "dir": "outputs/scenario_b_iter3"},
        ]

        for item in iterations:
            logger.info(f"Running Scenario B iteration {item['iter']} for sections {item['sections']}")

            result = run_prep_session(
                section_ids=item["sections"],
                num_questions=request.num_questions,
                simulate=True
            )

            if not result:
                raise HTTPException(
                    status_code=500,
                    detail=f"Iteration {item['iter']} failed — no questions generated."
                )

            # Save outputs
            save_output(result, item["dir"])
            logger.info(f"Iteration {item['iter']} completed. Score: {result['score']}")

            results[f"iter_{item['iter']}"] = {
                "session_id": result["session_id"],
                "section_ids": result["section_ids"],
                "score": result["score"]
            }

        logger.info("Scenario B completed successfully")
        return {
            "message": "Scenario B completed successfully!",
            "results": results
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scenario B failed: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")