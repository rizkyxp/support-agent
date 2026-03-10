import subprocess
import sys
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class ReadinessStatus(BaseModel):
    github_cli: bool
    github_cli_msg: str
    gemini_cli: bool
    gemini_cli_msg: str
    python_deps: bool
    python_deps_msg: str
    all_ready: bool

@router.get("/status", response_model=ReadinessStatus)
async def get_readiness_status():
    """Check if all required tools and dependencies are installed and configured."""
    status = ReadinessStatus(
        github_cli=False, github_cli_msg="",
        gemini_cli=False, gemini_cli_msg="",
        python_deps=False, python_deps_msg="",
        all_ready=False
    )
    
    # 1. Check GitHub CLI
    try:
        result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            status.github_cli = True
            status.github_cli_msg = "Logged in to GitHub CLI."
        else:
            status.github_cli_msg = "GitHub CLI not logged in or not found. Please run 'gh auth login'."
    except FileNotFoundError:
        status.github_cli_msg = "GitHub CLI ('gh') is not installed or not in PATH."
    except Exception as e:
        status.github_cli_msg = f"Error checking GitHub CLI: {str(e)}"

    # 2. Check Gemini CLI Status (We check if 'gemini' exists, or 'google-gemini' exists, let's assume 'gemini')
    try:
        # Many CLIs support --version or help. We just check if it's callable.
        result = subprocess.run(["gemini", "--help"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            status.gemini_cli = True
            status.gemini_cli_msg = "Gemini CLI is installed and responsive."
        else:
            # Maybe the user didn't install the exact 'gemini' binary or it's giving an error
            status.gemini_cli_msg = "Gemini CLI returned an error. Ensure it is configured."
    except FileNotFoundError:
        status.gemini_cli_msg = "Gemini CLI ('gemini') is not installed or not in PATH."
    except Exception as e:
        status.gemini_cli_msg = f"Error checking Gemini CLI: {str(e)}"

    # 3. Check Python Dependencies
    try:
        import github
        import google.generativeai
        import git
        status.python_deps = True
        status.python_deps_msg = "All core Python dependencies are installed."
    except ImportError as e:
        status.python_deps_msg = f"Missing Python dependency: {str(e)}. Run 'pip install -r requirements.txt'."

    # 4. Overall Readiness
    status.all_ready = status.github_cli and status.python_deps  # Gemini CLI might be optional depending on config, but UI can show warning. We'll require it for now based on doc.md.
    if config_requires_gemini_cli():
        status.all_ready = status.all_ready and status.gemini_cli
    else:
        status.all_ready = status.github_cli and status.python_deps

    return status

def config_requires_gemini_cli() -> bool:
    """Check global configuration to see if Gemini CLI is preferred over API."""
    import os
    from dashboard.database import get_db
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM global_config WHERE key = 'USE_GEMINI_CLI'")
            row = cursor.fetchone()
            if row:
                 return str(row[0]).lower() in ("true", "1", "yes")
    except Exception:
        pass
    
    # Fallback to current env
    return os.getenv("USE_GEMINI_CLI", "false").lower() in ("true", "1", "yes")
