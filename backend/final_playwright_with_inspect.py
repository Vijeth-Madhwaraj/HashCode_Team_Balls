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
    """Stream Gemini response into a single string."""
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


# ======================
# STEP 1: TASK PLAN
# ======================
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


# ======================
# STEP 2: INSPECTION SCRIPT
# ======================
def generate_inspection_script(task_name: str) -> str:
    """Generate a Playwright script that visits pages and extracts HTML only."""
    path = os.path.join(TASKS_DIR, f"{task_name}.json")
    if not os.path.exists(path):
        print(f"Error: Task JSON not found for {task_name}")
        return

    with open(path, "r", encoding="utf-8") as f:
        plan = json.load(f)

    prompt = f"""
You are an expert in Playwright and TypeScript automation.
Generate a Playwright script that:
- ONLY visits the websites from the task plan.
- Waits for full page load.
- Extracts the relevant HTML structure (prefer <main> else <body>).
- Removes script/style/link/meta tags.
- Truncates HTML to 50,000 chars.
- Saves HTML as page_source_X.html in '{OUTPUT_DIR}'.
- NO other interactions unless strictly required to load the page.
- Output ONLY TypeScript code.

Task plan:
{json.dumps(plan, indent=2)}
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
    filename = f"{task_name}inspection{timestamp}.spec.ts"
    ts_path = os.path.join(OUTPUT_DIR, filename)

    with open(ts_path, "w", encoding="utf-8") as f:
        f.write(code)

    print(f"Inspection Playwright script generated: {ts_path}")
    return ts_path


# ======================
# STEP 3: FINAL SCRIPT GENERATION (FROM HTML)
# ======================
def generate_final_script_from_html(task_name: str) -> str:
    """Use the inspected HTML as context to generate final Playwright script."""
    html_combined = ""
    for i in range(1, 20):
        html_file_path = os.path.join(OUTPUT_DIR, f"page_source_{i}.html")
        if os.path.exists(html_file_path):
            with open(html_file_path, "r", encoding="utf-8") as f:
                html_combined += f"\n<!-- PAGE {i} START -->\n" + f.read() + f"\n<!-- PAGE {i} END -->\n"

    if not html_combined.strip():
        print("Warning: No inspection HTML files found. Run inspection first.")
        return None

    prompt = f"""
You are an expert in Playwright and TypeScript automation.
Using the provided inspected HTML, generate the final Playwright script to perform the original instruction accurately.

Rules:
- Use the inspected HTML as context to craft accurate selectors.
- Always use async/await.
- Use getByRole/getByText/getByLabel.
- No XPath.
- Wait for elements before interacting.
- Use loops if multiple screenshots or items are involved.
- Handle pop-ups gracefully.
- Output ONLY TypeScript code.

Inspected HTML:
{html_combined}
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
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        code = "\n".join(lines)
    else:
        code = raw_code

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"{task_name}final{timestamp}.spec.ts"
    ts_path = os.path.join(OUTPUT_DIR, filename)

    with open(ts_path, "w", encoding="utf-8") as f:
        f.write(code)

    print(f"Final Playwright script generated: {ts_path}")
    return ts_path


# ======================
# STEP 4: RUN PLAYWRIGHT
# ======================
def run_playwright_test(file_path: str, headed: bool = True):
    print(f"Running Playwright script: {file_path}")
    folder = os.path.dirname(file_path)
    filename = os.path.basename(file_path)

    cmd = ["npx", "playwright", "test", filename]
    if headed:
        cmd.append("--headed")

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

    # 1. Task Plan
    print("\nGenerating task plan...")
    task_name = generate_task_plan(user_prompt)

    # 2. Inspection
    print("\nGenerating INSPECTION script...")
    inspection_path = generate_inspection_script(task_name)

    print("\nRunning INSPECTION automatically (headless)...")
    run_playwright_test(inspection_path, headed=False)

    # 3. Final script using actual HTML
    print("\nGenerating FINAL script from inspected HTML...")
    final_path = generate_final_script_from_html(task_name)

    # 4. Run final
    if final_path:
        print("\nRunning FINAL script automatically (headed)...")
        run_playwright_test(final_path, headed=True)
        print("\nAll done — Inspection + Final executed successfully.")
    else:
        print("\nFinal script generation skipped — no inspection output found.")
