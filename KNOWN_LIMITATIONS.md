# Known limitations and deliberate boundaries

1. The real assignment evidence pack is missing. The deliverable is a tested prototype and illustrative sample, not finished company episode subtitles.
2. Ingestion accepts human-curated JSON. There is no automatic PDF dictionary parser, transcription/diarization, forced alignment or audio confidence estimator. Five interviews cannot be processed without audio and an approved transcription path.
3. Language hypothesis induction is limited to grouping structured candidate claims and testing simple word order against examples. It does not discover a full grammar from raw prose or speech.
4. Translation supports a single S/V/O clause with corroborated whole-unit lexical entries. Negation, tense inflection, multiword idioms, punctuation restoration, agreement and productive morphology are not implemented. Other tense scopes abstain; other clause shapes require review.
5. Respect can select explicitly scoped lexical senses; humour and ambiguous tone are escalated. Code-switch spans require explicit human preservation labels. Labels and source roles may themselves be wrong.
6. Confidence is an explainable heuristic, not a calibrated probability. A proper calibration exercise requires independent expert-labelled decisions and reliability curves/Brier scores.
7. Corroboration cannot identify coordinated poisoning across falsely independent sources. Human curators set provenance and source reliability. A single trustworthy source can be held unnecessarily; this is an intentional conservative policy.
8. The verifier is structurally independent from provider output but shares the evidence representation. It does not prove full meaning preservation. Token coverage alone cannot prove semantic accuracy.
9. No hosted or local generative model adapter is shipped. Replay/mock satisfies the key-free execution requirement; its simple method interface is the extension point. No claim is made that model behaviour was evaluated live.
10. Correction scope covers evidence claims and example withdrawals/additions. Changing source metadata, source roles, timing or speaker context requires a fresh episode run. Shared grammar changes can conservatively invalidate many cues.
11. The SRT review copy can exceed normal two-line display limits because it contains review markers. It is for review, never distribution. approved_only.srt is incomplete while any cues are withheld.
12. Run state and audit logs are local plaintext, not encrypted or digitally signed; there is no database, service auth, multi-user correction approval or concurrent update locking.
13. Tests demonstrate engineered failure scenarios on synthetic data. They establish code behaviour, not accuracy on authentic Nadi-9 or effectiveness against every injection/poisoning attack.

Priority after receiving materials: preserve original spans and provenance; curate a small blind expert test set; map real grammar patterns; introduce audio only for disputed claims; test narrow extensions; then evaluate actual episode proposals. Do not expand fluency faster than verification coverage.
