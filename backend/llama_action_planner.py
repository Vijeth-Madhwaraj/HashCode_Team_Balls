import os
import json
import re
import dateparser
from google import genai

# Initialize Gemini client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Required fields per task type
REQUIRED_FIELDS = {
    "flight_booking": ["origin", "destination", "departure_date", "return_date", "number_of_passengers", "seat_class", "flight_type"]
    # Add other task types if needed
}

# Helper to detect if a field is present
def is_field_present(field, instruction, steps):
    instruction_lower = instruction.lower()
    # Combine target + value of all steps
    steps_text = " ".join(
        [str(step.get("target", "")).lower() + " " + str(step.get("value", "")).lower() for step in steps]
    )

    if field == "origin":
        return bool(re.search(r"\bfrom\s+[\w\s]+", instruction_lower)) or "origin" in steps_text
    elif field == "destination":
        return bool(re.search(r"\bto\s+[\w\s]+", instruction_lower)) or "destination" in steps_text
    elif field == "departure_date":
        # Check date in instruction or in step value
        return bool(dateparser.parse(instruction)) or bool(re.search(r"\d{1,2}\s\w+\s\d{4}", steps_text))
    elif field == "return_date":
        return "return" in instruction_lower or "round-trip" in steps_text
    elif field == "number_of_passengers":
        return bool(re.search(r"\b\d+\s*(passenger|people|member)s?\b", instruction_lower)) or \
               bool(re.search(r"\b\d+\s*(passenger|people|member)s?\b", steps_text))
    elif field == "seat_class":
        return any(word in instruction_lower for word in ["economy", "business", "first"]) or \
               any(word in steps_text for word in ["economy", "business", "first"])
    elif field == "flight_type":
        return any(word in instruction_lower for word in ["one-way", "round-trip"]) or \
               any(word in steps_text for word in ["one-way", "round-trip"])
    else:
        return False

# Detect missing info
def detect_missing_info(task_type, instruction, plan_json):
    missing = []
    steps = plan_json.get("steps", [])
    for field in REQUIRED_FIELDS.get(task_type, []):
        if not is_field_present(field, instruction, steps):
            missing.append(field)
    return missing

# Infer task type from instruction
def infer_task_type(instruction: str):
    inst = instruction.lower()
    if "flight" in inst or "book a flight" in inst:
        return "flight_booking"
    else:
        return "flight_booking"  # fallback for testing

# Main task plan generation
def generate_task_plan(instruction: str, max_steps: int = 6, output_file: str = "task_plan.json"):
    task_type = infer_task_type(instruction)

    prompt = f"""
Convert the following instruction into a structured JSON action plan for web automation.
Instruction: "{instruction}"

- Use no more than {max_steps} steps.
- Use generic actions: "goto", "click", "enter", "select", "search", "play", etc.
- Include a "value" field if a value is provided (e.g., origin, destination, date, passengers, class).
- Output format:

{{
    "task": "<short_task_name>",
    "steps": [
        {{"action": "<action>", "target": "<target>", "value": "<optional_value>"}},
        ...
    ]
}}
"""

    # Streaming API call
    response_stream = client.models.generate_content_stream(
        model="gemini-2.5-pro",
        contents=prompt
    )

    # Handle None chunks
    text = ""
    max_chars = 2000
    for chunk in response_stream:
        if chunk.text:
            text += chunk.text
        if len(text) >= max_chars:
            break

    # Clean code fences
    text_clean = re.sub(r"```(?:json)?", "", text).strip()

    try:
        plan_json = json.loads(text_clean)
    except json.JSONDecodeError:
        print("Warning: Failed to parse JSON, saving raw text instead")
        plan_json = {"raw_text": text_clean}

    # Detect missing info
    missing_info = detect_missing_info(task_type, instruction, plan_json)
    if missing_info:
        plan_json["missing_info"] = missing_info

    # Save JSON
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(plan_json, f, indent=4)

    # Print readable output
    print(f"\nTask plan saved to {output_file}\n")
    print("Readable JSON output:")
    print(json.dumps(plan_json, indent=4))

    print("\nStep-by-step instructions:")
    if "steps" in plan_json:
        for i, step in enumerate(plan_json["steps"], start=1):
            action = step.get("action", "do")
            target = step.get("target", "")
            value = step.get("value", "")
            if value:
                print(f"Step {i}: {action.capitalize()} {target} with value {value}")
            else:
                print(f"Step {i}: {action.capitalize()} {target}")

    if missing_info:
        print("\n⚠ Missing information detected:")
        for info in missing_info:
            print(f"- {info}")

    return plan_json

if __name__ == "__main__":
    instruction = input("Enter your instruction: ")
    generate_task_plan(instruction)
