import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from agent import AutomationAgent, TOOL_REGISTRY
from tools.system_tools import get_system_metrics, format_system_metrics_text

app = FastAPI(title="Local AI Automation Hub", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = AutomationAgent()

# Serve static dashboard files
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
def read_root():
    return RedirectResponse(url="/static/index.html")

class ChatRequest(BaseModel):
    prompt: str
    model: Optional[str] = "llama3.2:1b"
    history: Optional[List[Dict[str, Any]]] = []

class QuickActionRequest(BaseModel):
    action_type: str
    target_param: Optional[str] = None
    model: Optional[str] = "llama3.2:1b"

class ConfirmActionRequest(BaseModel):
    tool: str
    args: Dict[str, Any]

@app.get("/api/status")
def get_status():
    metrics = get_system_metrics()
    models = agent.get_available_models()
    return {
        "status": "online",
        "system": metrics,
        "ollama_connected": True,
        "models": models
    }

@app.get("/api/models")
def list_models():
    return {"models": agent.get_available_models()}

@app.post("/api/chat")
def chat_with_agent(req: ChatRequest):
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    
    result = agent.run_agent_loop(
        prompt=req.prompt,
        history=req.history,
        model=req.model or "llama3.2:1b"
    )
    return result

@app.post("/api/quick-action")
def run_quick_action(req: QuickActionRequest):
    act = req.action_type
    param = req.target_param or ""
    
    if act == "system_health":
        prompt = "Provide a comprehensive system health summary using the system metrics tool and suggest any optimizations."
    elif act == "organize_downloads":
        downloads_path = str(Path.home() / "Downloads")
        prompt = f"Run a dry-run preview to organize loose files in my Downloads directory: '{downloads_path}'"
    elif act == "clean_temp_preview":
        temp_path = os.environ.get("TEMP", "C:\\Windows\\Temp")
        prompt = f"List the top temporary files in '{temp_path}' and check how much space can be safely cleaned."
    elif act == "scrape_url":
        if not param:
            raise HTTPException(status_code=400, detail="URL parameter required for web scraping")
        prompt = f"Fetch and summarize the core key takeaways from this webpage: {param}"
    elif act == "list_workspace":
        ws = str(Path.cwd().resolve())
        prompt = f"Inspect and summarize the structure of the workspace directory: '{ws}'"
    else:
        raise HTTPException(status_code=400, detail=f"Unknown quick action: {act}")
        
    return agent.run_agent_loop(prompt=prompt, model=req.model or "llama3.2:1b")

@app.post("/api/confirm-action")
def confirm_action(req: ConfirmActionRequest):
    fn = TOOL_REGISTRY.get(req.tool)
    if not fn:
        raise HTTPException(status_code=404, detail=f"Tool {req.tool} not found")
        
    try:
        # Pass confirmed=True if the tool accepts it
        args = dict(req.args)
        if "confirmed" in fn.__code__.co_varnames:
            args["confirmed"] = True
        elif "dry_run" in fn.__code__.co_varnames:
            args["dry_run"] = False
            
        output = fn(**args)
        return {
            "success": True,
            "tool": req.tool,
            "output": str(output)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
