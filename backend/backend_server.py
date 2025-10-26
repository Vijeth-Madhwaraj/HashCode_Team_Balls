from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import os, json
from llama_action_planner import (
    generate_task_plan,
    modify_task_plan,
    execute_task,
    save_stepwise_text,
    json_to_stepwise_text,
)

app = FastAPI()

TASKS_DIR = "tasks"
os.makedirs(TASKS_DIR, exist_ok=True)

# Allow frontend local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# -----------------------------
# List all tasks
# -----------------------------
@app.get("/list-tasks")
async def list_tasks():
    tasks = [f.replace(".json", "") for f in os.listdir(TASKS_DIR) if f.endswith(".json")]
    return {"tasks": tasks}

# -----------------------------
# Generate/Add Task
# -----------------------------
@app.post("/generate-task")
async def add_task(request: Request):
    data = await request.json()
    instr = data.get("instruction")
    if not instr:
        return {"status": "error", "message": "instruction required"}
    plan = generate_task_plan(instr)
    return plan

# -----------------------------
# Modify Task
# -----------------------------
@app.post("/modify-task")
async def modify_task(request: Request):
    data = await request.json()
    task_name = data.get("task")
    mod_instr = data.get("modification")
    if not task_name or not mod_instr:
        return {"status": "error", "message": "task & modification required"}
    updated = modify_task_plan(task_name, mod_instr)
    return updated

# -----------------------------
# Execute Task (original)
# -----------------------------
@app.post("/execute-task")
async def exec_task(request: Request):
    data = await request.json()
    task_name = data.get("task")
    if not task_name:
        return {"status": "error", "message": "task required"}
    result = execute_task(task_name)
    return result

# -----------------------------
# Developer: Get JSON + stepwise text
# -----------------------------
@app.get("/developer-task/{task_name}")
async def dev_task(task_name: str):
    json_path = os.path.join(TASKS_DIR, f"{task_name}.json")
    readable_path = os.path.join(TASKS_DIR, f"{task_name}_steps.txt")
    if not os.path.exists(json_path):
        return {"status": "error", "message": "task not found"}

    with open(json_path, "r", encoding="utf-8") as f:
        plan = json.load(f)

    readable_text = ""
    if os.path.exists(readable_path):
        with open(readable_path, "r", encoding="utf-8") as f:
            readable_text = f.read()

    return {"plan": plan, "readable_text": readable_text}

# -----------------------------
# Developer: Execute edited JSON
# -----------------------------
@app.post("/execute-json")
async def execute_json(request: Request):
    data = await request.json()
    task_name = data.get("task")
    steps = data.get("steps")
    if not task_name or not steps:
        return {"status": "error", "message": "task or steps missing"}

    json_path = os.path.join(TASKS_DIR, f"{task_name}.json")
    plan = {"task": task_name, "steps": steps}

    # Save JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)

    # Save stepwise text
    step_text = json_to_stepwise_text(plan)
    save_stepwise_text(task_name, step_text)

    return {"status": "success", "message": f"{task_name} saved and executed"}
