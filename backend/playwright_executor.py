import os
import sys
import json
import time
import re
import subprocess
from google import genai
from dotenv import load_dotenv

# ======================
# CONFIG
# ======================
TASKS_DIR = "tasks"
OUTPUT_DIR = r"C:\Users\Balaji K\OneDrive\Desktop\LLM_PlayWright-TEST4\tests"
os.makedirs(TASKS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ======================
# HELPERS
# ======================
def ai_generate(prompt: str) -> str:
    text = ""
    response_stream = client.models.generate_content_stream(
        model="gemini-2.5-pro",
        contents=prompt
    )
    for chunk in response_stream:
        if hasattr(chunk, "text") and chunk.text:
            text += chunk.text
    return text


def clean_json_response(raw_text: str) -> dict:
    text_clean = re.sub(r"(?:json)?", "", raw_text).strip()
    match = re.search(r"\{.*\}", text_clean, re.DOTALL)
    if match:
        text_clean = match.group(0)
    else:
        print("Warning: No JSON object detected, saving raw text instead")
        return {"raw_text": raw_text}

    try:
        return json.loads(text_clean)
    except json.JSONDecodeError:
        print("Warning: Failed to parse JSON, saving raw text instead")
        return {"raw_text": text_clean}


def generate_task_plan(instruction: str) -> str:
    prompt = f"""
Convert the following instruction into a structured JSON action plan for web automation.
Instruction: "{instruction}"

- Do NOT include actual usernames or passwords; use placeholders like '${{USERNAME}}' or '${{PASSWORD}}' if needed.
- Use no more than 20 steps.
- Use generic actions: "goto", "click", "search", "type", "screenshot", "play".
- Output ONLY valid JSON in the format:
{{
  "task": "<short_task_name>",
  "steps": [
    {{"action": "<action>", "target": "<target>", "value": "<optional_placeholder>"}}
  ]
}}
"""
    raw = ai_generate(prompt)
    plan = clean_json_response(raw)

    task_name = plan.get("task", "unnamed_task").replace(" ", "_").lower()
    json_path = os.path.join(TASKS_DIR, f"{task_name}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)

    print(f"Task plan saved: {json_path}")
    return task_name


def generate_ts_from_json(task_name: str, mode: str):
    """Generate inspection or final TS from JSON task plan."""
    path = os.path.join(TASKS_DIR, f"{task_name}.json")
    if not os.path.exists(path):
        print(f"Error: Task JSON not found for {task_name}")
        return

    with open(path, "r", encoding="utf-8") as f:
        plan = json.load(f)

    prompt = f"""
You are an expert in Playwright and TypeScript automation.
Convert this structured task plan into valid Playwright TypeScript code.

Rules:
- Always use async/await
- Use getByRole/getByText/getByLabel for locating elements
- Do not use XPath
- Output ONLY TypeScript code, no explanations
- Ensure each element is properly awaited
- Take screenshots if mentioned in the steps
- Use a loop for multiple screenshots
- Wait until the page is visible or fully loaded before performing actions
- If a link or element doesn't exist, click the first similar element
- Screen record slowly if required
- If mode = inspection: also extract and save relevant HTML of each visited page (prefer <main>, strip scripts/styles, truncate to 50k chars)
- Save HTML in '{OUTPUT_DIR}' as page_source_X.html

Task plan:
{json.dumps(plan, indent=2)}
Mode: {mode.upper()}
"""

    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt
    )

    raw_code = response.text.strip()
    if raw_code.startswith(""):
        lines = raw_code.splitlines()
        if lines[0].startswith(""):
            lines = lines[1:]
        if lines and lines[-1].startswith(""):
            lines = lines[:-1]
        code = "\n".join(lines)
    else:
        code = raw_code

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"{task_name}{mode}{timestamp}.spec.ts"
    ts_path = os.path.join(OUTPUT_DIR, filename)

    with open(ts_path, "w", encoding="utf-8") as f:
        f.write(code)

    print(f"{mode.capitalize()} Playwright script generated: {ts_path}")
    return ts_path


def run_playwright_test(file_path: str, headed: bool = True):
    print(f"Running Playwright script: {file_path}")

    folder = os.path.dirname(file_path)
    filename = os.path.basename(file_path)

    cmd = ["npx", "playwright", "test", filename]
    if headed:
        cmd.append("--headed")  # only add headed if True

    result = subprocess.run(cmd, cwd=folder, shell=True)

    if result.returncode != 0:
        print("Playwright test failed.")
    else:
        print("Playwright test completed successfully.")


# ======================
# MAIN PIPELINE
# ======================
if _name_ == "_main_":
    user_prompt = input("Enter your automation instruction: ").strip()
    print("\nGenerating task plan...")
    task_name = generate_task_plan(user_prompt)

    print("\nGenerating INSPECTION script...")
    inspection_path = generate_ts_from_json(task_name, "inspection")

    print("\nRunning INSPECTION automatically...")
    run_playwright_test(inspection_path, headed=False)  # headless mode

    print("\nGenerating FINAL script...")
    final_path = generate_ts_from_json(task_name, "final")

    print("\nRunning FINAL script automatically...")
    run_playwright_test(final_path, headed=True)

    print("\nAll done — Inspection + Final executed successfully.")
