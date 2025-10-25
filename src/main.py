import os
import json
import re
import getpass
from google import genai
from dotenv import load_dotenv

# -------------------------
# Init & config
# -------------------------
load_dotenv()  # load any existing .env (so we don't overwrite existing)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

TASKS_DIR = "tasks"
ENV_FILE = ".env"
os.makedirs(TASKS_DIR, exist_ok=True)


# -------------------------
# Low-level helpers
# -------------------------
def ai_generate(prompt: str) -> str:
    """Stream Gemini response into a single text string."""
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
    """Extract JSON object from AI output; fall back to raw_text if parse fails."""
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
    """Replace URLs with placeholder recursively."""
    if isinstance(obj, dict):
        return {k: remove_urls(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [remove_urls(v) for v in obj]
    if isinstance(obj, str):
        return re.sub(r"https?://\S+", "<website>", obj)
    return obj


def store_in_env(key: str, value: str):
    """Persist key=value to .env (append/update) and set it in runtime env."""
    # Read existing lines
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

    # Write back
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)

    # Make available immediately in this process
    os.environ[key] = value


def resolve_secret(value: str) -> str:
    """If value is a ${KEY} placeholder, return os.getenv(KEY) else return literal value."""
    if not isinstance(value, str):
        return value
    m = re.match(r"^\$\{(.+?)\}$", value)
    if m:
        key = m.group(1)
        return os.getenv(key, "")
    return value


# -------------------------
# Credential extraction + handling
# -------------------------
def extract_credentials_from_instruction(instruction: str):
    """
    Try to extract username/password pairs from the user's instruction.
    Returns (username, password) or (None, None).
    """
    username = None
    password = None

    # common patterns: "username X", "user X", "login as X", "password Y", "pass Y"
    u_match = re.search(r"(?:username|user|login as)\s+['\"]?([^\s,'\"]+)['\"]?", instruction, re.IGNORECASE)
    p_match = re.search(r"(?:password|pass)\s+['\"]?([^\s,'\"]+)['\"]?", instruction, re.IGNORECASE)

    if u_match:
        username = u_match.group(1)
    if p_match:
        password = p_match.group(1)

    return username, password


def detect_service_from_text(text: str, fallback: str = "GENERAL"):
    """Try to infer service (INSTAGRAM, FACEBOOK, etc.) from text; fallback to provided name."""
    if not text:
        return fallback.upper()
    match = re.search(r"(instagram|facebook|youtube|twitter|gmail|linkedin|tiktok)", text, re.IGNORECASE)
    return match.group(1).upper() if match else fallback.upper()


def handle_login_credentials(plan_json: dict, instruction: str):
    """
    For every 'type' step that looks like username/password:
     - Try to get real value from instruction
     - If missing or a placeholder, prompt user (username prompt or password prompt via getpass)
     - Store real value in .env as USERNAME_<SERVICE> / PASSWORD_<SERVICE>
     - Replace step value with placeholder ${USERNAME_<SERVICE>} / ${PASSWORD_<SERVICE>}
    """
    steps = plan_json.get("steps", [])
    task_name = plan_json.get("task", "GENERAL")
    instr_user, instr_pass = extract_credentials_from_instruction(instruction)

    for step in steps:
        if step.get("action") != "type":
            continue
        target = (step.get("target") or "").lower()
        current_value = step.get("value", "")

        # Determine service using target first, then task name, then fallback
        service = detect_service_from_text(target, fallback=task_name)

        # Username handling
        if "username" in target or re.search(r"\b(user|email|login)\b", target):
            env_key = f"USERNAME_{service}"
            # decide real value: instruction extract -> literal current value (if not placeholder) -> prompt
            real_value = None
            if instr_user:
                real_value = instr_user
            elif isinstance(current_value, str) and not re.match(r"^\$\{.+\}$", current_value) and current_value.strip():
                real_value = current_value
            else:
                # prompt the user
                real_value = input(f"Enter username for {service} (will be saved to {ENV_FILE}): ").strip()

            if real_value:
                store_in_env(env_key, real_value)
                step["value"] = f"${{{env_key}}}"

        # Password handling
        elif "password" in target or re.search(r"\b(pass|pwd)\b", target):
            env_key = f"PASSWORD_{service}"
            real_value = None
            if instr_pass:
                real_value = instr_pass
            elif isinstance(current_value, str) and not re.match(r"^\$\{.+\}$", current_value) and current_value.strip():
                real_value = current_value
            else:
                # secure prompt
                real_value = getpass.getpass(f"Enter password for {service} (input hidden, will be saved to {ENV_FILE}): ").strip()

            if real_value:
                store_in_env(env_key, real_value)
                step["value"] = f"${{{env_key}}}"

    return plan_json


# -------------------------
# Presentation helpers
# -------------------------
def json_to_stepwise_text(plan_json: dict) -> str:
    steps = plan_json.get("steps", [])
    if not steps:
        return "⚠️ No steps found in the task plan."

    lines = []
    for i, step in enumerate(steps, start=1):
        action = step.get("action", "<action>")
        target = step.get("target", "<target>")
        value = step.get("value", None)

        # Mask passwords for display
        display_value = None
        if isinstance(value, str):
            resolved = resolve_secret(value)
            if "password" in target.lower():
                display_value = "*" * 8  # fixed length mask
            else:
                display_value = resolved or value

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
def generate_task_plan(instruction: str, max_steps: int = 20):
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

    # handle credentials: extract from instruction or prompt & store into .env + os.environ
    plan = handle_login_credentials(plan, instruction)

    task_name = plan.get("task", "unnamed_task").replace(" ", "_").lower()
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

    # handle credentials again (may prompt)
    updated = handle_login_credentials(updated, modification_instruction)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(updated, f, indent=2)

    step_text = json_to_stepwise_text(updated)
    save_stepwise_text(task_name, step_text)
    print(f"✅ Task '{task_name}' updated at {json_path}")
    return updated


# -------------------------
# CLI / Main loop
# -------------------------
def choose_task() -> str:
    tasks = [f[:-5] for f in os.listdir(TASKS_DIR) if f.endswith(".json")]
    if not tasks:
        print("❌ No tasks available.")
        return None
    for i, t in enumerate(tasks, start=1):
        print(f"{i}. {t}")
    choice = input("Select a task number: ").strip()
    if not choice.isdigit() or not (1 <= int(choice) <= len(tasks)):
        print("❌ Invalid choice.")
        return None
    return tasks[int(choice) - 1]


if __name__ == "__main__":
    print("Welcome! Options:\n1. Add Task\n2. Modify Task\n3. Regenerate Stepwise Text from JSON (Developer Mode)")
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
            path = os.path.join(TASKS_DIR, f"{task}.json")
            plan = json.load(open(path, "r", encoding="utf-8"))
            text = json_to_stepwise_text(plan)
            save_stepwise_text(task, text)
            print(f"✅ Regenerated stepwise text for '{task}'.")

    else:
        print("❌ Invalid option. Please type 1, 2, or 3.")
