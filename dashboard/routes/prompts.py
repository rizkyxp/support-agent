from fastapi import APIRouter
from pydantic import BaseModel
from dashboard.database import get_db

router = APIRouter()

class PromptTemplate(BaseModel):
    id: str
    template_text: str

@router.get("/")
async def get_all_prompts():
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, template_text FROM prompt_templates")
            results = {row['id']: row['template_text'] for row in cursor.fetchall()}
            return results
    except Exception:
        return {}

@router.post("/")
async def save_prompt(data: PromptTemplate):
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO prompt_templates (id, template_text) VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET template_text=excluded.template_text",
                (data.id, data.template_text)
            )
            conn.commit()
            return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
