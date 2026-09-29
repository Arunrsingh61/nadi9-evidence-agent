# Demonstration and technical discussion

## Five-minute demo

1. Run the tests, then run the synthetic pack using README commands.
2. Open `sample_run/subtitle_decisions.jsonl`. S002 has competing meanings for “work”; the system proposes only a review candidate and reports the evidence conflict.
3. Locate `work-poison`, `lex-work-A` and `lex-work-B` in evidence_records.json. Explain why a high-coverage dictionary is not automatically trusted.
4. Apply data/correction.json. The CLI prints only S002 as impacted. Compare the old and new audit records. Other decision objects remain unchanged.
5. Show S003: missing “moon” yields null text and a question rather than an invented word.
6. Show the final HOLD recommendation. The demo is synthetic and the actual evidence pack has not arrived.

## Questions you should be able to answer

**How is a source trusted?** Human-configured provenance, independent corroboration, scoped applicability and observed counterexamples. Source size and recency do not settle disputes. Reliability priors are not calibrated truth probabilities.

**How is verifier disagreement possible?** The proposer emits text and alignments. Independent deterministic code checks them against engine-owned evidence, exact coverage, grammar and timing. The tests deliberately inject an unsupported grammar claim, omitted token and changed number; verification refuses approval.

**What changes after a corrected rule?** Rebuild the affected hypothesis group, invalidate decisions that depend on it, rerun those decisions and retain old evidence/decisions for audit. Grammar is shared and may affect all cues. Lexical changes can be narrow.

**Which choices require a human?** Unresolved source contradictions, unsupported language, humour and culturally sensitive relationship interpretation, context/role annotations, and final release approval.

**What happens when a tool fails?** One bounded retry, with failed attempts charged to budget. Continued failure or exhausted budget produces an explicit abstention and review question. It never calls an unapproved fallback service.

**Why no vector database or live model?** The supplied brief lacks the real corpus. For this small reproducible slice, deterministic retrieval and replay expose reasoning without API keys. They do not replace eventual language extraction/transcription or evaluation on the real pack.

**How would this scale?** Versioned dialect namespaces, durable evidence/decision storage, reverse-dependency indices, idempotent per-episode jobs, bounded budgets and expert queues. The current prototype remains a local CLI.

**What did AI help with and what was checked?** Read AI_COLLABORATION.md. Explain the malformed-provider regression and shared-grammar invalidation fix. Do not invent a personal rejection story or pretend to have written the code unaided.

## Simple Hindi explanation

यह project fluent translation से पहले evidence देखता है। अगर किसी शब्द के दो meaning मिलते हैं, तो वह conflict दिखाता है। शब्द का evidence नहीं है तो translation invent नहीं करता। Expert correction आने पर उस शब्द से जुड़ी lines ही दोबारा check होती हैं। हर decision के पीछे कौन-सा source था, वह JSON में मिलता है। अभी demo के शब्द बनाए हुए हैं; company का असली data मिलने पर उसका अलग validation करना होगा।

पहले README की तीन commands अपने Mac पर चलाएँ। फिर S002 की पुरानी और corrected decision समझें। Interview में “हमारी accuracy इतनी है” न कहें, क्योंकि असली Nadi-9 data पर evaluation अभी नहीं हुआ है।
