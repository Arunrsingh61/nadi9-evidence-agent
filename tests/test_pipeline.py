import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from nadi9.core import Budget, Engine, PackError, ReplayProvider, ToolFailure, verify, write_outputs
ROOT=Path(__file__).resolve().parents[1]


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.pack=json.loads((ROOT/'data/synthetic_pack.json').read_text())

    def test_supported_line(self):
        d=Engine(self.pack).run().decisions['S001']
        self.assertEqual(d['decision'],'APPROVED')
        self.assertEqual(d['nadi_9_text'],'mi naru vek')
        self.assertIn('example-01',d['evidence'])

    def test_dictionary_conflict(self):
        d=Engine(self.pack).run().decisions['S002']
        self.assertEqual(d['decision'],'HUMAN_REVIEW')
        self.assertTrue(d['conflicts'])

    def test_unsupported_term_abstains(self):
        d=Engine(self.pack).run().decisions['S003']
        self.assertIsNone(d['nadi_9_text'])
        self.assertIn('moon',d['review_question'])

    def test_correction_only_impacted_line(self):
        e=Engine(self.pack).run(); before=copy.deepcopy(e.decisions)
        affected=e.correct(json.loads((ROOT/'data/correction.json').read_text()))
        self.assertEqual(affected,['S002'])
        self.assertEqual(e.decisions['S002']['decision'],'APPROVED')
        for key in set(before)-{'S002'}: self.assertEqual(before[key],e.decisions[key])
        self.assertEqual(e.budget.tool,8)

    def test_new_evidence_revisits_previously_unknown_term(self):
        e=Engine(self.pack).run()
        records=[]
        for id,source in [('moon-A','dict-a'),('moon-B','dict-b')]:
            records.append(dict(id=id,source_id=source,kind='lex',key='moon',value='luno',scope={},locator=id))
        self.assertEqual(e.correct(dict(id='new-term',add=records)),['S003'])
        self.assertEqual(e.decisions['S003']['decision'],'APPROVED')

    def test_failed_tool_retry(self):
        e=Engine(self.pack,ReplayProvider(fail_once=True)).run()
        self.assertEqual(e.budget.tool,8)
        self.assertEqual(e.decisions['S001']['decision'],'APPROVED')
        self.assertTrue(any(a['event']=='tool_failure' for a in e.audit))

    def test_persistent_failure_safe(self):
        class Broken(ReplayProvider):
            def propose(self,line,candidates,grammar,budget):
                budget.spend('tool'); raise ToolFailure('offline')
        e=Engine(self.pack,Broken()).run()
        self.assertTrue(all(d['nadi_9_text'] is None for d in e.decisions.values()))
        self.assertEqual(e.budget.tool,14)

    def test_budget_cap(self):
        e=Engine(self.pack,budget=Budget(max_tool=2)).run()
        self.assertEqual(e.budget.tool,2)
        self.assertTrue(any(d['decision']=='INSUFFICIENT_EVIDENCE' for d in e.decisions.values()))

    def test_injected_instructions_are_data(self):
        e=Engine(self.pack).run()
        self.assertNotIn('raw:comment',e.knowledge)
        self.assertEqual(e.decisions['S003']['decision'],'INSUFFICIENT_EVIDENCE')

    def test_fabricated_model_grammar_rejected(self):
        class Hallucinating(ReplayProvider):
            def propose(self,*args):
                p=super().propose(*args); p['rule']='VSO'; return p
        e=Engine(self.pack,Hallucinating()).run()
        self.assertIn('UNSUPPORTED_GRAMMAR',[x['code'] for x in e.decisions['S001']['verification']])

    def test_relationship_sense(self):
        e=Engine(self.pack).run()
        self.assertEqual(e.decisions['S004']['nadi_9_text'],'tira ara salu')
        self.assertEqual(e.decisions['S004']['decision'],'APPROVED')

    def test_approved_example_revoked(self):
        e=Engine(self.pack).run()
        affected=e.correct(dict(id='withdraw',invalidate=['example-01','example-02']))
        self.assertEqual(len(affected),7)
        self.assertNotEqual(e.decisions['S001']['decision'],'APPROVED')

    def test_counterexample_visible(self):
        self.pack['evidence'].append(dict(id='counter',source_id='example-2',kind='example',key='word_order',value='SVO',scope={'tense':'present'},locator='counterexample',source_roles=['S','V','O'],source_values=['mi','vek','naru'],target_values=['mi','vek','naru']))
        e=Engine(self.pack).run()
        self.assertEqual(e.decisions['S001']['decision'],'HUMAN_REVIEW')
        self.assertIn('counter',e.knowledge['grammar:word_order']['variants'][0]['counterexamples'])

    def test_bad_timing_rejected(self):
        self.pack['episode'][0]['end_ms']=0
        with self.assertRaises(PackError): Engine(self.pack)

    def test_overlap_and_reading_speed(self):
        self.pack['episode'][1]['start_ms']=100
        self.pack['episode'][1]['end_ms']=200
        d=Engine(self.pack).run().decisions['S002']
        codes={x['code'] for x in d['verification']}
        self.assertTrue({'TIMING_OVERLAP','READING_SPEED'} <= codes)

    def test_omission_and_addition_independent_check(self):
        e=Engine(self.pack).run(); line=self.pack['episode'][0]
        p=copy.deepcopy(e.decisions['S001']['proposal']); p['alignments'].pop(); p['text']+=' SECRET'
        codes={x['code'] for x in verify(line,p,e.knowledge,self.pack,0)}
        self.assertTrue({'COVERAGE','ADDITION'} <= codes)

    def test_name_and_number_preservation(self):
        e=Engine(self.pack).run()
        for id,index in [('S005',4),('S006',5)]:
            p=copy.deepcopy(e.decisions[id]['proposal'])
            next(a for a in p['alignments'] if a['unit']==2)['target']='wrong'
            codes={x['code'] for x in verify(self.pack['episode'][index],p,e.knowledge,self.pack,0)}
            self.assertIn('PRESERVATION',codes)

    def test_single_origin_cannot_corroborate_itself(self):
        self.pack['sources'][1]['independence_group']='vendor'
        e=Engine(self.pack).run()
        self.assertNotEqual(e.decisions['S001']['decision'],'APPROVED')

    def test_snapshot_resume_preserves_budget_and_audit(self):
        e=Engine(self.pack).run(); restored=Engine.restore(json.loads(json.dumps(e.state())))
        self.assertEqual(e.state(),restored.state())
        restored.correct(json.loads((ROOT/'data/correction.json').read_text()))
        self.assertEqual(restored.budget.tool,8)

    def test_synthetic_release_hold_and_evidence_resolution(self):
        e=Engine(self.pack).run()
        with tempfile.TemporaryDirectory() as folder:
            report=write_outputs(e,folder)
            self.assertEqual(report['release'],'HOLD')
            self.assertEqual(report['approved'],4)
            self.assertTrue((Path(folder)/'subtitles.srt').exists())
            with self.assertRaises(PackError): write_outputs(e,folder)
        evidence={x['id'] for x in self.pack['evidence']}
        for d in e.decisions.values(): self.assertTrue(set(d['evidence']) <= evidence)

    def test_invalid_correction_atomic(self):
        e=Engine(self.pack).run(); before=copy.deepcopy(e.state())
        with self.assertRaises(PackError): e.correct(dict(id='bad',invalidate=['nonexistent']))
        self.assertEqual(e.state(),before)

    def test_malformed_provider_response(self):
        class Malformed(ReplayProvider):
            def propose(self,line,candidates,grammar,budget):
                budget.spend('tool'); return {'text':'fake','alignments':[None]}
        e=Engine(self.pack,Malformed()).run()
        self.assertTrue(all(d['decision']=='INSUFFICIENT_EVIDENCE' for d in e.decisions.values()))

    def test_unseen_tense_abstains(self):
        self.pack['episode'][0]['context']['tense']='past'
        e=Engine(self.pack).run()
        self.assertEqual(e.decisions['S001']['decision'],'INSUFFICIENT_EVIDENCE')

    def test_empty_pack_hold(self):
        pack=json.loads((ROOT/'data/empty_real_pack_template.json').read_text())
        e=Engine(pack).run()
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(write_outputs(e,folder)['release'],'HOLD')


if __name__=='__main__': unittest.main()
