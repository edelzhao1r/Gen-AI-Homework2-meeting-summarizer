# Homework 2 Report: Meeting Action Item Extractor

**Author:** Edel Zhao | **Course:** Generative AI (BU.330.760) | **Week 2**

---

## Business Use Case

Every team that runs meetings faces the same friction: someone has to read through the raw notes, identify what was decided, figure out who owns what, and turn it into a task list — reliably, every time. This is a narrow, high-frequency writing task that follows predictable patterns, which makes it a reasonable candidate for LLM assistance.

The workflow targets a project manager or team lead as the primary user. The system receives raw meeting transcripts or notes in free-text form and produces a structured JSON output containing three components: confirmed decisions, action items with owner and due date, and open questions that remain unresolved. The value proposition is not to replace the PM's judgment, but to reduce the time spent on mechanical extraction so human attention can focus on reviewing and acting on the output rather than producing it.

---

## Model Choice

**Primary model: `gemini-1.5-flash`** via Google AI Studio API.

Flash was selected over Pro for this use case for three reasons. First, the task is extraction-heavy rather than synthesis-heavy — the model needs to read carefully and output structured JSON, not reason across multiple documents. Second, Flash's latency and cost profile is appropriate for a workflow that might run after every team meeting. Third, the free tier in AI Studio makes iteration fast during development.

No systematic A/B comparison against other models was run in this prototype. Informally, a few test calls were made against `gemini-1.5-pro` and the output quality was similar for Cases 01–02 while Pro showed marginally better restraint on Case 05 (the hallucination test). A production deployment would warrant a more structured model comparison on a larger eval set.

---

## Baseline vs. Final Design: Prompt Iteration

The most significant improvements came from prompt iteration, not model selection.

**V1 (baseline):** A single-sentence instruction with no format constraint. Output was readable prose but structurally inconsistent and prone to hallucination. On Case 05 (no action items), the model invented two tasks that were never mentioned. On Case 03 (ambiguous transcript), it assigned confident ownership to a task where the source was explicitly unclear.

**V2:** Added a required JSON schema and explicit rules against inventing information. This eliminated most formatting inconsistency and reduced hallucination on Case 05 to roughly one-in-three runs. However, the model still resolved ambiguity in Case 03 by silently picking an owner rather than flagging uncertainty.

**V3 (final):** Added a `confidence` field (`"high" | "low"`) per action item, an `extraction_note` field for cases with no output, and expanded rules covering disputed and ambiguous ownership. This produced the most reliable behavior across all five eval cases. The confidence signal is particularly useful operationally: low-confidence items become a natural human review queue rather than requiring the reviewer to read the entire output from scratch.

The key insight from iteration: the model's default behavior is to be helpful by resolving ambiguity, even when that means inventing certainty. Explicit rules that give it permission to say "unclear" are more effective than general rules like "do not infer."

---

## Where the Prototype Still Fails

Three failure modes remain after V3:

1. **Long transcripts with buried action items.** The eval set used relatively short inputs. For a 60-minute meeting transcript, the model occasionally missed items that appeared in the middle of a long block of text. A chunking strategy or a follow-up verification pass would be needed at scale.

2. **Inconsistent `extraction_note` population.** The field is present in the schema but sometimes left blank or populated with boilerplate rather than meaningful context. This makes it less useful as a reviewer signal than intended.

3. **Subtle hallucination on confident-sounding speculation.** In one V3 run on Case 03, the model returned `"confidence": "low"` but still wrote a task description that implied a decision had been made ("Jen will evaluate Stripe as a replacement payment processor") when the source only said someone might look into it. The confidence flag fired correctly, but the task wording itself was more definitive than the evidence warranted.

---

## Deployment Recommendation

**Conditional yes, with mandatory human review on flagged items.**

The V3 prototype performs reliably on well-structured inputs and correctly handles the absence of action items — the most dangerous failure mode (silent hallucination) has been substantially reduced. However, the three remaining failure modes above mean this system should not operate without a human in the loop.

The appropriate deployment pattern, using the framework from Module 2: **human approval required** tier. The model drafts the structured summary; the meeting organizer reviews it before it is distributed or committed to a task tracker. Low-confidence items (flagged by the `confidence` field) receive mandatory review; high-confidence items with clear owners and dates can be spot-checked rather than reviewed line-by-line.

This is not a limitation to hide — it is a reasonable division of labor. The model handles mechanical extraction; the human handles judgment calls about ownership disputes, ambiguous scope, and implicit commitments. That split is where the actual time savings come from.
