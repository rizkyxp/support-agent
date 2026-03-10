from fastapi import APIRouter
from pydantic import BaseModel
from dashboard.database import get_db

router = APIRouter()

@router.get("/")
async def get_history(limit: int = 50):
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, timestamp, target_repo, target_type, target_id, status, details FROM run_history ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return results
    except Exception as e:
        return []

@router.post("/")
async def record_history(target_repo: str, target_type: str, target_id: str, status: str, details: str = ""):
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO run_history (target_repo, target_type, target_id, status, details) VALUES (?, ?, ?, ?, ?)",
                (target_repo, target_type, target_id, status, details)
            )
            conn.commit()
            return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.delete("/")
async def clear_history():
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM run_history")
            conn.commit()
            return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
