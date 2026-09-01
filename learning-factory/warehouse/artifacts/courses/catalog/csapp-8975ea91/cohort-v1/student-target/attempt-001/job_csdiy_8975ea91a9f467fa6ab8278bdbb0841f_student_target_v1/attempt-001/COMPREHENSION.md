# Comprehension Questions

Answer in submission/COMPREHENSION_RESPONSES.md. Use your own reasoning and cite your implementation or tests where requested. Do not alter this question sheet.

1. State the invariants connecting the histogram total, its individual counters, and the bytes accepted from the input stream. At which program boundaries must those invariants hold?

2. Explain how your implementation represents an input byte before using it to select a counter. What behavior would be at risk if that representation choice were changed?

3. A stream operation can return less data than requested. Explain how your program distinguishes progress, end-of-file, and error, and how that decision affects output and exit status. Cite the relevant code.

4. Explain why processing the same byte sequence with different read boundaries should produce the same report. Identify automated tests that support this claim and one boundary case those tests do not establish.

5. Describe when your program begins emitting its report. How does that timing affect what another program can infer after an input failure?

6. Describe your count-overflow policy. What externally observable false claim could the program make if overflow were ignored?

7. Choose one automated test and describe its oracle: where does the expected result come from, and why is it independent of the production counting logic? Name one plausible defect the test would miss.

8. Suppose a later unit requires a second presentation format while preserving the same counting behavior. Which responsibilities or interfaces would you retain, and which would you change? Explain using your current module boundary.

9. Trace one requirement through four artifacts: its design statement, implementing code, automated test, and recorded validation evidence. Identify any gap you found.

Keep each response focused. A precise paragraph is usually enough; use a short table or trace where it communicates better than prose.

---

Artifact provenance: course-manager-authored comprehension prompts for study_unit_csapp_001_trustworthy_byte_histogram; no external course material was retrieved.

Validation label: LEARNER_SAFE_QUESTIONS_ONLY.
