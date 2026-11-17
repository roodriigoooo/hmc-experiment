import unittest,tempfile,uuid,json,io,zipfile,subprocess,copy
from server.protocol import V3_DEFAULT as DEFAULT,LEGACY_DEFAULT,FIXTURES,LEGACY_FIXTURES,manifest,answers,CATEGORIES,SCHEDULE,allocation,canonical
from server.domain import initial,expected,condition,checkpoint,transition
from server.store import Store
from server.metrics import derive,union
from server.questionnaire import ITEMS,TLX_KEYS,score
from test_study import Driver as LegacyDriver

class Driver:
    def __init__(self,store):
        self.db=store;self.session=store.create('demo',DEFAULT['version'],True);self.id=self.session['id'];self.tab=uuid.uuid4().hex;self.segment=uuid.uuid4().hex;self.seq=0;self.mono=0;self.origin=100000;self.trace=[];store.lease(self.id,self.tab)
    @property
    def snap(self):return self.db.snapshot(self.id)
    def event(self,t,p=None,dt=50):
        e=dict(id=uuid.uuid4().hex,seq=self.seq+1,segment=self.segment,origin=self.origin,mono=self.mono+dt,type=t,payload=p or {})
        a=self.snap['assignment'];self.db.ingest(self.id,self.tab,[e]);self.seq+=1;self.mono+=dt
        self.trace.append(dict(event=e,assignment=a,state=self.snap['state']));return e
    def raw(self):
        with self.db.db() as db:return [json.loads(r['body'])|{'context':json.loads(r['context'])} for r in db.execute('SELECT * FROM events WHERE session=? ORDER BY seq',(self.id,))]
    def select(self,c):return self.event('select',dict(category=c,expected=expected(self.snap['state']),cue_removed=self.snap['state']['cue'] is not None,input='mouse'))
    def submit(self,c,value,delay=50):
        self.event('judge',{'judgment':value},dt=delay)
        e=self.event('submit',dict(category=c,judgment=value,expected=expected(self.snap['state'])))
        self.ack();return e
    def check(self,c,value=True,delay=50):self.select(c);return self.submit(c,value,delay)
    def ack(self):
        s=self.snap['state'];a=self.snap['assignment'];cond=condition(s,a);form='U' if s['practice'] else a['b_form'] if cond=='B' else 'V' if a['b_form']=='U' else 'U';episode=0 if s['practice'] else list(SCHEDULE).index(s['order']) if s['order'] in SCHEDULE else -1
        self.event('ack_end',dict(checkpoint=checkpoint(s),form=form,episode=episode),300)
        if self.snap['state']['phase']=='secondary':
            self.event('secondary_ready',dt=16)
            for j,pair in enumerate(self.snap['secondary'][form][episode]):
                self.event('secondary_item',dict(item=j,pair=pair),0 if j==0 else 1950)
                self.event('secondary_response',dict(item=j,choice=pair.index(max(pair))),50)
            self.event('return',dt=1950);self.event('task_return_ready',dict(expected=expected(self.snap['state']),cue_appears=cond=='C'),16)
        else:self.event('task_ready',{'kind':'ack'},16)
    def finish(self):
        e=self.event('finish',dict(expected=expected(self.snap['state']),cue_removed=self.snap['state']['cue'] is not None))
        if self.snap['state']['phase']=='order':self.event('task_ready',{'kind':'order'},16)
        return e
    def train(self,fail=False):
        self.event('document');self.event('consent',{'agree':True});self.event('device',dict(width=1280,height=720,input='mouse'));self.event('practice_start');self.event('task_ready',{'kind':'practice'},16)
        while self.snap['state']['phase']=='order':
            index=self.snap['state']['practice_index'];key=answers(FIXTURES['P'][index])
            if not fail or index<3:
                for c in CATEGORIES:self.check(c,key[c])
            self.finish();self.event('practice_next')
            if self.snap['state']['phase']=='order':self.event('task_ready',{'kind':'practice'},16)
    def begin(self):self.event('block_start');self.event('task_ready',{'kind':'block'},16)
    def ratings(self):
        values={q['key']:20 for q in ITEMS};values['performance']=0;values['tracking']=100
        for k,v in values.items():self.event('questionnaire_item',dict(key=k,value=v))
        self.event('questionnaire',values)
    def run(self,edge=False):
        self.train();self.db.allocate(self.id)
        for b,cond in enumerate(self.snap['assignment']['conditions']):
            self.begin()
            for oi in range(12):
                key=answers(FIXTURES[self.snap['assignment']['task_sets'][b]][oi])
                self.check('product',key['product']);self.check('quantity',key['quantity'])
                if edge and cond!='A' and oi in [1,4,9]:
                    if oi==1:
                        self.select('delivery');self.select('packaging');self.submit('packaging',not key['packaging'],delay=4000)
                    elif oi==4:self.check('delivery',key['delivery'])
                    # oi 9 ends with no deliberate category selection.
                else:self.check('packaging',key['packaging']);self.check('delivery',key['delivery'])
                self.finish()
            self.ratings()
            if b<2:self.event('break_end',dt=60000)

class RevisionTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.store=Store(self.tmp.name+'/study.sqlite','revision-tests')
    def tearDown(self):self.tmp.cleanup()
    def result(self,d):return derive(d.raw(),manifest(DEFAULT,'revision-tests'),d.snap['assignment'])
    def test_complete_session_and_frontend_backend_parity(self):
        d=Driver(self.store);d.run();r=self.result(d)
        self.assertEqual(d.snap['state']['phase'],'complete');self.assertEqual(len(r['interruptions']),12);self.assertEqual(len(r['transitions']),6);self.assertEqual(len(r['secondary_items']),60)
        self.assertEqual(len(r['practice_attempts']),5)
        for s in r['summaries']:
            self.assertEqual((s['accuracy_numerator'],s['accuracy_denominator']),(48,48));self.assertIsNotNone(s['active_ms']);self.assertEqual(s['raw_tlx'],100/6)
        for e in r['interruptions']:
            self.assertEqual(e['stimulus_exposure_ms'],10000);self.assertEqual(e['secondary_correct'],5);self.assertFalse(e['technically_compromised']);self.assertTrue(e['expected_submission_observed'])
        code="""import {reduce} from './dist/web/state.js';let text='';for await(const c of process.stdin)text+=c;const x=JSON.parse(text);let s=x.initial;for(const row of x.trace){s=reduce(s,row.event.type,row.event.payload,row.assignment,x.config,x.fixtures);if(JSON.stringify(sort(s))!==JSON.stringify(sort(row.state)))throw Error('Parity mismatch '+row.event.seq+' '+row.event.type+' '+JSON.stringify(s)+' vs '+JSON.stringify(row.state));}function sort(x){return x&&typeof x==='object'?Array.isArray(x)?x.map(sort):Object.fromEntries(Object.keys(x).sort().map(k=>[k,sort(x[k])])):x;}"""
        p=subprocess.run(['node','--input-type=module','-e',code],input=json.dumps(dict(initial=initial(DEFAULT),trace=d.trace,config=DEFAULT,fixtures=FIXTURES)),text=True,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr)
    def test_wrong_first_selection_delayed_wrong_submission_and_unobserved(self):
        d=Driver(self.store);d.run(edge=True);r=self.result(d)
        for e in r['interruptions']:
            if e['order']==1:
                self.assertTrue(e['first_action_sequence_error']);self.assertEqual(e['recovery_ms'],100);self.assertGreater(e['expected_check_submission_ms'],4000);self.assertFalse(e['expected_submission_correct']);self.assertFalse(e['first_submission_correct'])
            if e['order'] in [4,9]:
                self.assertIsNone(e['recovery_ms']);self.assertIsNone(e['expected_check_submission_ms']);self.assertEqual(e['unobserved_reason'],'order_ended');self.assertTrue(e['first_action_sequence_error']);self.assertIsNotNone(e['window_end'])
        for s in r['summaries']:
            self.assertEqual(s['accuracy_denominator'],48)
            if s['condition']!='A':self.assertEqual(s['unobserved_recoveries'],2);self.assertGreater(s['omissions'],0)
    def test_training_failure_no_allocation_and_export(self):
        d=Driver(self.store);d.train(fail=True);self.assertEqual(d.snap['state']['phase'],'incomplete_training');self.assertEqual(d.snap['state']['training'],6)
        with self.assertRaises(ValueError):self.store.allocate(d.id)
        r=self.result(d);self.assertEqual(len(r['practice_attempts']),9);self.assertTrue(all(not a['passed'] for a in r['practice_attempts'][3:]))
        from server import app
        old=app.STORE;app.STORE=self.store
        try:
            with zipfile.ZipFile(io.BytesIO(app.bundle('demo',DEFAULT['version']))) as z:
                b=json.loads(z.read('bundle.json'));self.assertEqual(len(b['tables']['practice_attempts']),9);self.assertEqual(b['tables']['sessions'][0]['training_outcome'],'incomplete_training')
        finally:app.STORE=old
    def test_tlx_orientation_completeness_and_intent(self):
        self.assertEqual(score(dict.fromkeys(TLX_KEYS,0)),0);self.assertEqual(score(dict.fromkeys(TLX_KEYS,100)),100)
        values=dict.fromkeys(TLX_KEYS,0)|dict(performance=100,tracking=100)
        self.assertEqual(score(values),100/6);self.assertIsNone(score({'effort':50,'tracking':50,'frustration':50}));self.assertIsNone(score(values|dict(physical=None)))
        for v in [-5,101,12,True]:self.assertIsNone(score(values|dict(mental=v)))
        d=Driver(self.store);d.train();self.store.allocate(d.id);d.begin()
        for _ in range(12):d.finish()
        with self.assertRaisesRegex(ValueError,'intentional'):d.event('questionnaire',{q['key']:0 for q in ITEMS})
        d.ratings();self.assertEqual(d.snap['state']['phase'],'break')
    def test_actual_last_repetition_wrong_judgment_and_only_c_card(self):
        for cond in 'BC':
            a=dict(conditions=cond+'AC',task_sets='XYZ',b_form='U');s=initial(DEFAULT)|dict(phase='order',practice=False,order=1,available=True)
            for cat in ['delivery','delivery']:
                s=transition(s,'select',dict(category=cat,expected=expected(s)),DEFAULT,a);s=transition(s,'judge',dict(judgment=False),DEFAULT,a);s=transition(s,'submit',dict(category=cat,judgment=False,expected=expected(s)),DEFAULT,a);s=transition(s,'ack_end',{},DEFAULT,a)
                if s['phase']=='order':s=transition(s,'task_ready',{},DEFAULT,a)
            s=transition(s,'secondary_ready',{},DEFAULT,a);s=transition(s,'return',{},DEFAULT,a)
            self.assertEqual(s['cue'],'delivery' if cond=='C' else None);self.assertIsNone(s['selected']);self.assertIsNone(s['judgment'])
            with self.assertRaises(ValueError):transition(s,'select',dict(category='product',expected='product'),DEFAULT,a)
            s=transition(s,'task_return_ready',dict(expected='product',cue_appears=cond=='C'),DEFAULT,a)
            self.assertEqual(s['return_expected'],'product');s=transition(s,'select',dict(category='quantity',expected='product'),DEFAULT,a);self.assertIsNone(s['cue'])
    def test_matching_and_legacy_versions(self):
        for name in 'XYZ':self.assertEqual(FIXTURES[name],LEGACY_FIXTURES[name])
        self.assertEqual(len(FIXTURES['P']),9)
        codes=lambda rows:{r['requested']['product'] for r in rows}
        self.assertFalse(codes(FIXTURES['P']) & set.union(*(codes(FIXTURES[s]) for s in 'XYZ')))
        old=LegacyDriver(self.store);old.run();new=Driver(self.store);new.run()
        before=old.raw();a=old.snap['assignment'];r=derive(before,manifest(LEGACY_DEFAULT,'revision-tests'),a)
        self.assertTrue(all(s['metrics_version']=='hmc-metrics-1' for s in r['summaries']));self.assertEqual(old.snap['config']['questionnaire_version'],'custom-workload-1')
        self.assertEqual(old.raw(),before);self.assertEqual(self.store.allocate(old.id),a)
        from server import app
        saved=app.STORE;app.STORE=self.store
        try:
            with zipfile.ZipFile(io.BytesIO(app.bundle('demo'))) as z:
                b=json.loads(z.read('bundle.json'));self.assertEqual(b['metrics_versions'],['hmc-metrics-1','hmc-metrics-2']);self.assertEqual(len(b['tables']['summaries']),6);self.assertEqual(len(b['tables']['questionnaire_items']),21)
        finally:app.STORE=saved
    def test_synthetic_allocation_pool_does_not_consume_main_slots(self):
        from server.protocol import DEFAULT as CURRENT
        c=CURRENT|dict(version='live-revised',contact='Configured locally',study_information='Test-only information')
        self.store.create_protocol(c)
        synthetic=self.store.create('main',c['version'],True);human=self.store.create('main',c['version'],False)
        with self.store.db() as db:
            for session in [synthetic,human]:db.execute('UPDATE sessions SET state=? WHERE id=?',(canonical(initial(c)|dict(phase='ready')),session['id']))
        a=self.store.allocate(synthetic['id']);b=self.store.allocate(human['id']);self.assertEqual(a['slot'],0);self.assertEqual(b['slot'],0)
        with self.assertRaisesRegex(ValueError,'revised'):self.store.create('main',LEGACY_DEFAULT['version'])
    def test_secondary_pause_and_missing_responses_do_not_invent_recovery(self):
        d=Driver(self.store);d.train();a=self.store.allocate(d.id)
        # Reach first assigned interrupted block using actual reducer transitions.
        for cond in a['conditions']:
            d.begin()
            if cond!='A':break
            for _ in range(12):d.finish()
            d.ratings();d.event('break_end',dt=60000)
        d.finish()  # order 1 is the first checkpoint
        d.check('product');d.select('quantity');d.event('judge',{'judgment':True});d.event('submit',dict(category='quantity',judgment=True,expected='quantity'))
        form=a['b_form'] if cond=='B' else ('V' if a['b_form']=='U' else 'U')
        d.event('ack_end',dict(checkpoint=True,form=form,episode=0),300);d.event('secondary_ready',dt=16)
        # A delayed DOM commit can straddle an item deadline; retain it and flag timing.
        d.event('secondary_item',dict(item=0,pair=d.snap['secondary'][form][0][0]),2001)
        # Omitting a response does not prevent a return; a technical pause ends exposure.
        pause=d.event('pause',{'reason':'external'},500);d.event('resume',dt=500);ret=d.event('task_return_ready',dict(expected='packaging',cue_appears=cond=='C'),16)
        d.finish()
        r=self.result(d);episode=r['interruptions'][0]
        self.assertEqual(episode['secondary_omissions'],5);self.assertEqual(episode['stimulus_exposure_ms'],2501);self.assertEqual(episode['unobserved_reason'],'order_ended');self.assertTrue(episode['technically_compromised'])
        spans=[x for x in r['intervals'] if x['block']==d.snap['state']['block']+1]
        self.assertEqual(sum(x['duration_ms'] for x in spans),2517+516)
        summary=r['summaries'][-1];self.assertEqual(summary['excluded_union_ms'],2517+516)
    def test_not_applicable_expected_and_unanswered_full_secondary(self):
        d=Driver(self.store);d.run();events=d.raw()
        without_responses=[e for e in events if e['type']!='secondary_response']
        r=derive(without_responses,manifest(DEFAULT,'test'),d.snap['assignment'])
        self.assertTrue(all(e['secondary_omissions']==5 and e['stimulus_exposure_ms']==10000 for e in r['interruptions']))
        # Derivation handles a no-next-step checkpoint without manufacturing a latency.
        events=copy.deepcopy(events)
        ret=next(e for e in events if not e['context']['practice'] and e['type']=='task_return_ready')
        ret['context']['expected']=None
        r=derive(events,manifest(DEFAULT,'test'),d.snap['assignment']);ep=next(e for e in r['interruptions'] if e['return_ready']['seq']==ret['seq'])
        self.assertFalse(ep['applicable']);self.assertIsNone(ep['recovery_ms']);self.assertIsNone(ep['expected_check_submission_ms']);self.assertEqual(ep['not_applicable_reason'],'no_remaining_check')
    def test_reload_offline_retry_and_clock_segment_reuse(self):
        d=Driver(self.store);d.train();a=self.store.allocate(d.id);d.begin();e=d.check('product')
        self.store.ingest(d.id,d.tab,[e]);self.assertEqual(self.store.allocate(d.id),a)
        original=d.segment;d.segment=uuid.uuid4().hex;d.mono=0;d.origin+=100000;d.event('document');d.event('resume');d.event('task_ready',{'kind':'resume'});d.finish()
        r=self.result(d);self.assertIsNone(r['summaries'][0]['active_ms']);self.assertIn('clock_discontinuity',r['summaries'][0]['invalid_timing_reasons'])
        d.segment=original
        with self.assertRaisesRegex(ValueError,'reused'):d.event('document')
    def test_pauses_actual_union_and_unanswered_secondary(self):
        self.assertEqual(union([(0,10),(5,20),(18,25)]),25)
        d=Driver(self.store);d.train();self.store.allocate(d.id)
        # Pure reconstruction fixture from a full raw session tests deliberate overlapping intervals.
        d.begin()
        for oi in range(12):
            d.event('pause',{'reason':'external'},100);d.event('resume',dt=500);d.event('task_ready',{'kind':'resume'},16);d.finish()
        r=self.result(d);s=r['summaries'][0];self.assertEqual(s['technical_pause_union_ms'],12*516);self.assertEqual(s['active_ms'],s['total_elapsed_ms']-12*516);self.assertEqual(s['accuracy_numerator'],0);self.assertEqual(s['accuracy_denominator'],48)
        self.assertTrue(all(o['premature_finish'] for o in r['orders']))

class InterfaceVersionTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.store=Store(self.tmp.name+'/study.sqlite','interface-tests')
    def tearDown(self):self.tmp.cleanup()
    def test_pilot3_changes_presentation_only_and_pilot2_is_retained(self):
        from server.protocol import V2_DEFAULT,validate_config,interface
        from server.questionnaire import VERSIONS
        self.assertEqual(DEFAULT['version'],'pilot-3');self.assertEqual(interface(V2_DEFAULT),'pilot-2-interface');self.assertEqual(interface(LEGACY_DEFAULT),'pilot-1-interface')
        changed=['version','questionnaire_version','interface_version']
        self.assertEqual({k:v for k,v in DEFAULT.items() if k not in changed},{k:v for k,v in V2_DEFAULT.items() if k not in changed})
        new,old=manifest(DEFAULT,'b'),manifest(V2_DEFAULT,'b')
        for k in ['fixtures','answer_keys','schedule','secondary','stimulus_version','stimulus_hash']:self.assertEqual(new[k],old[k])
        self.assertEqual(old['questionnaire']['id'],'raw-tlx-1');self.assertEqual(new['questionnaire']['id'],'raw-tlx-2')
        strip=lambda qs:[{k:v for k,v in q.items() if k!='title' or q['key']!='tracking'} for q in qs]
        self.assertEqual(strip(new['questions']),strip(old['questions']));self.assertEqual(VERSIONS['raw-tlx-1'][0],ITEMS)
        with self.store.db() as db:self.assertEqual({r[0] for r in db.execute('SELECT id FROM protocols')},{'pilot-1','pilot-2','pilot-3','pilot-4'})
        validate_config(DEFAULT|dict(version='pilot-3-site'));validate_config(V2_DEFAULT|dict(version='pilot-2-copy'))
        for bad in [DEFAULT|dict(interface_version='other'),DEFAULT|dict(questionnaire_version='raw-tlx-1')]:
            with self.assertRaises(ValueError):validate_config(bad)
    def test_live_sessions_require_current_interface_and_exports_label_it(self):
        from server.protocol import V2_DEFAULT
        info=dict(contact='Configured locally',study_information='Test-only information')
        self.store.create_protocol(V2_DEFAULT|info|dict(version='old-ui-live'));self.store.create_protocol(DEFAULT|info|dict(version='new-ui-live'))
        with self.assertRaisesRegex(ValueError,'current interface'):self.store.create('pilot','old-ui-live',True)
        with self.assertRaisesRegex(ValueError,'current interface'):self.store.create('pilot','new-ui-live',True)
        d=Driver(self.store);d.train()
        self.assertTrue(all(e['context']['interface_version']=='ergonomic-3' for e in d.raw()))
        from server import app
        saved=app.STORE;app.STORE=self.store
        try:
            with zipfile.ZipFile(io.BytesIO(app.bundle('demo',DEFAULT['version']))) as z:
                b=json.loads(z.read('bundle.json'));self.assertEqual(b['interface_versions'],['ergonomic-3'])
                self.assertTrue(all(r['interface_version']=='ergonomic-3' for r in b['tables']['practice_attempts']))
                self.assertIn('protocol-v3.md',z.namelist())
        finally:app.STORE=saved

if __name__=='__main__':unittest.main()
