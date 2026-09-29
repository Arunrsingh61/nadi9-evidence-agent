"""Evidence-constrained offline subtitle pipeline. No network or API keys."""
from __future__ import annotations
import copy
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

VERSION = '1.0.0'
WORDS = re.compile(r"\w+(?:['’-]\w+)*", re.UNICODE)
REQUIRED = {'examples', 'grammar', 'dictionary_a', 'dictionary_b', 'feedback', 'expert', 'audio', 'episode'}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def tokens(text):
    return WORDS.findall(text)


def matches(scope, context):
    return all(context.get(k) == v for k, v in scope.items())


def group_key(record):
    return record['kind'] + ':' + record['key']


class PackError(ValueError):
    pass


class ToolFailure(RuntimeError):
    pass


@dataclass
class Budget:
    max_model: int = 25
    max_tool: int = 50
    model: int = 0
    tool: int = 0

    def spend(self, kind):
        limit = getattr(self, 'max_' + kind)
        used = getattr(self, kind)
        if used >= limit:
            raise ToolFailure(f'{kind} budget exhausted ({used}/{limit})')
        setattr(self, kind, used + 1)

    def as_dict(self):
        return vars(self).copy()


def validate_pack(pack):
    if pack.get('schema_version') != 1:
        raise PackError('schema_version must be 1')
    for field in ('sources', 'evidence', 'episode'):
        if not isinstance(pack.get(field), list):
            raise PackError(f'{field} must be a list')
    def unique(items):
        ids = [x['id'] for x in items]
        if len(ids) != len(set(ids)):
            raise PackError('duplicate identifiers')
    try:
        unique(pack['sources']); unique(pack['evidence']); unique(pack['episode'])
        sources = {s['id']: s for s in pack['sources']}
        for s in sources.values():
            for field in ('author', 'date', 'category', 'scope', 'reliability', 'independence_group', 'path'):
                if field not in s:
                    raise PackError(f"source {s['id']} missing {field}")
            if not 0 <= s['reliability'] <= 1:
                raise PackError('reliability must be in [0,1]')
        for e in pack['evidence']:
            if e['source_id'] not in sources:
                raise PackError('dangling source reference')
            if e['kind'] not in ('lex', 'grammar', 'raw', 'example'):
                raise PackError('unknown evidence kind')
            if not all(k in e for k in ('key', 'value', 'scope', 'locator')):
                raise PackError('incomplete evidence record')
            if e['kind'] == 'example' and not all(k in e for k in ('source_roles', 'source_values', 'target_values')):
                raise PackError('example requires aligned observations')
        for line in pack['episode']:
            if not isinstance(line['start_ms'], int) or not isinstance(line['end_ms'], int):
                raise PackError('integer millisecond timing required')
            if line['start_ms'] < 0 or line['end_ms'] <= line['start_ms']:
                raise PackError('invalid subtitle interval')
            if tokens(line['source_text']) != [u['text'] for u in line['units']]:
                raise PackError(f"{line['id']}: source units must cover source text exactly")
            if not isinstance(line['context'], dict):
                raise PackError('context must be an object')
            for u in line['units']:
                if u['role'] not in ('S', 'V', 'O', 'X'):
                    raise PackError('roles must be S/V/O/X')
                if u.get('preserve') not in (None, 'name', 'number', 'code_switch'):
                    raise PackError('invalid preservation class')
                if u.get('preserve') == 'number' and not u['text'].isnumeric():
                    raise PackError('preserved number must be numeric')
    except (KeyError, TypeError) as exc:
        raise PackError(f'malformed pack: {exc}') from exc


def learn_group(pack, key):
    """Use data-only observations. Raw prose can never become executable claims."""
    sources = {s['id']: s for s in pack['sources']}
    records = [e for e in pack['evidence'] if e.get('active', True)]
    claims = []
    for e in records:
        if group_key(e) != key or e['kind'] not in ('lex', 'grammar'):
            continue
        s = sources[e['source_id']]
        # Source authority cannot be supplied by retrieved text. Local pack curator sets it.
        weight = s['reliability']
        if s['category'] in ('feedback', 'dictionary_a', 'dictionary_b'):
            weight = min(weight, .75)
        claims.append(dict(e, weight=weight, independence=s['independence_group']))
    variants = []
    for value, scope in sorted({(e['value'], json.dumps(e['scope'], sort_keys=True)) for e in claims}):
        scoped = json.loads(scope)
        support = [e for e in claims if e['value'] == value and e['scope'] == scoped]
        counter = [e['id'] for e in claims if e['value'] != value and e['scope'] == scoped]
        tested = []
        if key == 'grammar:word_order':
            for example in records:
                if example['kind'] != 'example' or not matches(scoped, example['scope']):
                    continue
                order = ordered_indices(example['source_roles'], value)
                predicted = [example['source_values'][i] for i in order]
                passed = predicted == example['target_values']
                tested.append({'evidence': example['id'], 'passed': passed})
                if not passed:
                    counter.append(example['id'])
        origins = {e['independence'] for e in support if e['weight'] >= .5}
        score = max((e['weight'] for e in support), default=0)
        if len(origins) >= 2:
            score = min(.95, score + .1)
        # A single dictionary is insufficient; independent corroboration is required.
        supported = len(origins) >= 2 and score >= .7
        if key == 'grammar:word_order':
            test_origins = {sources[next(e['source_id'] for e in records if e['id'] == t['evidence'])]['independence_group'] for t in tested if t['passed']}
            supported = supported and len(test_origins) >= 2 and value in ('SVO', 'SOV')
        variants.append({'value': value, 'scope': scoped, 'support': [e['id'] for e in support],
                         'counterexamples': sorted(set(counter)), 'tests': tested,
                         'score': round(score, 2), 'supported': supported})
    return {'key': key, 'variants': variants}


def ordered_indices(roles, order):
    # X marks punctuation-free adjuncts. General syntax is intentionally unsupported.
    if order not in ('SVO', 'SOV'):
        return list(range(len(roles)))
    rank = {role: i for i, role in enumerate(order + 'X')}
    return sorted(range(len(roles)), key=lambda i: (rank[roles[i]], i))


def choose(hypothesis, context):
    variants = [v for v in hypothesis.get('variants', []) if matches(v['scope'], context)]
    if not variants:
        return None, [], []
    # Specific contextual meanings outrank broad senses, but remain visible in evidence.
    specificity = max(len(v['scope']) for v in variants)
    exact = [v for v in variants if len(v['scope']) == specificity]
    exact.sort(key=lambda v: (-v['score'], v['value']))
    selected = exact[0]
    conflicts = [v for v in exact if v['value'] != selected['value']]
    ids = sorted({eid for v in variants for eid in v['support'] + v['counterexamples'] + [t['evidence'] for t in v['tests']]})
    return selected, conflicts, ids


class ReplayProvider:
    """Protocol: propose(line, candidates, grammar, budget) -> proposal.

    This deterministic provider is not an LLM; model usage stays zero.
    A hosted provider must reserve budget.spend('model') before *each* attempt.
    """
    name = 'offline-replay'

    def __init__(self, fail_once=False):
        self.fail_once = fail_once

    def propose(self, line, candidates, grammar, budget):
        budget.spend('tool')
        if self.fail_once:
            self.fail_once = False
            raise ToolFailure('simulated transient provider failure')
        if grammar is None or any(c is None for c in candidates):
            return {'text': None, 'alignments': [], 'rule': None}
        order = ordered_indices([u['role'] for u in line['units']], grammar['value'])
        alignments = [{'unit': i, 'target': candidates[i]['value']} for i in order]
        return {'text': ' '.join(a['target'] for a in alignments), 'alignments': alignments, 'rule': grammar['value']}


def verify(line, proposal, knowledge, pack, previous_end):
    """Independent deterministic checks: recompute evidence choices, never trust scores from provider."""
    issues = []
    text = proposal.get('text')
    alignments = proposal.get('alignments', [])
    if text is None:
        return [{'code': 'NO_TRANSLATION', 'detail': 'Evidence or provider did not yield a complete proposal.'}]
    def flag(code, detail):
        issues.append({'code': code, 'detail': detail})
    indices = [a.get('unit') for a in alignments]
    if sorted(indices, key=str) != sorted(range(len(line['units'])), key=str):
        flag('COVERAGE', 'Every source unit must appear exactly once; omission, addition or duplicate detected.')
    for a in alignments:
        i = a.get('unit')
        if not isinstance(i, int) or i < 0 or i >= len(line['units']):
            flag('ALIGNMENT', 'Invalid unit index'); continue
        unit = line['units'][i]
        if unit.get('preserve'):
            if a.get('target') != unit['text']:
                flag('PRESERVATION', f"Name/number/code-switch changed: {unit['text']}")
        else:
            selected, conflicts, _ = choose(knowledge.get('lex:' + unit['text'].lower(), {}), line['context'])
            if selected is None or not selected['supported'] or selected['value'] != a.get('target'):
                flag('UNSUPPORTED_TERM', f"No corroborated support for {unit['text']} -> {a.get('target')}")
            if conflicts or (selected and selected['counterexamples']):
                flag('LEXICAL_CONFLICT', f"Conflicting evidence for {unit['text']}")
    grammar, conflicts, _ = choose(knowledge.get('grammar:word_order', {}), line['context'])
    if not grammar or not grammar['supported'] or proposal.get('rule') != grammar['value']:
        flag('UNSUPPORTED_GRAMMAR', 'Proposed order is not a corroborated, tested rule.')
    if grammar:
        if conflicts or grammar['counterexamples']:
            flag('GRAMMAR_CONFLICT', 'Rule has competing evidence or observed counterexamples.')
        expected = ordered_indices([u['role'] for u in line['units']], grammar['value'])
        if indices != expected:
            flag('WORD_ORDER', 'Target alignment order violates supported syntax.')
    if text != ' '.join(str(a.get('target', '')) for a in alignments):
        flag('ADDITION', 'Surface text differs from verified aligned tokens.')
    if '-->' in text or '\n' in text or '\r' in text:
        flag('FORMAT', 'Unsafe subtitle text formatting.')
    if line['start_ms'] < previous_end:
        flag('TIMING_OVERLAP', 'Cue overlaps an earlier cue.')
    seconds = (line['end_ms'] - line['start_ms']) / 1000
    if len(text) / seconds > pack.get('subtitle_policy', {}).get('max_cps', 17):
        flag('READING_SPEED', f'{len(text)/seconds:.1f} characters per second exceeds policy.')
    if len(text) > pack.get('subtitle_policy', {}).get('max_chars', 84):
        flag('LINE_LENGTH', 'Cue exceeds two-line character budget.')
    if any(len(word) > 42 for word in text.split()):
        flag('LINE_LENGTH', 'Unbreakable token exceeds 42 characters.')
    if any(x in line['context'] for x in ('humour', 'ambiguity', 'tone_risk')):
        flag('PRAGMATICS', 'Humour, ambiguity or tone needs expert interpretation.')
    if sorted(u['role'] for u in line['units']) != ['O', 'S', 'V']:
        flag('GRAMMAR_SCOPE', 'Only one subject, verb and object are supported by the simple-clause grammar.')
    return issues


class Engine:
    def __init__(self, pack, provider=None, budget=None):
        validate_pack(pack)
        self.pack = copy.deepcopy(pack)
        self.provider = provider or ReplayProvider()
        self.budget = budget or Budget()
        self.knowledge = {}
        self.decisions = {}
        self.audit = []
        self.revision = 0
        self.events = []

    def log(self, event, **fields):
        self.audit.append({'seq': len(self.audit) + 1, 'revision': self.revision, 'event': event, **fields})

    def learn(self, keys=None):
        if keys is None:
            keys = {group_key(e) for e in self.pack['evidence'] if e['kind'] in ('lex', 'grammar')}
        for key in sorted(keys):
            if key.startswith(('lex:', 'grammar:')):
                self.knowledge[key] = learn_group(self.pack, key)
                self.log('hypothesis_tested', key=key, hypothesis=self.knowledge[key])

    def dependencies(self, line):
        return sorted({'grammar:word_order'} | {'lex:' + u['text'].lower() for u in line['units'] if not u.get('preserve')})

    def risk(self, line):
        risk = 0
        for key in self.dependencies(line):
            selected, conflict, _ = choose(self.knowledge.get(key, {}), line['context'])
            risk += 3 if selected is None else 2 if conflict or not selected['supported'] or selected['counterexamples'] else 0
        return risk + 2 * sum(k in line['context'] for k in ('humour', 'ambiguity', 'tone_risk'))

    def translate(self, line):
        context = line['context']; refs = set(); conflicts = []; missing = []; scores = []
        candidates = []
        for unit in line['units']:
            if unit.get('preserve'):
                candidates.append({'value': unit['text'], 'supported': True}); continue
            key = 'lex:' + unit['text'].lower()
            candidate, clash, ids = choose(self.knowledge.get(key, {}), context)
            refs.update(ids); candidates.append(candidate)
            if candidate is None:
                missing.append(unit['text'])
            else:
                scores.append(candidate['score'])
                if clash or candidate['counterexamples']:
                    conflicts.append({'key': key, 'evidence': ids})
        grammar, clash, ids = choose(self.knowledge.get('grammar:word_order', {}), context)
        refs.update(ids)
        if grammar:
            scores.append(grammar['score'])
            if clash or grammar['counterexamples']:
                conflicts.append({'key': 'grammar:word_order', 'evidence': ids})
        errors = []; proposal = {'text': None, 'alignments': [], 'rule': None}
        for attempt in range(2):
            try:
                proposal = self.provider.propose(line, candidates, grammar, self.budget)
                if not isinstance(proposal, dict) or not isinstance(proposal.get('alignments'), list):
                    raise ToolFailure('malformed provider response')
                if proposal.get('text') is not None and not isinstance(proposal['text'], str):
                    raise ToolFailure('malformed provider text')
                if not all(isinstance(a, dict) and type(a.get('unit')) is int and isinstance(a.get('target'), str) for a in proposal['alignments']):
                    raise ToolFailure('malformed alignment')
                break
            except (ToolFailure, TimeoutError, ConnectionError) as exc:
                proposal = {'text': None, 'alignments': [], 'rule': None}
                errors.append(str(exc)); self.log('tool_failure', subtitle_id=line['id'], attempt=attempt+1, error=str(exc))
        previous_end = max((x['end_ms'] for x in self.pack['episode'] if (x['start_ms'], x['id']) < (line['start_ms'], line['id'])), default=0)
        issues = verify(line, proposal, self.knowledge, self.pack, previous_end)
        if errors and proposal.get('text') is None:
            issues.append({'code': 'TOOL_FAILURE', 'detail': '; '.join(errors)})
        status = 'INSUFFICIENT_EVIDENCE' if proposal.get('text') is None else 'HUMAN_REVIEW' if issues else 'APPROVED'
        confidence = min(scores, default=0) if status == 'APPROVED' else min(.45, min(scores, default=0)) if proposal.get('text') else 0
        question = None
        if missing:
            question = f"What is the evidenced Nadi-9 rendering of {', '.join(missing)} for context {json.dumps(context, ensure_ascii=False)}? Please cite an example."
        elif status != 'APPROVED':
            question = f"For {line['id']} in {json.dumps(context, ensure_ascii=False)}, resolve: " + '; '.join(i['detail'] for i in issues) + ' Please supply a scoped correction and supporting source.'
        decision = {'subtitle_id': line['id'], 'source_text': line['source_text'], 'nadi_9_text': proposal.get('text'),
                    'start_ms': line['start_ms'], 'end_ms': line['end_ms'], 'speaker': line.get('speaker'),
                    'confidence': round(confidence, 2), 'confidence_reason': 'Heuristic evidence score, NOT an empirically calibrated probability. Minimum corroborated claim score; review capped at 0.45; abstention 0.',
                    'decision': status, 'evidence': sorted(refs), 'assumptions': [f'{k}={v}' for k,v in sorted(context.items())] + ['Source-unit roles and preservation labels are human-curated.'],
                    'conflicts': conflicts, 'review_question': question, 'verification': issues,
                    'proposal': proposal, 'dependencies': self.dependencies(line), 'revision': self.revision,
                    'pack_hash': digest(self.pack), 'provider_errors': errors}
        self.decisions[line['id']] = decision
        self.log('subtitle_decided', decision=copy.deepcopy(decision))

    def run(self):
        self.learn()
        self.process(self.pack['episode'])
        return self

    def process(self, lines):
        plan = sorted(lines, key=lambda line: (-self.risk(line), line['start_ms'], line['id']))
        self.log('plan', items=[{'subtitle_id': x['id'], 'risk': self.risk(x)} for x in plan])
        for line in plan:
            self.translate(line)

    def correct(self, event):
        if event['id'] in {e['id'] for e in self.events}:
            raise PackError('duplicate correction event')
        # Only the local CLI control plane calls this method; retrieved prose never can.
        updated = copy.deepcopy(self.pack)
        by_id = {e['id']: e for e in updated['evidence']}
        changed = []
        for eid in event.get('invalidate', []):
            if eid not in by_id:
                raise PackError(f'unknown correction target {eid}')
            by_id[eid]['active'] = False; changed.append(by_id[eid])
        updated['sources'].extend(copy.deepcopy(event.get('sources', [])))
        for record in event.get('add', []):
            if record['id'] in by_id:
                raise PackError('correction evidence IDs must be new')
            updated['evidence'].append(copy.deepcopy(record)); changed.append(record)
        validate_pack(updated)  # Atomic validation before mutation.
        keys = {group_key(e) for e in changed if e['kind'] in ('lex', 'grammar')}
        if any(e['kind'] == 'example' for e in changed):
            keys.add('grammar:word_order')
        self.pack = updated; self.revision += 1; self.events.append(copy.deepcopy(event))
        self.learn(keys)
        affected = []
        for line in self.pack['episode']:
            if not keys.intersection(self.dependencies(line)):
                continue
            relevant = [e for e in changed if (group_key(e) in self.dependencies(line) or e['kind'] == 'example') and matches(e['scope'], line['context'])]
            if relevant or any(k.startswith('grammar:') for k in keys):
                affected.append(line)
        self.log('correction_applied', correction=event, changed_keys=sorted(keys), affected=[x['id'] for x in affected])
        self.process(affected)
        return [x['id'] for x in affected]

    def state(self):
        return {'version': VERSION, 'pack': self.pack, 'knowledge': self.knowledge, 'decisions': self.decisions,
                'audit': self.audit, 'revision': self.revision, 'events': self.events, 'budget': self.budget.as_dict()}

    @classmethod
    def restore(cls, state, provider=None):
        obj = cls(state['pack'], provider=provider, budget=Budget(**state['budget']))
        for field in ('knowledge', 'decisions', 'audit', 'revision', 'events'):
            setattr(obj, field, copy.deepcopy(state[field]))
        return obj


def stamp(ms):
    sec, millis = divmod(ms, 1000); minutes, seconds = divmod(sec, 60); hours, minutes = divmod(minutes, 60)
    return f'{hours:02}:{minutes:02}:{seconds:02},{millis:03}'


def write_outputs(engine, out):
    import textwrap
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        raise PackError('Output directory must be empty; use a new path to preserve audit history.')
    out.mkdir(parents=True, exist_ok=True)
    def dump(name, value):
        (out / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    decisions = sorted(engine.decisions.values(), key=lambda x: (x['start_ms'], x['subtitle_id']))
    review = [d for d in decisions if d['decision'] != 'APPROVED']
    categories = {s['category'] for s in engine.pack['sources']}
    missing = sorted(REQUIRED - categories)
    synthetic = engine.pack.get('synthetic', False)
    release = 'HOLD' if review or missing or synthetic or not decisions else 'READY_FOR_EXPERT_SIGNOFF'
    report = {'release': release, 'synthetic': synthetic, 'total_lines': len(decisions), 'approved': len(decisions)-len(review),
              'needs_review': len(review), 'missing_material_categories': missing, 'budget': engine.budget.as_dict(), 'pack_hash': digest(engine.pack)}
    dump('run_state.json', engine.state()); dump('learned_rules.json', engine.knowledge)
    dump('evidence_records.json', {'sources': engine.pack['sources'], 'evidence': engine.pack['evidence']})
    dump('review_queue.json', review); dump('release_report.json', report)
    for name, rows in [('subtitle_decisions.jsonl', decisions), ('audit_log.jsonl', engine.audit)]:
        (out/name).write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows), encoding='utf-8')
    cues = []; safe_cues = []
    for i, d in enumerate(decisions, 1):
        text = d['nadi_9_text'] or '[INSUFFICIENT EVIDENCE]'
        if d['decision'] != 'APPROVED':
            text = f"[{d['decision']}] {text}"
        text = text.replace('-->', '→').replace('\r', ' ').replace('\n', ' ')
        cues.append(f"{i}\n{stamp(d['start_ms'])} --> {stamp(d['end_ms'])}\n{textwrap.fill(text, width=42)}\n")
        if d['decision'] == 'APPROVED':
            safe_cues.append(f"{len(safe_cues)+1}\n{stamp(d['start_ms'])} --> {stamp(d['end_ms'])}\n{textwrap.fill(d['nadi_9_text'], width=42)}\n")
    (out/'subtitles.srt').write_text('\n'.join(cues), encoding='utf-8')
    (out/'approved_only.srt').write_text('\n'.join(safe_cues), encoding='utf-8')
    (out/'final_report.md').write_text(f"# Release recommendation: {release}\n\n" +
        ('**Synthetic engineering fixture. Not real Nadi-9. Never publish these subtitles.**\n\n' if synthetic else '') +
        f"{len(decisions)} lines; {len(decisions)-len(review)} approved by deterministic checks; {len(review)} require review.\n\n" +
        f"Missing material categories: {', '.join(missing) or 'none (inventory only; completeness not guaranteed)'}.\n\n" +
        'subtitles.srt is a REVIEW COPY containing explicit review markers. approved_only.srt is incomplete when lines are withheld; it is not a release asset. Human signoff is always required.\n\n' +
        f"Budget: {engine.budget.model}/{engine.budget.max_model} model calls, {engine.budget.tool}/{engine.budget.max_tool} tool calls.\n\n" +
        'Review questions and check failures are in review_queue.json. Each evidence ID resolves in evidence_records.json; decisions retain pack hashes and revisions.\n', encoding='utf-8')
    return report
