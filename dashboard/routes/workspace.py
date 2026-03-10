import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.config import Configuration

router = APIRouter()

class FileContent(BaseModel):
    content: str
    
class FileLocation(BaseModel):
    repo_name: str
    folder: str
    filename: str

def get_repos_dir() -> Path:
    config = Configuration.load()
    return Path(config.repositories_dir).resolve()

@router.get("/repos")
async def list_repositories():
    repos_dir = get_repos_dir()
    if not repos_dir.exists():
        return []
    
    repos = []
    for item in repos_dir.iterdir():
        if item.is_dir() and (item / ".git").exists():
            repos.append(item.name)
    return sorted(repos)

@router.get("/repos/{repo_name}/files")
async def list_workspace_files(repo_name: str):
    repos_dir = get_repos_dir()
    repo_path = repos_dir / repo_name
    
    if not repo_path.exists() or not repo_path.is_dir():
        raise HTTPException(status_code=404, detail="Repository not found")
        
    result = {
        ".context": [],
        ".agents": []
    }
    
    for folder in [".context", ".agents"]:
        folder_path = repo_path / folder
        if folder_path.exists() and folder_path.is_dir():
            result[folder] = sorted([f.name for f in folder_path.iterdir() if f.is_file()])
            
    return result

@router.get("/repos/{repo_name}/file")
async def read_workspace_file(repo_name: str, folder: str, filename: str):
    repos_dir = get_repos_dir()
    if folder not in [".context", ".agents"]:
        raise HTTPException(status_code=400, detail="Invalid folder")
        
    file_path = repos_dir / repo_name / folder / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
        
    try:
        return {"content": file_path.read_text(encoding="utf-8")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/repos/{repo_name}/file")
async def save_workspace_file(repo_name: str, folder: str, filename: str, file_data: FileContent):
    repos_dir = get_repos_dir()
    if folder not in [".context", ".agents"]:
        raise HTTPException(status_code=400, detail="Invalid folder")
        
    folder_path = repos_dir / repo_name / folder
    folder_path.mkdir(parents=True, exist_ok=True)
    
    file_path = folder_path / filename
    try:
        file_path.write_text(file_data.content, encoding="utf-8")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/repos/{repo_name}/file")
async def delete_workspace_file(repo_name: str, folder: str, filename: str):
    repos_dir = get_repos_dir()
    if folder not in [".context", ".agents"]:
        raise HTTPException(status_code=400, detail="Invalid folder")
        
    file_path = repos_dir / repo_name / folder / filename
    if file_path.exists():
        try:
            file_path.unlink()
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return {"status": "success"}
