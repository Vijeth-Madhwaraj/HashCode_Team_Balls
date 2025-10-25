import os
import json
import re
import getpass
from google import genai
from dotenv import load_dotenv

# -------------------------
# Init & config
# -------------------------
load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

TASKS_DIR = "tasks"
ENV_FILE = ".env"
os.makedirs(TASKS_DIR, exist_ok=True)

# -------------------------
# Helpers
# -------------------------
def save_readable_stepwise_text(task_name: str, plan_json: dict):
    lines = []
    steps = plan_json.get("steps", [])
    if not steps:
        lines.append("⚠️ No steps found in the task plan.")
    else:
        for i, step in enumerate(steps, start=1):
            action = step.get("action", "<action>")
            target = step.get("target", "<target>")
            value = step.get("value", None)
            display_value = "*" * 8 if isinstance(value, str) and "password" in target.lower() else value
            line = f"Step {i}: {action.capitalize()} -> {target}"
            if display_value:
                line += f" | Value: {display_value}"
            lines.append(line)
    out_path = os.path.join(TASKS_DIR, f"{task_name}_readable.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✅ Human-readable plan saved to {out_path}")

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

def execute_task(task_name: str):
    path = os.path.join(TASKS_DIR, f"{task_name}.json")
    if not os.path.exists(path):
        print(f"❌ Task {task_name} not found")
        return {"status": "error", "message": "task not found"}
    with open(path, "r", encoding="utf-8") as f:
        plan = json.load(f)
    print(f"Executing task '{task_name}' with {len(plan.get('steps',[]))} steps...")
    return {"status": "success", "task": task_name, "steps_count": len(plan.get("steps", []))}

def clean_json_response(raw_text: str) -> dict:
    text_clean = re.sub(r"```(?:json)?", "", raw_text).strip()
    match = re.search(r"\{.*\}", text_clean, re.DOTALL)
    if match:
        text_clean = match.group(0)
    else:
        print("⚠️ Warning: No JSON object detected, saving raw text instead")
        return {"raw_text": raw_text}
    try:
        return json.loads(text_clean)
    except json.JSONDecodeError:
        print("⚠️ Warning: Failed to parse JSON, saving raw text instead")
        return {"raw_text": text_clean}

def remove_urls(obj):
    if isinstance(obj, dict):
        return {k: remove_urls(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [remove_urls(v) for v in obj]
    if isinstance(obj, str):
        return re.sub(r"https?://\S+", "<website>", obj)
    return obj

def replace_urls_with_service(obj):
    """
    Recursively replace URLs or plain service names with proper capitalized service names.
    """
    service_map = {
        "instagram": "Instagram",
        "facebook": "Facebook",
        "youtube": "YouTube",
        "twitter": "Twitter",
        "gmail": "Gmail",
        "linkedin": "LinkedIn",
        "tiktok": "TikTok"
    }

    if isinstance(obj, dict):
        return {k: replace_urls_with_service(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [replace_urls_with_service(v) for v in obj]
    if isinstance(obj, str):
        # First, replace URLs
        def url_to_service(match):
            url = match.group(0).lower()
            for domain, name in service_map.items():
                if domain in url:
                    return name
            return "<website>"
        obj = re.sub(r"https?://\S+", url_to_service, obj)

        # Then, replace plain mentions of service names
        for key, name in service_map.items():
            pattern = re.compile(rf"\b{key}\b", re.IGNORECASE)
            obj = pattern.sub(name, obj)

        return obj
    return obj

def store_in_env(key: str, value: str):
    lines = []
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
    prefix = f"{key}="
    updated = False
    for i, line in enumerate(lines):
        if line.startswith(prefix):
            lines[i] = f"{key}={value}\n"
            updated = True
            break
    if not updated:
        lines.append(f"{key}={value}\n")
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)
    os.environ[key] = value

def resolve_secret(value: str) -> str:
    if not isinstance(value, str):
        return value
    m = re.match(r"^\$\{(.+?)\}$", value)
    if m:
        key = m.group(1)
        return os.getenv(key, "")
    return value

# -------------------------
# Credential handling
# -------------------------
def extract_credentials_from_instruction(instruction: str):
    """
    Extract identifiers (username, email, Indian phone) and password from instruction.
    Robustly handles multiple natural-language variants.
    """
    usernames = re.findall(r"(?:username|user|login as)\s+['\"]?([^\s,'\"]+)['\"]?", instruction, re.IGNORECASE)
    emails = re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", instruction)
    phones = re.findall(r"(?:\+91|0)?[6-9]\d{9}", instruction)
    # Password patterns
    pwd_pattern = (
        r"(?:password|pass)\b\s*(?:set|to|is|=|:)?\s*['\"]?(.+?)['\"]?"
        r"(?=(?:\s*(?:and|,|\busername\b|\buser\b|\bemail\b|\bmail\b|\bphone\b|\bnumber\b)|$))"
    )
    pwd_matches = re.findall(pwd_pattern, instruction, flags=re.IGNORECASE)
    password = None
    if pwd_matches:
        candidate = pwd_matches[-1].strip()
        if candidate.lower() not in {"to", "and", "was", "is", "set", ""}:
            password = candidate.rstrip(".;")
    return {"usernames": usernames, "emails": emails, "phones": phones, "password": password}

def detect_service_from_text(text: str, fallback: str = "GENERAL"):
    if not text:
        return fallback.upper()
    match = re.search(r"(instagram|facebook|youtube|twitter|gmail|linkedin|tiktok)", text, re.IGNORECASE)
    return match.group(1).upper() if match else fallback.upper()

def handle_login_credentials(plan_json: dict, instruction: str):
    creds = extract_credentials_from_instruction(instruction)
    steps = plan_json.get("steps", [])
    task_name = plan_json.get("task", "GENERAL")

    for step in steps:
        if step.get("action") != "type":
            continue
        target = (step.get("target") or "").lower()
        current_value = step.get("value", "")

        service = detect_service_from_text(target, fallback=task_name)

        # Assign correct identifier
        if "username" in target or re.search(r"\buser\b", target):
            value_to_use = creds["usernames"][0] if creds["usernames"] else current_value
            if value_to_use:
                step["value"] = value_to_use

        elif "mail" in target or "email" in target:
            value_to_use = creds["emails"][0] if creds["emails"] else current_value
            if value_to_use:
                step["value"] = value_to_use

        elif "phone" in target or "number" in target:
            value_to_use = creds["phones"][0] if creds["phones"] else current_value
            if value_to_use:
                step["value"] = value_to_use

        elif "password" in target or re.search(r"\b(pass|pwd)\b", target):
            env_key = f"PASSWORD_{service}"
            real_value = creds["password"] or (current_value if current_value and not re.match(r"^\$\{.+\}$", current_value) else getpass.getpass(f"Enter password for {service}: ").strip())
            if real_value:
                store_in_env(env_key, real_value)
                step["value"] = f"${{{env_key}}}"

    return plan_json

def json_to_stepwise_text(plan_json: dict) -> str:
    steps = plan_json.get("steps", [])
    if not steps:
        return "⚠️ No steps found in the task plan."
    lines = []
    for i, step in enumerate(steps, start=1):
        action = step.get("action", "<action>")
        target = step.get("target", "<target>")
        value = step.get("value", None)
        display_value = "*" * 8 if isinstance(value, str) and "password" in target.lower() else resolve_secret(value)
        line = f"Step {i}: {action.capitalize()} -> {target}"
        if display_value:
            line += f" | Value: {display_value}"
        lines.append(line)
    return "\n".join(lines)

def save_stepwise_text(task_name: str, text: str):
    out = os.path.join(TASKS_DIR, f"{task_name}_steps.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"✅ Stepwise plan saved to {out}")

# -------------------------
# Task management
# -------------------------
def generate_task_plan(instruction: str, existing_task_name: str = None, max_steps: int = 20):
    prompt = f"""
Convert the following instruction into a structured JSON action plan for web automation.
Instruction: "{instruction}"

- Do NOT include actual usernames or passwords; use placeholders like '${{USERNAME}}' or '${{PASSWORD}}' if needed.
- Use no more than {max_steps} steps.
- Use generic actions: "goto", "click", "search", "play", "type".
- Output ONLY valid JSON in the format:
{{
  "task": "<short_task_name>",
  "steps": [
    {{"action": "<action>", "target": "<target>", "value": "<optional_placeholder>"}},
    ...
  ]
}}
"""
    raw = ai_generate(prompt)
    plan = clean_json_response(raw)
    plan = remove_urls(plan)
    plan = replace_urls_with_service(plan)
    plan = handle_login_credentials(plan, instruction)

    task_name = existing_task_name or plan.get("task", "unnamed_task").replace(" ", "_").lower()
    plan["task"] = task_name

    json_path = os.path.join(TASKS_DIR, f"{task_name}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)

    step_text = json_to_stepwise_text(plan)
    save_stepwise_text(task_name, step_text)

    print(f"✅ Task '{task_name}' saved to {json_path}")
    return plan

def modify_task_plan(task_name: str, modification_instruction: str):
    json_path = os.path.join(TASKS_DIR, f"{task_name}.json")
    if not os.path.exists(json_path):
        print(f"❌ Task '{task_name}' not found.")
        return None
    with open(json_path, "r", encoding="utf-8") as f:
        existing = f.read()
    prompt = f"""
You are an intelligent automation planner.

Here is the current JSON task plan:
{existing}

Modify this plan based on the following user instruction:
"{modification_instruction}"

Keep the output strictly valid JSON only (no surrounding text).
"""
    raw = ai_generate(prompt)
    updated = clean_json_response(raw)
    updated = remove_urls(updated)
    updated = replace_urls_with_service(updated)
    updated = handle_login_credentials(updated, modification_instruction)
    updated["task"] = task_name

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(updated, f, indent=2)

    step_text = json_to_stepwise_text(updated)
    save_stepwise_text(task_name, step_text)
    print(f"✅ Task '{task_name}' updated at {json_path}")
    return updated

# -------------------------
# CLI / Main
# -------------------------
def choose_task():
    files = [f[:-5] for f in os.listdir(TASKS_DIR) if f.endswith(".json")]
    if not files:
        print("⚠️ No tasks found.")
        return None
    print("Available tasks:")
    for i, t in enumerate(files, start=1):
        print(f"{i}. {t}")
    choice = input("Choose a task by number: ").strip()
    try:
        idx = int(choice) - 1
        return files[idx] if 0 <= idx < len(files) else None
    except:
        return None

if __name__ == "__main__":
    print("Welcome! Options:\n1. Add Task\n2. Modify Task\n3. Edit JSON directly (Developer Mode)")
    opt = input("Choose an option (1/2/3): ").strip()

    if opt == "1":
        instr = input("Enter your instruction for the new task: ").strip()
        plan = generate_task_plan(instr)
        print("\n--- Stepwise Task Plan ---\n")
        print(json_to_stepwise_text(plan))

    elif opt == "2":
        task = choose_task()
        if task:
            mod = input("Describe what you want to modify: ").strip()
            updated = modify_task_plan(task, mod)
            if updated:
                print("\n--- Updated Stepwise Task Plan ---\n")
                print(json_to_stepwise_text(updated))

    elif opt == "3":
        task = choose_task()
        if task:
            json_path = os.path.join(TASKS_DIR, f"{task}.json")
            with open(json_path, "r", encoding="utf-8") as f:
                plan = json.load(f)
            print("\nCurrent JSON plan:")
            print(json.dumps(plan, indent=2))
            print("\nEdit JSON line by line. End input with empty line.")
            edited_lines = []
            while True:
                line = input()
                if line.strip() == "":
                    break
                edited_lines.append(line)
            if edited_lines:
                try:
                    edited_plan = json.loads("\n".join(edited_lines))
                except json.JSONDecodeError as e:
                    print(f"❌ Invalid JSON: {e}")
                    edited_plan = plan
            else:
                edited_plan = plan
            edited_plan["task"] = task
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(edited_plan, f, indent=2)
            text = json_to_stepwise_text(edited_plan)
            save_stepwise_text(task, text)
            print(f"✅ JSON plan and stepwise text for '{task}' updated successfully.")

    else:
        print("❌ Invalid option. Please type 1, 2, or 3.")
