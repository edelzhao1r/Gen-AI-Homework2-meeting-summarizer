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
- Cases 01 and 02: Content was accurate — all 4 action items correctly identified with the right owners and dates. 
- Case 05: Contrary to expectations, the model did NOT invent action items. It correctly stated "None identified" and cited the source text. 

**What failed:**
- All 5 cases returned `JSONDecodeError` — output was free-form Markdown with headers and bullet points, which the downstream parser could not handle.
- Output format varied between cases; no consistency guarantee

**Verdict:** Fluent output, but the output had no predictable shape.

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
- Case 04: All 4 items listed with `"owner": "Unassigned"` — no fabrication.
- Case 05: Returned empty `action_items` array on most runs — with no hallucination.

**What still failed:**
- Case 03: The model  returned 0 action items entirely, treating the Stripe research task as too ambiguous to include at all. The task was silently dropped rather than flagged. This is a different failure mode than expected: not overconfidence, but excessive conservatism that loses useful information.

**Verdict:** Major improvement in structure and parsability. Hallucination eliminated. But the model now has a new problem: when uncertain, it goes silent instead of flagging its uncertainty. Useful information is lost without any signal to the reviewer.

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
- Case 01: 4 action items, all [HIGH] confidence, owners and dates accurate.
- Case 02: 2 action items, "EOD Thursday" preserved as-is. No fabrication.
- Case 03: Stripe research task now preserved with `Owner: Unclear [LOW]` and an extraction_note explaining the ambiguity between Jen and Mike. This is the main improvement over V2.
- Case 04: All 3 extracted items marked [LOW] due to unassigned owners. Honest and useful for reviewer prioritization.
- Case 05: Empty `action_items: []` with extraction_note: "The meeting notes explicitly state no specific next steps were agreed upon." No hallucination.

**What could still improve:**
- Case 04: The onboarding flow redesign was classified as a decision rather than an action_item, resulting in only 3 extracted items instead of 4. The boundary between "a decision that implies a task" and "an action item without an assigned owner" is genuinely ambiguous — and the model resolved it differently than expected. This is an inherent limitation of the current schema design, not a prompting failure per se.

**Verdict:** Best overall performance across all 5 cases. Recommended as the deployed prompt for this prototype.
