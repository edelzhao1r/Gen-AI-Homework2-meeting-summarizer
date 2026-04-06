"""
Meeting Action Item Extractor
==============================
Extracts structured action items, decisions, and open questions
from raw meeting notes using the Google Gemini API.

Usage:
    # Run on all eval set cases:
    python app.py --eval

    # Run on a single input file:
    python app.py --input meeting.txt

    # Run on inline text:
    python app.py --text "Alice will finish the report by Friday..."

    # Use a different prompt version (v1, v2, v3):
    python app.py --eval --prompt-version v2

Requirements:
    pip install google-generativeai python-dotenv

Setup:
    Create a .env file with: GEMINI_API_KEY=your_key_here
    Or set the environment variable directly.
"""

import os
import sys
import json
import argparse
import textwrap
from datetime import datetime
from pathlib import Path

import google.generativeai as genai
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_NAME = "gemini-1.5-flash"
EVAL_SET_PATH = Path("eval_set.json")
OUTPUT_DIR = Path("outputs")

# ---------------------------------------------------------------------------
# Prompt Versions
# ---------------------------------------------------------------------------

PROMPTS = {
    "v1": textwrap.dedent("""\
        You are a helpful assistant. Read the following meeting notes and extract
        the key action items, decisions, and any open questions.
    """),

    "v2": textwrap.dedent("""\
        You are a meeting assistant that extracts structured information from meeting notes.

        Return ONLY valid JSON in this exact format:
        {
          "decisions": ["..."],
          "action_items": [
            { "task": "...", "owner": "...", "due": "..." }
          ],
          "open_questions": ["..."]
        }

        Rules:
        - Extract only what is explicitly stated in the notes.
        - If owner is not mentioned, set owner to "Unassigned".
        - If due date is not mentioned, set due to "Not specified".
        - Do not add tasks, owners, or dates that are not in the notes.
    """),

    "v3": textwrap.dedent("""\
        You are a meeting assistant that extracts structured information from meeting notes
        for a project manager.

        Return ONLY valid JSON in this exact format — no extra text, no markdown, no explanation:
        {
          "decisions": ["..."],
          "action_items": [
            {
              "task": "...",
              "owner": "...",
              "due": "...",
              "confidence": "high | low"
            }
          ],
          "open_questions": ["..."],
          "extraction_note": "..."
        }

        Rules you MUST follow:
        1. Extract only what is explicitly stated. Do not infer, assume, or complete missing information.
        2. If owner is ambiguous or unclear, set owner to "Unclear" and confidence to "low".
        3. If no owner is mentioned at all, set owner to "Unassigned" and confidence to "low".
        4. If due date is not mentioned, set due to "Not specified".
        5. If the meeting contains no action items, return an empty array [] for action_items
           and explain briefly in extraction_note.
        6. If a task was discussed but ownership was disputed or unresolved, set owner to "Disputed".
        7. Do not invent tasks, decisions, or questions not present in the notes.
    """),
}

# ---------------------------------------------------------------------------
# Core Functions
# ---------------------------------------------------------------------------

def setup_client():
    """Initialize the Gemini client."""
    if not API_KEY:
        print("[ERROR] GEMINI_API_KEY not found.")
        print("  → Create a .env file with: GEMINI_API_KEY=your_key_here")
        print("  → Or set the environment variable directly.")
        sys.exit(1)
    genai.configure(api_key=API_KEY)
    return genai.GenerativeModel(MODEL_NAME)


def call_llm(model, system_prompt: str, user_input: str) -> dict:
    """
    Make a single LLM call and return parsed result.
    Returns a dict with 'raw', 'parsed', and 'error' keys.
    """
    full_prompt = f"{system_prompt.strip()}\n\n---\nMEETING NOTES:\n{user_input.strip()}"

    try:
        response = model.generate_content(full_prompt)
        raw_text = response.text.strip()

        # Strip markdown code fences if present
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            raw_text = "\n".join(
                line for line in lines
                if not line.startswith("```")
            ).strip()

        # Attempt JSON parse
        try:
            parsed = json.loads(raw_text)
            return {"raw": raw_text, "parsed": parsed, "error": None}
        except json.JSONDecodeError:
            return {"raw": raw_text, "parsed": None, "error": "JSONDecodeError"}

    except Exception as e:
        return {"raw": None, "parsed": None, "error": str(e)}


def format_output(case_id: str, result: dict, expected: str) -> str:
    """Format a single result for display and saving."""
    lines = []
    lines.append(f"{'='*60}")
    lines.append(f"CASE: {case_id}")
    lines.append(f"{'='*60}")

    if result["error"]:
        lines.append(f"[ERROR] {result['error']}")
        lines.append(f"Raw output:\n{result['raw']}")
    elif result["parsed"] is None:
        lines.append("[WARN] Response was not valid JSON.")
        lines.append(f"Raw output:\n{result['raw']}")
    else:
        parsed = result["parsed"]

        # Decisions
        decisions = parsed.get("decisions", [])
        lines.append(f"\n📌 DECISIONS ({len(decisions)})")
        if decisions:
            for d in decisions:
                lines.append(f"  • {d}")
        else:
            lines.append("  (none)")

        # Action Items
        items = parsed.get("action_items", [])
        lines.append(f"\n✅ ACTION ITEMS ({len(items)})")
        if items:
            for item in items:
                confidence = item.get("confidence", "")
                conf_tag = f" [{confidence.upper()}]" if confidence else ""
                lines.append(f"  • {item.get('task', 'N/A')}")
                lines.append(f"    Owner: {item.get('owner', 'N/A')} | "
                              f"Due: {item.get('due', 'N/A')}{conf_tag}")
        else:
            lines.append("  (none — model correctly detected no action items)")

        # Open Questions
        questions = parsed.get("open_questions", [])
        lines.append(f"\n❓ OPEN QUESTIONS ({len(questions)})")
        if questions:
            for q in questions:
                lines.append(f"  • {q}")
        else:
            lines.append("  (none)")

        # Extraction Note (v3 only)
        note = parsed.get("extraction_note", "")
        if note:
            lines.append(f"\n📝 EXTRACTION NOTE\n  {note}")

    lines.append(f"\n🎯 EXPECTED BEHAVIOR\n  {expected}")
    lines.append("")
    return "\n".join(lines)


def run_eval(model, prompt_version: str):
    """Run all eval set cases and save results."""
    if not EVAL_SET_PATH.exists():
        print(f"[ERROR] eval_set.json not found at {EVAL_SET_PATH}")
        sys.exit(1)

    with open(EVAL_SET_PATH) as f:
        eval_data = json.load(f)

    system_prompt = PROMPTS[prompt_version]
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"eval_{prompt_version}_{timestamp}.txt"

    print(f"\n🚀 Running eval set with prompt version: {prompt_version.upper()}")
    print(f"   Model: {MODEL_NAME}")
    print(f"   Cases: {len(eval_data['eval_set'])}")
    print(f"   Output: {output_file}\n")

    all_output = []
    all_output.append(f"EVAL RUN — Prompt: {prompt_version.upper()} | "
                      f"Model: {MODEL_NAME} | {timestamp}\n")

    results_summary = []

    for case in eval_data["eval_set"]:
        case_id = case["id"]
        case_type = case["type"]
        print(f"  Processing {case_id} ({case_type})...", end=" ", flush=True)

        result = call_llm(model, system_prompt, case["input"])
        formatted = format_output(case_id, result, case["expected_behavior"])
        all_output.append(formatted)

        # Summary row
        status = "✅ JSON OK" if result["parsed"] else "⚠️  Non-JSON"
        if result["error"]:
            status = f"❌ ERROR: {result['error']}"
        action_count = len(result["parsed"].get("action_items", [])) if result["parsed"] else "?"
        results_summary.append(
            f"  {case_id:<12} | {case_type:<30} | {status} | {action_count} action items"
        )
        print(status)

    # Print summary table
    print(f"\n{'─'*75}")
    print("SUMMARY")
    print(f"{'─'*75}")
    for row in results_summary:
        print(row)
    print(f"{'─'*75}\n")

    # Save full output
    with open(output_file, "w") as f:
        f.write("\n".join(all_output))
    print(f"✅ Full output saved to: {output_file}\n")


def run_single(model, prompt_version: str, text: str, label: str = "custom_input"):
    """Run the model on a single input and print results."""
    system_prompt = PROMPTS[prompt_version]
    print(f"\n🚀 Running single input with prompt version: {prompt_version.upper()}")

    result = call_llm(model, system_prompt, text)
    formatted = format_output(label, result, "N/A — single input mode")
    print(formatted)

    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"single_{prompt_version}_{timestamp}.txt"
    with open(output_file, "w") as f:
        f.write(formatted)
    print(f"✅ Output saved to: {output_file}\n")


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Meeting Action Item Extractor — uses Gemini to parse meeting notes"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--eval", action="store_true",
                       help="Run against full eval set (eval_set.json)")
    group.add_argument("--input", type=str,
                       help="Path to a .txt file containing meeting notes")
    group.add_argument("--text", type=str,
                       help="Inline meeting notes as a string")

    parser.add_argument("--prompt-version", choices=["v1", "v2", "v3"], default="v3",
                        help="Which prompt version to use (default: v3)")

    args = parser.parse_args()
    model = setup_client()

    if args.eval:
        run_eval(model, args.prompt_version)
    elif args.input:
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"[ERROR] File not found: {args.input}")
            sys.exit(1)
        text = input_path.read_text()
        run_single(model, args.prompt_version, text, label=input_path.stem)
    elif args.text:
        run_single(model, args.prompt_version, args.text)


if __name__ == "__main__":
    main()
