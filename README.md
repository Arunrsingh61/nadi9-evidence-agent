# Nadi-9: evidence before fluency

A runnable, offline Python prototype for **Learn a Dialect That Does Not Exist**.
It creates auditable subtitle decisions, exposes conflicting evidence, abstains on missing knowledge, verifies proposals independently, and selectively recomputes decisions after corrections.

**Delivery status:** working engineering prototype with synthetic fixtures. The uploaded file contains the five-page challenge brief only. The actual examples, five interviews, grammar note, dictionaries, feedback, expert notes and episode were not provided. No translation in this repository is claimed to be authentic Nadi-9. Real episode completion is blocked until the company supplies those materials. The permitted AI assistance is disclosed in AI_COLLABORATION.md.

## Run in one minute

Python 3.10 or later. No API key, paid service, pip install or network connection required.
Open Terminal in this extracted `submission` folder:

```bash
python3 run.py run --pack data/synthetic_pack.json --out runs/demo
python3 -m unittest discover -s tests -v
python3 run.py correct --state runs/demo/run_state.json --event data/correction.json --out runs/corrected
```

Use a new output directory for each run; previous audit files are intentionally preserved.
On Windows, replace `python3` with `py` if appropriate. Optional installation for a `nadi9` executable: `python3 -m pip install -e .` (may download setuptools; unnecessary for the commands above).

```bash
python3 run.py run --pack data/synthetic_pack.json --out runs/failure --simulate-failure
python3 run.py run --pack data/synthetic_pack.json --out runs/limited --max-model-calls 0 --max-tool-calls 2
```

A successful command returns exit code 0 even if the release is HOLD: a safe abstention is a valid result. Invalid input or a nonempty output directory returns 2. Consumers must inspect release_report.json, not infer approval from an exit code.

## Included demonstration

| Cue | Scenario | Initial result | After C001 |
|---|---|---|---|
| S001 | Corroborated vocabulary and word order | APPROVED | Unchanged |
| S002 | Poison-like contradictory dictionary entry | HUMAN_REVIEW | APPROVED after entry withdrawal |
| S003 | Unknown word `moon` | INSUFFICIENT_EVIDENCE | Unchanged |
| S004 | Junior addresses senior | APPROVED with scoped respect form | Unchanged |
| S005 | Person name Ravi | APPROVED with exact preservation | Unchanged |
| S006 | Number 9 | APPROVED with exact preservation | Unchanged |
| S007 | Ironic tone | HUMAN_REVIEW | Unchanged |

Initial run: 7 decisions, 4 approved by the prototype checks, 3 escalated, 7 tool calls, 0 model calls. After the correction: only S002 is regenerated; 5 approved, 2 escalated, 8 cumulative tool calls. Both releases remain **HOLD**, including because fixtures are synthetic and interviews are absent.

`sample_run/` contains the initial result; `sample_run_corrected/` contains the correction result. These are reproducible outputs, not screenshots or manually edited decisions.

## What to inspect

- `subtitle_decisions.jsonl`: one machine-readable decision per cue, with proposal, confidence reason, references, assumptions, conflicts, checks and review question.
- `evidence_records.json`: inspectable evidence and source inventory, including withdrawn records.
- `learned_rules.json`: candidate claims, scope, support, counterexamples and grammar test results.
- `review_queue.json`: explicit unresolved questions.
- `audit_log.jsonl`: risk plans, failures, hypothesis tests, old and new decisions, correction impact.
- `run_state.json`: complete resumable snapshot with cumulative budget and evidence pack.
- `subtitles.srt`: annotated review copy; unknown lines have explicit placeholders.
- `approved_only.srt`: partial, unmarked approved cues only; never a complete release asset.
- `release_report.json` and `final_report.md`: final release recommendation and missing material categories.

## Adapting the actual company pack

1. Obtain the missing material listed in `docs/MISSING_MATERIAL.md`.
2. Keep it local in an ignored `private_pack/` directory. Do not commit confidential files to a public repository.
3. Follow `docs/PACK_FORMAT.md` to curate source records, evidence spans and episode units. Dates, author and independence groups must describe the actual sources.
4. Use `data/empty_real_pack_template.json` as the outer shape. It is intentionally empty and returns HOLD. Do not relabel the synthetic fixture as real.
5. Run the CLI on the curated pack; inspect every escalation and prepare expert corrections as structured events.
6. The current simple-clause engine intentionally cannot translate an arbitrary real episode. Add supported morphology and grammar rules plus adversarial tests before broadening its scope. Audio transcription and automatic document claim extraction are not implemented.

## Repository map

```text
submission/
  README.md
  ARCHITECTURE.md
  AI_COLLABORATION.md
  KNOWN_LIMITATIONS.md
  run.py
  pyproject.toml
  src/nadi9/
  tests/
  data/
  docs/
  sample_run/
  sample_run_corrected/
```

Read `docs/INTERVIEW_GUIDE.md` before the technical discussion and `docs/REQUIREMENTS_MATRIX.md` for implemented versus blocked requirements. Do not claim independent authorship, authentic translations or measured confidence calibration that this project does not establish.
