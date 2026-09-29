# AI collaboration log

The candidate requested help completing the take-home assignment. Codex read the uploaded brief, identified the missing evidence pack, authored the Python prototype, synthetic fixtures, tests and documentation, and ran the CLI and automated tests in the execution environment. AI assistance is explicitly permitted by the brief.

## Decisions and checks in this session

- Chosen: an offline, zero-dependency replay implementation so evaluators can run without credentials and confidential linguistic material need not leave a local machine.
- Rejected as a design path: inventing an authentic dialect or claiming the absent interviews and company transcript had been processed. All demonstration words are labelled synthetic.
- Chosen: deterministic evidence/coverage/timing verification rather than asking the same model to endorse its own output.
- Tested: contradictory dictionary entries, unknown words, scoped respect, example revocation, fabricated grammar, injected instructions, tool retries/exhaustion, alignment errors, preservation, timing and correction impact.
- Found during execution: a malformed provider response remained assigned after retry validation failed, allowing it to reach the verifier. Fixed by resetting the proposal on every caught provider failure; the regression test passes.
- Reviewed correction dependencies: shared grammar/example changes now conservatively invalidate all dependent cues, preventing stale approvals when a context-scoped example changes a shared rule.

## Honest attribution

This is AI-assisted code and writing. No claim is made that Arun independently authored, reviewed or understood every line yet. The candidate should run the documented commands locally, inspect the implementation, and be ready to explain its tradeoffs. No real company language accuracy was measured. The log does not invent human review, development hours or interactions with external linguists.
