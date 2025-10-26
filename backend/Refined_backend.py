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
OUTPUT_DIR = r"C:\Users\Balaji K\OneDrive\Desktop\LLM_PlayWright-TEST5\tests"
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


def get_prompt_path(task_name: str) -> str:
    return os.path.join(TASKS_DIR, f"{task_name}_prompt.txt")


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
    prompt_path = get_prompt_path(task_name)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)

    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(instruction)

    print(f"Task plan saved: {json_path}")
    print(f"Original prompt saved: {prompt_path}")
    return task_name


def load_original_prompt(task_name: str) -> str:
    prompt_path = get_prompt_path(task_name)
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Original prompt not found for {task_name}")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read().strip()


# ======================
# STEP 2: INSPECTION SCRIPT
# ======================
def generate_inspection_script(task_name: str) -> str:
    original_instruction = load_original_prompt(task_name)

    prompt = f"""
You are an expert in Playwright and TypeScript automation.
Generate a Playwright script that:
- ONLY visits the websites required to fulfill the instruction below.
- Waits for full page load.
- Extracts the relevant HTML structure (prefer <main> else <body>).
- Removes script/style/link/meta tags.
- Truncates HTML to 50,000 chars.
- Saves HTML as page_source_X.html in '{OUTPUT_DIR}'.
- NO other interactions unless strictly required to load the page.
- Output ONLY TypeScript code.

Original user instruction:
"{original_instruction}"
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
# STEP 3: FINAL SCRIPT GENERATION (HTML + Original Prompt)
# ======================
def generate_final_script_from_html(task_name: str) -> str:
    original_instruction = load_original_prompt(task_name)

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
Using the inspected HTML and the original instruction, generate the final Playwright script.

Rules:
- Follow the original user instruction exactly.
- Use the inspected HTML only to choose the most stable and semantic selectors.
- Always use async/await.
- Prefer getByRole/getByPlaceholder/getByLabel/getByText.
- Avoid XPath or unnecessary waits.
- Keep the script minimal and clean.
- Output ONLY valid TypeScript code.

Original instruction:
"{original_instruction}"

Inspected HTML:
{html_combined[:50000]}
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

    print("\nGenerating task plan...")
    task_name = generate_task_plan(user_prompt)

    print("\nGenerating INSPECTION script...")
    inspection_path = generate_inspection_script(task_name)

    print("\nRunning INSPECTION automatically (headless)...")
    run_playwright_test(inspection_path, headed=False)

    print("\nGenerating FINAL script from inspected HTML...")
    final_path = generate_final_script_from_html(task_name)

    if final_path:
        print("\nRunning FINAL script automatically (headed)...")
        run_playwright_test(final_path, headed=True)
        print("\nAll done — Inspection + Final executed successfully.")
    else:
        print("\nFinal script generation skipped — no inspection output found.")
