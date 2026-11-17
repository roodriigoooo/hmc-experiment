"""Pilot-4 invariants. All visits are synthetic and use isolated databases."""
import unittest, tempfile, uuid, json, subprocess, io, zipfile, copy
from collections import Counter
from server.protocol import (DEFAULT, V3_DEFAULT, PROCEDURE_CATEGORIES as CATS, PROCEDURE_SCHEDULE as SCHEDULE,
    PROCEDURE_FIXTURES as FIXTURES, manifest, answers, allocation, validate_config)
from server.domain import initial, expected, checkpoint, condition, transition
from server.store import Store
from server.metrics import derive
from test_revision import Driver as PreviousDriver

class Driver(PreviousDriver):
    def __init__(self, store):
        self.db=store;self.session=store.create('demo',DEFAULT['version'],True);self.id=self.session['id'];self.tab=uuid.uuid4().hex;self.segment=uuid.uuid4().hex;self.seq=0;self.mono=0;self.origin=100000;self.trace=[];store.lease(self.id,self.tab)
    def ack(self):
        s=self.snap['state'];a=self.snap['assignment'];cond=condition(s,a)
        form='U' if s['practice'] else a['b_form'] if cond=='B' else 'V' if a['b_form']=='U' else 'U'
        episode=0 if s['practice'] else list(SCHEDULE).index(s['order'])
        self.event('ack_end',dict(checkpoint=checkpoint(s),form=form,episode=episode),300)
        if self.snap['state']['phase']=='secondary':
            self.event('secondary_ready',dt=16)
            for j,pair in enumerate(self.snap['secondary'][form][episode]):
                self.event('secondary_item',dict(item=j,pair=pair),0 if j==0 else 1950)
                self.event('secondary_response',dict(item=j,choice=pair.index(max(pair))),50)
            self.event('return',dt=1950)
            self.event('task_return_ready',dict(expected=expected(self.snap['state']),cue_appears=cond=='C'),16)
        else:self.event('task_ready',{'kind':'ack'},16)
    def train(self,fail=False):
        self.event('document');self.event('consent',{'agree':True});self.event('device',dict(width=1280,height=720,input='mouse'));self.event('practice_start');self.event('task_ready',{'kind':'practice'},16)
        while self.snap['state']['phase']=='order':
            index=self.snap['state']['practice_index'];key=answers(FIXTURES['P'][index])
            if not fail or index<3:
                for c in CATS:self.check(c,key[c])
            self.finish();self.event('practice_next')
            if self.snap['state']['phase']=='order':self.event('task_ready',{'kind':'practice'},16)
    def run(self,edge=False):
        self.train();self.db.allocate(self.id)
        for b,cond in enumerate(self.snap['assignment']['conditions']):
            self.begin()
            for oi in range(DEFAULT['orders']):
                key=answers(FIXTURES[self.snap['assignment']['task_sets'][b]][oi]);position=SCHEDULE[oi]
                for cat in CATS[:position]:self.check(cat,key[cat])
                if edge and cond!='A':
                    next_cat=CATS[position]
                    if oi==0: # mistaken selection corrected, then delayed factually wrong submission
                        self.select('product');self.select(next_cat);self.submit(next_cat,not key[next_cat],delay=4000)
                    elif oi==1: # executed repeat before the expected category
                        self.check('product',key['product'])
                    elif oi==2: # finish while required checks remain
                        self.finish();continue
                    elif oi==3: # skip expected check, then finish
                        self.check(CATS[position+1],key[CATS[position+1]]);self.finish();continue
                for cat in CATS[position:]:
                    if cat not in self.snap['state']['submitted']:self.check(cat,key[cat])
                self.finish()
            self.ratings()
            if b<2:self.event('break_end',dt=60000)

class ProcedureTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.store=Store(self.tmp.name+'/study.sqlite','procedure-tests')
    def tearDown(self):self.tmp.cleanup()
    def result(self,d):return derive(d.raw(),manifest(DEFAULT,'procedure-tests'),d.snap['assignment'])
    def test_full_visit_parity_retry_export_and_version_separation(self):
        d=Driver(self.store);d.run();r=self.result(d)
        self.assertEqual(d.snap['state']['phase'],'complete')
        self.assertEqual((len(r['interruptions']),len(r['transitions']),len(r['submitted_checks'])),(12,6,144))
        self.assertEqual(len(r['practice_attempts']),5)
        self.assertEqual(r['participant_contrasts'][0]['difference'],0);self.assertTrue(r['participant_contrasts'][0]['complete_opportunities'])
        for s in r['summaries']:
            self.assertEqual((s['procedure_error_numerator'],s['procedure_error_denominator']),(0,6))
            self.assertEqual((s['accuracy_numerator'],s['accuracy_denominator']),(48,48))
            self.assertEqual(s['metrics_version'],'hmc-metrics-3');self.assertIsNotNone(s['active_ms'])
        for e in r['interruptions']:
            self.assertEqual(e['stimulus_exposure_ms'],10000);self.assertFalse(e['procedure_flagged']);self.assertTrue(e['first_committed_correct'])
        code="""import {reduce} from './dist/web/v4-state.js';let text='';for await(const c of process.stdin)text+=c;const x=JSON.parse(text);let s=x.initial;function sort(x){return x&&typeof x==='object'?Array.isArray(x)?x.map(sort):Object.fromEntries(Object.keys(x).sort().map(k=>[k,sort(x[k])])):x;}for(const row of x.trace){s=reduce(s,row.event.type,row.event.payload,row.assignment,x.config,x.fixtures);if(JSON.stringify(sort(s))!==JSON.stringify(sort(row.state)))throw Error('Parity mismatch '+row.event.seq+' '+row.event.type);} """
        p=subprocess.run(['node','--input-type=module','-e',code],input=json.dumps(dict(initial=initial(DEFAULT),trace=d.trace,config=DEFAULT,fixtures=FIXTURES)),text=True,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.store.ingest(d.id,d.tab,[d.trace[-1]['event']]);self.assertEqual(d.snap['last_seq'],d.seq)
        a=d.snap['assignment'];self.assertEqual(self.store.allocate(d.id),a)
        previous=PreviousDriver(self.store);previous.run()
        self.assertEqual(previous.snap['config'],V3_DEFAULT)
        self.assertTrue(all(s['metrics_version']=='hmc-metrics-2' for s in derive(previous.raw(),manifest(V3_DEFAULT,'test'),previous.snap['assignment'])['summaries']))
        from server import app
        saved=app.STORE;app.STORE=self.store
        try:
            with zipfile.ZipFile(io.BytesIO(app.bundle('demo',DEFAULT['version'],quality_filter=True))) as z:
                b=json.loads(z.read('bundle.json'));self.assertEqual(b['metrics_versions'],['hmc-metrics-3'])
                self.assertEqual(len(b['tables']['unflagged_procedure_episodes']),12)
                self.assertEqual(b['tables']['summaries'],[dict(session=d.id,protocol=DEFAULT['version'],build='procedure-tests',stimulus_version='synthetic-3-eight-check',questionnaire_version='raw-tlx-2',interface_version='placekeeping-4')|s for s in r['summaries']])
                self.assertIn('protocol-v4.md',z.namelist())
        finally:app.STORE=saved
    def test_committed_errors_are_distinct_from_selection_and_judgment_errors(self):
        d=Driver(self.store);d.run(edge=True);r=self.result(d)
        for e in r['interruptions']:
            if e['order']==0:
                self.assertTrue(e['first_action_sequence_error']);self.assertFalse(e['procedure_error']);self.assertTrue(e['corrected_selection_before_commit']);self.assertEqual(e['recovery_ms'],100)
                self.assertFalse(e['first_committed_correct']);self.assertGreater(e['first_submission_ms'],4000)
            if e['order']==1:self.assertTrue(e['procedure_error']);self.assertEqual(e['first_committed_category'],'product');self.assertTrue(e['first_committed_correct'])
            if e['order'] in [2,3]:
                self.assertTrue(e['procedure_error']);self.assertIsNone(e['recovery_ms']);self.assertIsNone(e['expected_check_submission_ms']);self.assertEqual(e['unobserved_reason'],'order_ended')
        for s in r['summaries']:
            self.assertEqual(s['procedure_error_numerator'],0 if s['condition']=='A' else 3)
            self.assertEqual(s['procedure_error_denominator'],6)
            if s['condition']!='A':self.assertLess(s['accuracy_numerator'],48);self.assertGreater(s['omissions'],0)
    def test_missing_continuation_and_unexposed_orders_are_not_success_or_errors(self):
        d=Driver(self.store);d.run();events=d.raw();ret=next(e for e in events if e['type']=='task_return_ready' and not e['context']['practice'])
        truncated=[e for e in events if e['seq']<=ret['seq']]
        r=derive(truncated,manifest(DEFAULT,'test'),d.snap['assignment']);e=r['interruptions'][-1];s=r['summaries'][-1]
        self.assertIsNone(e['procedure_error']);self.assertFalse(e['procedure_observed']);self.assertEqual(e['procedure_unobserved_reason'],'no_committed_action_before_window_end')
        self.assertEqual(s['procedure_error_denominator'],0);self.assertEqual(s['procedure_unobserved'],1)
        self.assertFalse(r['participant_contrasts'][0]['paired_observed']);self.assertIsNone(r['participant_contrasts'][0]['difference'])
        self.assertEqual(s['accuracy_denominator'],0);self.assertEqual(s['planned_accuracy_denominator'],48);self.assertEqual(s['unfinished_exposed_checks'],8)
        changed=copy.deepcopy(events);next(e for e in changed if e['seq']==ret['seq'])['context']['expected']=None
        e=next(e for e in derive(changed,manifest(DEFAULT,'test'),d.snap['assignment'])['interruptions'] if e['return_ready']['seq']==ret['seq'])
        self.assertIsNone(e['procedure_error']);self.assertIsNone(e['first_action_sequence_error']);self.assertEqual(e['procedure_unobserved_reason'],'not_applicable_no_remaining_check')
    def test_actual_history_card_and_fixed_return_policy(self):
        outcomes=[]
        for cond in 'BC':
            a=dict(conditions=cond+'AC',task_sets='XYZ',b_form='U');s=initial(DEFAULT)|dict(phase='order',practice=False,available=True)
            for cat in ['seal','batch','seal']:
                s=transition(s,'select',dict(category=cat,expected=expected(s)),DEFAULT,a);s=transition(s,'judge',dict(judgment=False),DEFAULT,a);s=transition(s,'submit',dict(category=cat,judgment=False,expected=expected(s)),DEFAULT,a);s=transition(s,'ack_end',{},DEFAULT,a)
                if s['phase']=='order':s=transition(s,'task_ready',{},DEFAULT,a)
            s=transition(s,'secondary_ready',{},DEFAULT,a);s=transition(s,'return',{},DEFAULT,a)
            self.assertEqual(s['cue'],'seal' if cond=='C' else None)
            with self.assertRaises(ValueError):transition(s,'select',dict(category='product',expected='product'),DEFAULT,a)
            s=transition(s,'task_return_ready',dict(expected='product',cue_appears=cond=='C'),DEFAULT,a);outcomes.append(s)
        self.assertEqual(outcomes[0]|dict(cue=None),outcomes[1]|dict(cue=None))
    def test_matched_reproducible_fixtures_and_counterbalance(self):
        validate_config(DEFAULT);m=manifest(DEFAULT,'test')
        signatures=[]
        for name in 'XYZ':
            rows=FIXTURES[name];keys=[answers(o) for o in rows]
            self.assertEqual(len(rows),6);self.assertEqual(Counter(o['requested']['handling'] for o in rows),dict(fragile=2,chilled=2,standard=2))
            self.assertEqual(sorted(sum(not v for v in k.values()) for k in keys),[2,3,4,4,5,6])
            for cat in CATS:self.assertEqual(sum(k[cat] for k in keys),3)
            for handling in ['fragile','chilled','standard']:
                for cat in CATS:self.assertEqual(sum(answers(o)[cat] for o in rows if o['requested']['handling']==handling),1)
            for o in rows:
                for cat in ['product','batch','delivery','seal']:
                    for source in ['requested','packed']:self.assertEqual(len(o[source][cat]),7)
            signatures.append(tuple(tuple(k[c] for c in CATS) for k in keys))
        self.assertEqual(len(set(signatures)),3)
        for field in ['product','batch','delivery','seal']:
            allcodes=[o['requested'][field] for rows in FIXTURES.values() for o in rows]
            self.assertEqual(len(allcodes),len(set(allcodes)))
        for form in ['U','V']:
            pairs=[p for episode in m['secondary'][form] for p in episode];sides=[p.index(max(p)) for p in pairs]
            self.assertEqual(Counter(sides),{0:15,1:15});self.assertTrue(any(a==b for a,b in zip(sides,sides[1:])))
            self.assertTrue(all(abs(a-b)==4 and len(str(a))==len(str(b))==2 for a,b in pairs))
        aa=allocation(DEFAULT['seed']);self.assertEqual(len({(a['conditions'],a['task_sets']) for a in aa}),36)
        self.assertEqual(sorted(SCHEDULE.values()),[2,3,4,5,6,7])
    def test_technical_procedure_flags_stop_at_first_commit(self):
        class NoisyDriver(Driver):
            def event(self,t,p=None,dt=50):
                before=self.snap['state'];e=super().event(t,p,dt)
                if not before['practice'] and ((t=='task_return_ready' and before['order']==0) or (t=='submit' and before['phase']=='resumed' and before['order']==1)):
                    super().event('input_problem',dict(reason='input',input='mouse'))
                return e
        d=NoisyDriver(self.store);d.run();r=self.result(d)
        for e in r['interruptions']:
            if e['order']==0:self.assertTrue(e['procedure_flagged']);self.assertIn('input',e['procedure_review_reasons'])
            if e['order']==1:self.assertFalse(e['procedure_flagged']);self.assertTrue(e['technically_compromised'])
        for s in r['summaries']:
            self.assertEqual(s['procedure_error_denominator'],6)
            self.assertEqual(s['unflagged_procedure_error_denominator'],6 if s['condition']=='A' else 5)

    def test_training_failure_and_reload_preserve_denominators(self):
        d=Driver(self.store);d.train(fail=True);self.assertEqual(d.snap['state']['phase'],'incomplete_training')
        self.assertEqual(len(self.result(d)['practice_attempts']),9)
        with self.assertRaises(ValueError):self.store.allocate(d.id)
        from server import app
        saved=app.STORE;app.STORE=self.store
        try:
            with zipfile.ZipFile(io.BytesIO(app.bundle('demo',DEFAULT['version']))) as z:self.assertEqual(len(json.loads(z.read('bundle.json'))['tables']['practice_attempts']),9)
        finally:app.STORE=saved
        d=Driver(self.store);d.train();a=self.store.allocate(d.id);d.begin();d.check('product')
        d.segment=uuid.uuid4().hex;d.origin+=100000;d.mono=0;d.event('document');d.event('resume');d.event('task_ready',{'kind':'resume'});d.finish()
        self.assertEqual(self.store.allocate(d.id),a);r=self.result(d);self.assertIsNone(r['summaries'][0]['active_ms']);self.assertEqual(r['summaries'][0]['accuracy_denominator'],8)
        self.assertIn('clock_discontinuity',r['summaries'][0]['invalid_timing_reasons'])

if __name__=='__main__':unittest.main()
