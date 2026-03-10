import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import uvicorn

from dashboard.database import init_db

# Initialize database
init_db()

app = FastAPI(
    title="Support Agent Control Panel",
    description="Zero-code management dashboard for the Support Agent"
)

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Mount Static Files (CSS, JS)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Templates Setup
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# API Routers
from dashboard.routes import setup, runner, config, prompts, workspace, history
app.include_router(setup.router, prefix="/api/setup", tags=["setup"])
app.include_router(runner.router, prefix="/api/runner", tags=["runner"])
app.include_router(config.router, prefix="/api/config", tags=["config"])
app.include_router(prompts.router, prefix="/api/prompts", tags=["prompts"])
app.include_router(workspace.router, prefix="/api/workspace", tags=["workspace"])
app.include_router(history.router, prefix="/api/history", tags=["history"])

@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    """Serve the main control panel dashboard SPA."""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "Agent Control Panel"
    })

if __name__ == "__main__":
    # Start the local development server easily
    print("Starting Control Panel on http://127.0.0.1:8000")
    uvicorn.run("dashboard.main:app", host="127.0.0.1", port=8000, reload=True)
