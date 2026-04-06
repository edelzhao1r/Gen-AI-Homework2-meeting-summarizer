# Meeting Action Item Extractor

## Overview

This project builds a small Python prototype that extracts structured action items, decisions, and open questions from raw meeting notes using the Google Gemini API.

**Business workflow:** This project focuses on converting internal project meeting notes into structured action items.

**User:** The primary user is a project manager or team member who needs a clear and actionable summary after a meeting.

**Input:** Raw meeting transcript or notes in free-text form (English).

**Output:** Structured JSON containing:
- ✅ **Action items** — task description, owner, due date, and confidence level
- 📌 **Decisions** — confirmed outcomes from the meeting
- ❓ **Open questions** — items discussed but not resolved

**Why this task is valuable enough to automate or partially automate?** Meeting notes are high-frequency, high-friction, and follow predictable patterns. The bottleneck is mechanical extraction, not judgment — making it a reasonable candidate for LLM assistance with human review on flagged items.

---

## Repository Structure

```
hw2-meeting-summarizer/
├── README.md          ← This file
├── app.py             ← Main Python prototype
├── prompts.md         ← Prompt iteration log (V1 → V2 → V3)
├── eval_set.json      ← 5 evaluation test cases
├── report.md          ← evaluation report
└── outputs/           ← Generated output files
```

---

## Setup

### 1. Clone the repository
```bash
git clone https://github.com/edelzhao1r/hw2-meeting-summarizer.git
cd hw2-meeting-summarizer
```

### 2. Install dependencies
```bash
pip install google-genai python-dotenv
```

### 3. Add your API key
Create a `.env` file in the project root:
```
GEMINI_API_KEY=your_key_here
```

---

## Usage

### Run the full evaluation set
```bash
python app.py --eval
```

### Test a specific prompt version (v1, v2, or v3)
```bash
python app.py --eval --prompt-version v2
```

### Run on a text file
```bash
python app.py --input my_meeting.txt
```

### Run on inline text
```bash
python app.py --text "Alice will finish the report by Friday. Bob will send the client update by EOD."
```

All outputs are saved to the `outputs/` directory with a timestamp.

---

## Evaluation Design

Five test cases in `eval_set.json` cover:

| Case | Type | What it tests |
|------|------|---------------|
| case_01 | Normal | Well-structured meeting, clear owners and dates |
| case_02 | Normal | Short standup, minimal content |
| case_03 | Edge | Messy transcript, ambiguous ownership |
| case_04 | Edge | Tasks present but no owners assigned |
| case_05 | Hallucination risk | No action items — tests whether model invents tasks |

---

## Key Finding

Even V1 avoided hallucination on Case 05. The main failure mode was not false invention, but silent omission — V2 dropped ambiguous items entirely. V3 solved this with confidence signaling.
The most important prompt improvement was adding a **`confidence` field** and explicit rules for handling ambiguity. The model's default behavior is to resolve uncertainty helpfully — which means hallucinating ownership. Giving it permission to say `"owner": "Unclear"` with `"confidence": "low"` reduces hallucination more effectively than general "do not infer" rules.

See `prompts.md` for the full iteration log and `report.md` for the complete evaluation.

---

## Walkthrough Video

🎥 **[Video link — add after recording]**

---

## Model

- **Model:** `gemini-2.5-flash` via Google AI Studio API
- **Why Flash over Pro:** Extraction task, not synthesis — Flash is faster, cheaper, and performed comparably on this eval set.
