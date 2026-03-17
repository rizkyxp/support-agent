import asyncio
import os
import sys
import subprocess
from collections import deque
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

router = APIRouter()

# Global state for the runner
agent_process = None
log_buffer = deque(maxlen=1000)  # Keep last 1000 lines
active_connections: list[WebSocket] = []

class RunRequest(BaseModel):
    interval: int = 0
    process_prs: bool = True
    process_issues: bool = True
    log_level: str = "INFO"
    auto_request_review: bool = True

@router.post("/start")
async def start_agent(req: RunRequest):
    global agent_process, log_buffer
    
    if agent_process is not None and agent_process.poll() is None:
        return {"status": "error", "message": "Agent is already running"}
        
    cmd = [sys.executable, "-m", "src.main"]
    
    # Map request to args
    cmd.extend(["--interval", str(req.interval)])
    
    if req.process_prs and req.process_issues:
        pass # default is both
    elif req.process_prs:
        cmd.append("--pr")
    elif req.process_issues:
        cmd.append("--issue")
        
    if not req.auto_request_review:
        cmd.append("--no-auto-request-review")
        
    cmd.extend(["--log-level", req.log_level])
    
    log_buffer.clear()
    broadcast_log(f"Starting agent with command: {' '.join(cmd)}\n")
    
    # Include dashboard DB hint in environment
    env = os.environ.copy()
    
    try:
        agent_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        )
        
        # Start background task to read output
        asyncio.create_task(read_agent_output(agent_process))
        
        return {"status": "success", "message": "Agent started successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/stop")
async def stop_agent():
    global agent_process
    
    if agent_process is None or agent_process.poll() is not None:
        return {"status": "error", "message": "Agent is not currently running"}
        
    agent_process.terminate()
    try:
        agent_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        agent_process.kill()
        
    agent_process = None
    broadcast_log("\n--- Agent gracefully stopped by user ---\n")
    return {"status": "success", "message": "Agent stopped"}

@router.get("/status")
async def get_status():
    global agent_process
    is_running = agent_process is not None and agent_process.poll() is None
    return {
        "is_running": is_running,
        "pid": agent_process.pid if is_running else None
    }

async def read_agent_output(process):
    """Reads stdout from the agent process and broadcasts it asynchronously."""
    global log_buffer
    
    # We use run_in_executor to avoid blocking the event loop with synchronous read
    loop = asyncio.get_event_loop()
    
    def read_line():
        return process.stdout.readline()
        
    while True:
        line = await loop.run_in_executor(None, read_line)
        if not line and process.poll() is not None:
            break
            
        if line:
            log_buffer.append(line)
            # Find all active connections and send
            for connection in list(active_connections):
                try:
                    # Using asyncio.create_task to avoid blocking
                    asyncio.create_task(connection.send_text(line))
                except Exception:
                    # If send fails, we'll clean it up on the websocket endpoint
                    pass
                    
    broadcast_log("\n--- Agent process exited ---\n")

def broadcast_log(msg: str):
    """Helper to append system messages to buffer and active websockets."""
    global log_buffer
    log_buffer.append(msg)
    for connection in list(active_connections):
        try:
            asyncio.create_task(connection.send_text(msg))
        except Exception:
            pass

@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    
    # Send history
    for line in log_buffer:
        await websocket.send_text(line)
        
    try:
        while True:
            # Keep connection alive, wait for client disconnect
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)
