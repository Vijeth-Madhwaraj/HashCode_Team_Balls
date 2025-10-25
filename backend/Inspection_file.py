import os
import time
import sys
from google import genai

# === CONFIG ===
output_dir = r"C:\Users\Balaji K\OneDrive\Desktop\LLM_PlayWright - TEST3\tests"
os.makedirs(output_dir, exist_ok=True)

# === MODE SELECTION ===
mode = "inspect"  # default
if len(sys.argv) > 1:
    if sys.argv[1].lower() in ["inspect", "final"]:
        mode = sys.argv[1].lower()

# === GEMINI CLIENT ===
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# === USER INPUT ===
user_instruction = "Go to goodreads find 10 of the most popular books, click on them and take screenshots"

# === BASE PROMPT ===
base_prompt = (
    "You are an expert in Playwright and TypeScript automation. "
    "Generate valid Playwright TypeScript code from the user's instruction. "
    "Rules:\n"
    "- Always use async/await\n"
    "- Use getByRole/getByText/getByLabel for locating elements\n"
    "- Do not use XPath\n"
    "- Output ONLY TypeScript code, no explanations\n"
    "- Ensure each element is properly awaited or waited for\n"
    "- Take screenshots (IF MENTIONED IN THE PROMPT) of only what is visible to the user (not the full page)\n"
    "- Use a loop to store multiple screenshots (IF MENTIONED IN THE PROMPT)\n"
    "- Close any pop-ups before performing any action\n"
    "- Screen record videos slowly\n"
    "- Wait until a page is visible or has completely loaded before performing the required action\n"
    "- If a certain link doesn’t exist after searching, click on the first product or link (especially for e-commerce)\n"
)

# === GENERATE INSPECTION SCRIPT ===
if mode == "inspect":
    inspection_prompt = (
    base_prompt +
    "Your job now is NOT to perform the user action directly. "
    "Instead, generate Playwright TypeScript code that:\n"
    "- Visits the website(s) mentioned in the instruction\n"
    "- Waits until each page is fully loaded before continuing\n"
    "- Extracts ONLY the most relevant and visible HTML structure:\n"
    "  * Prefer <main> or fallback to <body>\n"
    "  * Remove <script>, <style>, <link>, <meta> tags completely\n"
    "  * Strip attributes like data-, aria-, or any attribute >100 chars\n"
    "  * Truncate the final HTML to 10,000 characters maximum\n"
    "- Explicitly import 'fs' and 'path'\n"
    "- Save the cleaned HTML file to this absolute path:\n"
    f"  '{output_dir.replace('\\', '\\\\')}'\n"
    "- Use fs.writeFileSync(path.join(...)) to store files like 'page_source_1.html', 'page_source_2.html'\n"
    "- Ensure the file is actually written into the tests folder\n"
    "- Keep it lightweight so the output file is small\n"
    f"User instruction: \"{user_instruction}\""
)



    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=inspection_prompt
    )

    raw_code = response.text.strip()
    if raw_code.startswith(""):
        lines = raw_code.splitlines()
        if lines[0].startswith(""):
            lines = lines[1:]
        if lines and lines[-1].startswith(""):
            lines = lines[:-1]
        inspection_code = "\n".join(lines)
    else:
        inspection_code = raw_code

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    inspection_filename = f"inspection_script_{timestamp}.spec.ts"
    inspection_path = os.path.join(output_dir, inspection_filename)

    with open(inspection_path, "w", encoding="utf-8") as f:
        f.write(inspection_code)

    print(f"✅ Inspection Playwright TypeScript file created: {inspection_path}")
    print("👉 Now run the inspection script using:")
    print(f"   npx playwright test tests/{inspection_filename}")

# === GENERATE FINAL SCRIPT ===
elif mode == "final":
    html_combined = ""
    for i in range(1, 20):  # look for up to 20 page sources
        html_file_path = os.path.join(output_dir, f"page_source_{i}.html")
        if os.path.exists(html_file_path):
            with open(html_file_path, "r", encoding="utf-8") as f:
                html_combined += f"\n<!-- PAGE {i} START -->\n" + f.read() + f"\n<!-- PAGE {i} END -->\n"

    if not html_combined:
        print("⚠ No page_source_X.html files found. Run the inspection script first.")
        sys.exit(0)

    final_prompt = (
        base_prompt +
        f"Here is the page source for better context:\n\n{html_combined}\n\n"
        f"User instruction: \"{user_instruction}\""
    )

    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=final_prompt
    )

    raw_code = response.text.strip()
    if raw_code.startswith(""):
        lines = raw_code.splitlines()
        if lines[0].startswith(""):
            lines = lines[1:]
        if lines and lines[-1].startswith(""):
            lines = lines[:-1]
        final_code = "\n".join(lines)
    else:
        final_code = raw_code

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    final_filename = f"final_script_{timestamp}.spec.ts"
    final_path = os.path.join(output_dir, final_filename)

    with open(final_path, "w", encoding="utf-8") as f:
        f.write(final_code)

    print(f"✅ Final Playwright TypeScript file created: {final_path}")
