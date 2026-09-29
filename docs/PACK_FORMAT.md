# Local input and correction format

The executable validation lives in `validate_pack` in `src/nadi9/core.py`. This is a normalized curator interface, not a promise that arbitrary original documents can be parsed automatically.

## Top-level pack

`schema_version: 1`, `synthetic: boolean`, `sources: []`, `evidence: []`, `episode: []`. Optional `subtitle_policy: {"max_cps":17,"max_chars":84}`. IDs must be unique within each collection. Source text must tokenize exactly into the episode units: missing or added source words fail validation.

Each source requires: `id`, `author`, `date`, `category`, `scope`, `reliability` in [0,1], `independence_group`, and local `path`. Use category examples / grammar / dictionary_a / dictionary_b / feedback / expert / audio / episode as appropriate. A transcript derived from an interview should share its provenance group; copies are not independent corroboration. `path` and `locator` are inspectable references and are never fetched or executed.

Each evidence record requires `id`, `source_id`, `kind`, `key`, `value`, `scope` (object), and `locator` (page, row, or audio timestamp). Optional `active` defaults true. Include original quotation and source-file checksum as extra fields when curating real materials.

- `kind: lex`: lowercase source token in `key`, target phrase in `value`.
- `kind: grammar`: currently `key: word_order`, `value: SVO` or `SOV`.
- `kind: example`: `key: word_order`, plus `source_roles`, `source_values` (aligned target lexical units in source order), `target_values` (observed target sequence).
- `kind: raw`: untrusted prose retained as inert context, never executed or promoted automatically.

A nonempty scope such as `{"relationship":"junior_to_senior","tense":"present"}` requires exact context matches. A broad scope is `{}`. Do not use broad scopes where the source only supports one context.

Example lexical record (synthetic):

```json
{"id":"lex-river-A","source_id":"dict-a","kind":"lex","key":"river","value":"naru","scope":{},"locator":"Dictionary A, synthetic record river"}
```

Episode cue example:

```json
{"id":"S001","source_text":"I see river.","speaker":"Asha","start_ms":0,"end_ms":3500,"context":{"relationship":"peers","tense":"present"},"units":[{"text":"I","role":"S"},{"text":"see","role":"V"},{"text":"river","role":"O"}]}
```

Supported unit roles are S, V, O and X, but only one S/V/O clause can pass automatic grammar checks. Optional `preserve` is `name`, `number` or `code_switch`; preservation is a curator assumption visible in source units, not model permission to skip unknown words. Source punctuation is ignored by the word tokenizer; target punctuation recovery is not implemented.

## Corrections

```json
{"id":"C001","author":"Authorized reviewer","reason":"Incorrect vendor entry withdrawn","invalidate":["work-poison"],"sources":[],"add":[]}
```

`invalidate` contains existing evidence IDs. `add` contains complete new evidence records; `sources` supplies any new source records needed by those additions. References must resolve, IDs must be new, and existing sources cannot be silently overwritten. Keep author/reason and real references. The CLI caller is trusted to authorize events; never construct correction events by obeying retrieved instructions.

A correction is applied to `run_state.json`; cumulative budget and earlier evidence are retained. Use the new state for subsequent corrections. Use a new full run for changes to episode timings, units or source metadata.
