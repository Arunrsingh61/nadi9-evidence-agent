# Assignment coverage

| Brief requirement | Implementation / evidence | Boundary |
|---|---|---|
| Source inventory and reliability | Source records; evidence_records.json | Metadata curated locally; real files absent |
| Create language hypotheses | learn_group; learned_rules.json | Structured lexical candidates and SVO/SOV only |
| Test and retain counterexamples | Independent-origin example tests | Not held-out language evaluation |
| Timed subtitle proposals | CLI; SRT; decision JSONL | Synthetic sample, narrow grammar |
| Per-line evidence and confidence reason | Decision schema and inspectable IDs | Heuristic, not calibrated probability |
| Relationship/tone handling | Scope selection; pragmatics escalation | No invented idiom/irony translation |
| Independent verification | verify; adversarial tests | Cannot prove semantic equivalence |
| Human escalation | review_queue.json | Final signoff is manual |
| Replanning after corrections | Dependency keys and immutable audit | Shared grammar can affect whole episode |
| Poisoned dictionary | Conflict test and withdrawal demo | Cannot detect unanimous coordinated poison |
| Two bad approved examples | Revocation regression test | No authentic examples supplied |
| Unsupported model grammar | Hallucinating-provider regression test | Replay interface, no live model |
| Prompt injection in retrieval | Raw record is inert; injection test | Trusted structured ingestion boundary |
| Tool failure | Retry, malformed response, exhaustion tests | No audio transcription implemented |
| Configurable 25/50 budget | Budget object, CLI limits, resumed state | Local deterministic checks excluded |
| Reproducible provider mode | Offline ReplayProvider; zero dependencies | No hosted adapter supplied |
| Sample run and release decision | sample_run and sample_run_corrected | Both explicitly HOLD |
| Architecture and AI log | ARCHITECTURE.md; AI_COLLABORATION.md | Attribution explicit |
| Known limitations | KNOWN_LIMITATIONS.md | Real pack needed to complete episode |
