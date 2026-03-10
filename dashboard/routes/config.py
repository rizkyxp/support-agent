from fastapi import APIRouter
from pydantic import BaseModel
from dashboard.database import get_db

router = APIRouter()

class ConfigUpdate(BaseModel):
    key: str
    value: str

class BatchConfigUpdate(BaseModel):
    configs: list[ConfigUpdate]

@router.get("/")
async def get_all_configs():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM global_config")
        results = {row['key']: row['value'] for row in cursor.fetchall()}
        return results

@router.post("/")
async def save_configs(data: BatchConfigUpdate):
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            for config in data.configs:
                cursor.execute(
                    "INSERT INTO global_config (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (config.key, config.value)
                )
            conn.commit()
            return {"status": "success", "message": "Configurations saved successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
