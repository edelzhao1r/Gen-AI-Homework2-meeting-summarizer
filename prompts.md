# Prompt Iteration Log

This file documents the evolution of the system prompt used in the meeting summarizer prototype.
Each version was tested against all 5 cases in `eval_set.json`.

---

## Version 1 — Initial Draft

```
You are a helpful assistant. Read the following meeting notes and extract the key action items, decisions, and any open questions.
```

**What changed from nothing:** This was the first attempt — minimal instruction, no format constraints, no handling of uncertainty.

**What worked:**
- Correctly identified action items in Case 01 and Case 02.
- Output was readable prose.

**What failed:**
- Case 03 (messy transcript): Model confidently assigned owners that were ambiguous in the source ("Jen will research Stripe pricing") — hallucinated certainty.
- Case 05 (no action items): Model invented 2 action items that were never discussed ("Alex will schedule a follow-up", "Team will finalize sprint length by next week") — clear hallucination.
- Output format varied significantly between runs; hard to parse downstream.
- No distinction between confirmed decisions and open questions.

**Verdict:** Fluent output, but structurally unreliable and prone to hallucination on ambiguous inputs.

---

## Version 2 — Add Structure + JSON Output

```
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
```

**What changed from V1:** Added a required JSON schema and explicit rules about not inventing information.

**What worked:**
- Case 01 and 02: Clean, parseable JSON output. All 4 action items correctly extracted with accurate owners and dates.
- Case 04 (no owners): All 4 items listed with `"owner": "Unassigned"` — no fabrication.
- Case 05: Returned empty `action_items` array on most runs — a significant improvement.

**What still failed:**
- Case 03 (messy transcript): On 2 out of 3 runs, model still assigned a confident owner for the Stripe research item despite the ambiguity in the source. The rule "extract only what is explicitly stated" was not strong enough to override the model's tendency to resolve ambiguity.
- Case 05: On 1 out of 3 runs, model still inserted a speculative action item — the rule was not consistently enforced.
- No mechanism to flag low-confidence extractions; model either committed or left blank.

**Verdict:** Major improvement in structure and parsability. Hallucination reduced but not eliminated on ambiguous cases.

---

## Version 3 — Add Uncertainty Signaling + Confidence Flag

```
You are a meeting assistant that extracts structured information from meeting notes for a project manager.

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
5. If the meeting contains no action items, return an empty array [] for action_items and explain briefly in extraction_note.
6. If a task was discussed but ownership was disputed or unresolved, still include the task with owner "Disputed".
7. Do not invent tasks, decisions, or questions not present in the notes.
```

**What changed from V2:** Added a `confidence` field per action item, expanded rules to cover disputed ownership, and added an `extraction_note` field to surface model uncertainty explicitly.

**What worked:**
- Case 03: Model now correctly returns `"owner": "Unclear"` and `"confidence": "low"` for the Stripe research item. No hallucinated certainty.
- Case 05: Consistently returns empty `action_items: []` and populates `extraction_note` explaining no tasks were assigned. Zero hallucination across all test runs.
- Case 04: All items correctly marked `"owner": "Unassigned"`, `"confidence": "low"`.
- Case 01 and 02: High-confidence items correctly marked `"confidence": "high"`. Output remains clean and parseable.

**What could still improve:**
- The `extraction_note` field is sometimes verbose and inconsistently populated across cases.
- For very long transcripts, the model occasionally misses action items buried in the middle — a chunking or retrieval strategy would help at scale.
- The JSON output was valid on all test runs, but a production system should still validate schema before parsing.

**Verdict:** Best overall performance. Confidence signaling makes human review easier — low-confidence items become a natural review queue. Recommended as the deployed prompt for this prototype.
