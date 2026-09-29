# Architecture and engineering choices

## Execution flow

Local curated JSON -> schema and reference validation -> source inventory -> scoped claim hypotheses -> counterexample tests -> risk-prioritized cue plan -> constrained replay proposal -> independent deterministic verification -> decision/review queue -> release gate and snapshot.

Correction events enter through a separate local CLI: validate event -> invalidate/add evidence -> rebuild affected claim groups -> find dependent cues -> replan and reverify those cues -> preserve original decisions in audit history.

## Planning and memory

The planner scores missing claims above conflicted/weak claims and adds risk for humour, ambiguity and tone. High-risk cues execute first within a fixed budget. Output is sorted back into chronological order. This is a deterministic plan-act-check-replan state machine, not a general LLM agent.

Memory is explicit JSON: sources, immutable evidence identifiers, active/withdrawn flags, scoped hypotheses, decisions, dependencies, revisions, event IDs, cumulative budget and chronological audit records. Pack hashes identify the knowledge snapshot for each decision. Old decisions remain in the audit; unaffected current decisions retain their original revision/hash. Run directories are not overwritten. This makes local review reproducible but is not a cryptographically signed audit trail.

## Evidence and hypotheses

The pack format is a curated ingestion boundary. Each lexical or grammar record is a candidate claim, not automatically a fact. The engine groups competing values by key and scope. It requires support from at least two independent source groups, rejects self-corroboration, and exposes disagreements. Repeated copied documents must share an independence group.

Source reliability is an explicit human-configured prior. It is not inferred from file size, recency or prose asserting authority. Dictionaries and viewer feedback cannot receive more than 0.75 effective weight. An expert is not automatically ground truth. Claims need corroboration even when an individual source has a high prior. Authors, dates and scope remain visible in the source inventory; dates are not used as automatic truth scores.

More specific matching relationship/status scopes take precedence over generic senses, but generic evidence remains cited. Contradictions at the chosen specificity force review regardless of the winning score. This policy is conservative rather than statistically calibrated.

Word-order hypotheses additionally predict held evidence observations and must pass examples from at least two independent groups. Failing observations become counterexamples. These are consistency tests on available examples, not an unseen accuracy benchmark. The prototype supports SVO/SOV permutations of one subject, verb and object. Tense, negation, morphology and idiom learning are deliberately not asserted from missing evidence.

## Proposal versus verifier

ReplayProvider creates a proposal consisting of text, a grammar claim, and source-to-target unit alignments. A future provider can implement the same method without changing downstream decisions.

The verifier recalculates support from engine-owned knowledge. It does not accept model-provided confidence or ask the generating model to approve itself. Checks cover lexical support, conflicting evidence, grammar support, word order, exact-once unit coverage, text additions, names/numbers/code-switch preservation, timing overlap, reading speed and cue length. Contextual humour or ambiguity always triggers expert review. Unsupported words yield a null translation and a focused evidence question.

This verifier shares the curated corpus with the proposer, so wrong curated alignments can fool both. That is a known limitation, addressed operationally with independent expert annotations and future blind challenge sets. Unit coverage is not full semantic equivalence.

## Correction and dependency semantics

Decision dependencies include every lexical key, including previously unknown keys, plus grammar:word_order. A new entry can therefore recover an earlier abstention. Lexical changes rerun only cues that use that key and match the changed scope; competing evidence is tracked as well as selected evidence. A shared grammar/example change conservatively reruns all grammar-dependent cues, because a counterexample can invalidate a shared hypothesis. It is unsafe to promise zero over-invalidation here.

Corrections are idempotency-guarded by event ID; repeated events are rejected. Existing evidence IDs cannot be replaced silently. Evidence withdrawal changes an active flag; corrections add new records with new IDs. Events validate against a copy before mutation. Provider failures after a valid correction are recorded as safe abstentions. Source metadata replacement and episode timing changes need a fresh run in this version.

## Budgets and failure recovery

Limits are configurable from zero up to 25 model calls and 50 tool calls per episode. Replay counts each proposal attempt as a tool call and makes zero model calls. In-memory retrieval, deterministic validation and local serialization are not external tool calls. A failed attempt still spends budget. At most one retry is attempted for transient errors; exhausted budget leads to review, never a fabricated fallback. Malformed provider output is reset before verification. Resumed corrections inherit cumulative usage.

A production hosted provider must reserve one model call before every network attempt and enforce timeout, no nested hidden retries, approved retention policies and schema-constrained output. This adapter is not implemented. There is no fake live LLM integration or claimed transcription capability.

## Trust and privacy boundaries

Raw feedback is inert text stored for review. It cannot become a claim, issue a command, modify budgets, approve subtitles or create corrections. No tool executes text from evidence. The adversarial fixture explicitly includes an instruction to ignore assignment rules; it has no control-plane effect. Structured evidence and source reliability require a trusted local curator. A poisoned structured entry can still be detected only when contradicted or insufficiently corroborated, not by magical lie detection.

The runnable pipeline imports no HTTP client and makes no external calls. Actual supplied material should stay local unless the company explicitly approves a provider's retention/training policy. Local snapshots contain full text: protect and delete them according to company policy. Do not put credentials in packs, logs or repository history. The generated submission contains only synthetic data and documentation.

## Release policy and scale

Any unresolved cue, empty episode, missing material category or synthetic fixture yields HOLD. Otherwise the system can recommend READY_FOR_EXPERT_SIGNOFF, never automatic publication. Category inventory does not prove the supplied files are complete or authentic.

For 5,000 episodes and 40 dialects: namespace claims by dialect/version; store source spans and decisions in durable storage; index reverse dependencies; dispatch bounded idempotent jobs per episode; use optimistic version locks for corrections; partition expert queues by dialect and risk; sample accepted lines for independent quality audits. These are design proposals, not implemented distributed features.
