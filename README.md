# Meeting Action Item Extractor

**Generative AI (BU.330.760) — Homework 2**
**Author:** Edel Zhao | Johns Hopkins Carey Business School

---

## Overview

This project builds a small Python prototype that extracts structured action items, decisions, and open questions from raw meeting notes using the Google Gemini API.

**Business workflow:** A project manager pastes or pipes raw meeting transcript text into the tool. The system returns a structured JSON summary with:
- ✅ **Action items** — task description, owner, due date, and confidence level
- 📌 **Decisions** — confirmed outcomes from the meeting
- ❓ **Open questions** — items discussed but not resolved

**Why this task?** Meeting notes are high-frequency, high-friction, and follow predictable patterns. The bottleneck is mechanical extraction, not judgment — making it a reasonable candidate for LLM assistance with human review on flagged items.

---

## Repository Structure

```
hw2-meeting-summarizer/
├── README.md          ← This file (includes video link)
├── app.py             ← Main Python prototype
├── prompts.md         ← Prompt iteration log (V1 → V2 → V3)
├── eval_set.json      ← 5 evaluation test cases
├── report.md          ← 1-2 page evaluation report
└── outputs/           ← Generated output files (created at runtime)
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
pip install google-generativeai python-dotenv
```

### 3. Add your API key
Get a free API key from [Google AI Studio](https://aistudio.google.com/).

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

The most important prompt improvement was adding a **`confidence` field** and explicit rules for handling ambiguity. The model's default behavior is to resolve uncertainty helpfully — which means hallucinating ownership. Giving it permission to say `"owner": "Unclear"` with `"confidence": "low"` reduces hallucination more effectively than general "do not infer" rules.

See `prompts.md` for the full iteration log and `report.md` for the complete evaluation.

---

## Walkthrough Video

🎥 **[Video link — add after recording]**

---

## Model

- **Model:** `gemini-1.5-flash` via Google AI Studio API
- **Why Flash over Pro:** Extraction task, not synthesis — Flash is faster, cheaper, and performed comparably on this eval set.
