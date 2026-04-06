# Homework 2 Report: Meeting Action Item Extractor

## Business Use Case

Every team that runs meetings faces the same friction: someone has to read through the raw notes, identify what was decided, figure out who owns what, and turn it into a task list, which is consistently, every time. This is a narrow, high-frequency writing task with predictable patterns, which makes it a reasonable candidate for LLM assistance.

The workflow targets a project manager or team lead as the primary user. The system receives raw meeting transcripts or notes in free-text form and produces a structured JSON output containing three components: confirmed decisions, action items with owner and due date, and open questions that remain unresolved. The value proposition is not to replace the project manager's judgment, but to reduce the time spent on mechanical extraction so human attention can focus on reviewing and acting on the output rather than producing it.

---

## Model Choice

**Primary model: `gemini-2.5-flash`** via Google AI Studio API.

Flash was selected over Pro for this use case. First, the task is extraction-heavy rather than synthesis-heavy. The model needs to read carefully and output structured JSON, not reason across multiple documents. Second, Flash's latency and cost profile is appropriate for a workflow that might run after every team meeting.

No systematic A/B comparison against other models was run in this prototype. A production deployment would warrant a more structured model comparison on a larger eval set.

---

## Baseline vs. Final Design

**V1:** A single-sentence instruction with no format constraint. The model produced accurate content on Cases 01 and 02 correctly identifying all 4 action items, owners, and dates. However, output was free-form Markdown, which caused `JSONDecodeError` across all 5 cases. The system could not parse or route any output downstream. On Case 05, the model correctly avoided hallucinating action items.

**V2:** Added a required JSON schema and explicit rules against inventing information. A major structural improvement. Cases 01 and 02 produced clean, parseable JSON with accurate extraction. Case 04 correctly marked all owners as `"Unassigned"`. Case 05 returned an empty `action_items` array with no hallucination. However, Case 03 returned 0 action items, indicating that the model was too conservative and dropped the Stripe research task entirely rather than flagging its uncertainty. Useful information was silently lost.

**V3:** Added a `confidence` field (`"high" | "low"`) per action item, an `extraction_note` field for cases with no output, and expanded rules covering disputed and ambiguous ownership. Best overall performance across all 5 cases.

- **Case 01:** 4 action items, all marked `[HIGH]` confidence. Clean and accurate.
- **Case 02:** 2 action items, dates preserved as-is ("EOD Thursday"). No padding.
- **Case 03:** Stripe research task preserved with `Owner: Unclear [LOW]` and an `extraction_note` explaining the ambiguity — no longer silently dropped.
- **Case 04:** 3 action items marked `[LOW]` due to unassigned owners. Honest and useful.
- **Case 05:** Empty `action_items: []` with a clear `extraction_note`: *"The meeting notes explicitly state no specific next steps were agreed upon."* Zero hallucination.

---

## Where the Prototype Still Fails

Two failure modes remain after V3:

1. **Misclassification of action items as decisions (Case 04).** The onboarding flow redesign was listed under `decisions` rather than `action_items` in both V2 and V3, resulting in only 3 extracted items instead of 4. A production system would need clearer schema definitions or a post-processing step to catch this.

2. **Inconsistent `extraction_note` population.** The field is sometimes left blank or populated with boilerplate rather than meaningful context. This limits its usefulness as a reviewer signal.

---

## Deployment Recommendation

**Conditional yes, with mandatory human review on low-confidence items.**

The V3 prototype performs reliably on well-structured inputs and correctly handles the absence of action items. The `confidence` field provides a practical human review queue: low-confidence items get reviewed, high-confidence items can be spot-checked.

However, the misclassification issue in Case 04 means the system cannot be trusted to run fully autonomously. The appropriate deployment method is adding a human approval required tier. The model drafts the structured summary, and then the project manager reviews it before it is distributed or committed to a task tracker.