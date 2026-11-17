import unittest,tempfile,json,uuid,concurrent.futures,collections,copy,io,zipfile,threading,urllib.request,urllib.error,os
from server.protocol import *
from server.domain import *
from server.store import Store
from server.metrics import derive,union,delta
DEFAULT=LEGACY_DEFAULT
FIXTURES=LEGACY_FIXTURES

class Driver:
    def __init__(self,store,mode='demo'):
        self.db=store;self.session=store.create(mode,DEFAULT['version']);self.id=self.session['id'];self.tab='tab-'+uuid.uuid4().hex;store.lease(self.id,self.tab);self.seq=0;self.mono=0;self.segment=uuid.uuid4().hex;self.events=[]
    @property
    def snap(self):return self.db.snapshot(self.id)
    def event(self,t,p=None,dt=50):
        self.mono+=dt;self.seq+=1;e=dict(id=uuid.uuid4().hex,seq=self.seq,segment=self.segment,origin=100000,mono=self.mono,type=t,payload=p or {});self.db.ingest(self.id,self.tab,[e]);self.events.append(e);return e
    def judgment(self,cat,value=True):
        self.event('select',dict(category=cat,expected=expected(self.snap['state'])))
        self.event('submit',dict(category=cat,expected=expected(self.snap['state']),judgment=value))
        st=self.snap['state'];checkpoint=len(st['submitted'])==(2 if st['practice'] else SCHEDULE.get(st['order']))
        a=self.snap['assignment'];cond='C' if st['practice'] else a['conditions'][st['block']];form='U' if st['practice'] else a['b_form'] if cond=='B' else ('V' if a['b_form']=='U' else 'U');episode=0 if st['practice'] else list(SCHEDULE).index(st['order']) if st['order'] in SCHEDULE else -1
        self.event('ack_end',dict(checkpoint=checkpoint,form=form,episode=episode),300)
        if self.snap['state']['phase']=='secondary':
            for i in range(5):
                self.event('secondary_item',{'item':i,'pair':secondary(form,episode)[i]},0 if i==0 else 1950)
                self.event('secondary_response',{'item':i,'choice':0},50)
            self.event('return',dict(expected=expected(self.snap['state'])),1950)
    def train(self):
        self.event('document');self.event('consent',{'agree':True});self.event('device',dict(width=1280,height=720,input='mouse'));self.event('practice_start')
        for cat in CATEGORIES:self.judgment(cat)
        self.event('finish');self.event('comprehension',{'sequence':','.join(CATEGORIES),'return':'automatic'})
    def run(self):
        self.train();self.db.allocate(self.id)
        for b in range(3):
            self.event('block_start')
            for i in range(12):
                for cat in CATEGORIES:self.judgment(cat,answers(FIXTURES[self.snap['assignment']['task_sets'][b]][i])[cat])
                self.event('finish')
            self.event('questionnaire',dict(effort=20,tracking=30,frustration=10))
            if b<2:self.event('break_end',dt=60000)
    def raw(self):
        with self.db.db() as db:return [json.loads(r['body'])|{'context':json.loads(r['context'])} for r in db.execute('SELECT * FROM events WHERE session=? ORDER BY seq',(self.id,))]

class StudyTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.store=Store(self.tmp.name+'/study.sqlite','test-build')
    def tearDown(self):self.tmp.cleanup()
    def test_schedule_balance(self):
        rows=allocation(42);self.assertEqual(rows,allocation(42));self.assertNotEqual(rows,allocation(43));self.assertEqual(len({(r['conditions'],r['task_sets']) for r in rows}),36)
        for b in range(6):self.assertEqual(len({r['conditions'] for r in rows if r['batch']==b}),6)
        for i in range(3):self.assertEqual(collections.Counter(r['conditions'][i] for r in rows),dict(A=12,B=12,C=12))
        self.assertTrue(all(v==12 for v in collections.Counter((r['conditions'][i],r['task_sets'][i]) for r in rows for i in range(3)).values()))
        self.assertEqual(collections.Counter(r['b_form'] for r in rows),dict(U=18,V=18))
    def test_concurrent_allocation_and_extension(self):
        ds=[Driver(self.store) for _ in range(37)]
        for d in ds:
            with self.store.db() as db:db.execute('UPDATE sessions SET state=? WHERE id=?',(canonical(initial()|{'phase':'ready'}),d.id))
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:assign=list(pool.map(lambda d:self.store.allocate(d.id),ds))
        self.assertEqual(len({a['slot'] for a in assign}),37)
        self.assertEqual(self.store.allocate(ds[0].id),assign[0])
    def test_fixture_validation(self):
        self.assertEqual(set(SCHEDULE.values()),{2,3});self.assertEqual(list(SCHEDULE.values()).count(2),3)
        keys=[]
        for s in 'XYZ':
            rows=FIXTURES[s];self.assertEqual(len(rows),12);self.assertEqual(collections.Counter(r['requested']['handling'] for r in rows),dict(fragile=4,chilled=4,standard=4))
            for o in rows:
                self.assertEqual(len(o['requested']['product']),7);self.assertEqual(len(o['requested']['delivery']),7)
                k=answers(o);self.assertEqual(k['packaging'],RULES[o['requested']['handling']]==o['packed']['packaging'])
            keys.append([answers(o) for o in rows]);self.assertEqual({c:sum(answers(o)[c] for o in rows) for c in CATEGORIES},dict.fromkeys(CATEGORIES,6))
        self.assertEqual(keys[0],keys[1]);self.assertEqual(keys[1],keys[2]);self.assertEqual(len({o['id'] for rows in FIXTURES.values() for o in rows}),37)
        self.assertNotEqual(secondary('U',0),secondary('V',0));self.assertEqual([abs(a-b) for a,b in secondary('U',0)],[4]*5)
    def test_complete_three_blocks_recomputable(self):
        d=Driver(self.store);d.run();snap=d.snap;self.assertEqual(snap['state']['phase'],'complete');self.assertEqual(set(snap['assignment']['conditions']),set('ABC'));self.assertEqual(set(snap['assignment']['task_sets']),set('XYZ'))
        m=manifest(DEFAULT,'test-build');result=derive(d.raw(),m,snap['assignment']);self.assertEqual(len(result['orders']),36);self.assertEqual(len(result['interruptions']),12);self.assertEqual(len(result['questionnaires']),3)
        for s in result['summaries']:self.assertEqual(s['accuracy_numerator'],48);self.assertEqual(s['accuracy_denominator'],48);self.assertEqual(s['completed_orders'],12);self.assertIsNotNone(s['active_ms'])
        self.assertEqual(result,derive(d.raw(),m,snap['assignment']))
        for r in result['interruptions']:self.assertTrue(r['recovery_observed']);self.assertEqual(r['actual_secondary_ms'],10000)
    def test_retry_conflict_sequence_and_append_only(self):
        d=Driver(self.store);e=d.event('document');self.assertEqual(self.store.ingest(d.id,d.tab,[e]),1)
        with self.assertRaises(ValueError):self.store.ingest(d.id,d.tab,[e|{'mono':999}])
        with self.assertRaises(ValueError):self.store.ingest(d.id,d.tab,[e|{'id':uuid.uuid4().hex,'seq':3}])
        with self.store.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM events').fetchone()[0],1)
        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError):
            with self.store.db() as db:db.execute('DELETE FROM events')
    def test_lease_and_scope(self):
        d=Driver(self.store);other=Driver(self.store)
        with self.assertRaises(ValueError):self.store.lease(d.id,other.tab)
        with self.assertRaises(ValueError):self.store.ingest(d.id,other.tab,[])
        with self.assertRaises(PermissionError):self.store.auth('bad')
        self.assertEqual(self.store.auth(d.session['code'])['id'],d.id);self.assertNotIn('answer_keys',self.store.snapshot(d.id))
    def test_omissions_repeats_and_wrong_judgments(self):
        d=Driver(self.store);d.train();a=self.store.allocate(d.id);d.event('block_start');d.judgment('quantity',False);d.judgment('quantity',True);d.event('finish');r=derive(d.raw(),manifest(DEFAULT,'test'),a)
        o=r['orders'][0];self.assertEqual(o['omissions'],3);self.assertEqual(o['duplicates'],1);self.assertEqual(o['denominator'],4);self.assertGreater(o['out_of_sequence'],0)
        q=next(c for c in r['checks'] if c['category']=='quantity' and c['order']==0);self.assertFalse(q['first']);self.assertTrue(q['final'])
    def test_reload_flags_no_clock_mixing(self):
        d=Driver(self.store);d.train();a=self.store.allocate(d.id);d.event('block_start');d.judgment('product');d.segment=uuid.uuid4().hex;d.mono=0;d.event('document');self.assertEqual(d.snap['state']['phase'],'paused');d.event('resume');d.event('finish');r=derive(d.raw(),manifest(DEFAULT,'test'),a);self.assertIsNone(r['summaries'][0]['active_ms']);self.assertTrue(r['summaries'][0]['timing_compromised'])
    def test_union(self):
        self.assertEqual(union([(0,10),(5,15),(15,20),(30,40)]),30);self.assertIsNone(delta({'segment':'a','mono':1},{'segment':'b','mono':2}));self.assertEqual(union([]),0)
    def test_config_immutable_and_live_gate(self):
        with self.assertRaises(ValueError):self.store.create('main',DEFAULT['version'])
        from server.protocol import DEFAULT as CURRENT
        c=CURRENT|{'version':'live-1','contact':'researcher@example.edu','study_information':'Draft reviewed locally'};self.store.create_protocol(c);self.store.create('main','live-1')
        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError):self.store.create_protocol(c)
        with self.store.db() as db:self.assertEqual(db.execute("SELECT frozen FROM protocols WHERE id='live-1'").fetchone()[0],1)
        with self.assertRaises(ValueError):validate_config(c|{'interruption_ms':2000})
    def test_early_timers_rejected(self):
        d=Driver(self.store);d.event('consent',{'agree':True});d.event('device',dict(width=1280,height=720,input='mouse'));d.event('practice_start');d.event('select',dict(category='product',expected='product'));d.event('submit',dict(category='product',expected='product',judgment=True))
        with self.assertRaises(ValueError):d.event('ack_end',{'checkpoint':False},dt=100)
    def test_incomplete_training_no_allocation(self):
        d=Driver(self.store);d.event('consent',{'agree':True});d.event('device',dict(width=1280,height=720,input='mouse'))
        for i in range(2):d.event('practice_start');d.event('finish');d.event('comprehension',{'sequence':'other','return':'other'})
        self.assertEqual(d.snap['state']['phase'],'incomplete_training')
        with self.assertRaises(ValueError):self.store.allocate(d.id)

if __name__=='__main__':unittest.main()

class EdgeMetricsTests(unittest.TestCase):
    setUp=StudyTests.setUp
    tearDown=StudyTests.tearDown
    # Reuse isolated storage, but only new cases (inherited tests also run).
    def test_wrong_first_correct_category_wrong_judgment_and_unobserved(self):
        d=Driver(self.store);d.train();a=self.store.allocate(d.id)
        # Exercise the interrupted block in its actual assigned position.
        for b,cond in enumerate(a['conditions']):
            d.event('block_start')
            for oi in range(12):
                d.judgment('product');d.judgment('quantity')
                if cond!='A' and oi in [1,4]:
                    d.judgment('delivery',False) # Wrong first action; expected packaging.
                    if oi==1:d.judgment('packaging',not answers(FIXTURES[a['task_sets'][b]][oi])['packaging'])
                else:d.judgment('packaging');d.judgment('delivery')
                d.event('finish')
            d.event('questionnaire',dict(effort=0,tracking=100,frustration=50))
            if b<2:d.event('break_end',dt=60000)
        r=derive(d.raw(),manifest(DEFAULT,'test'),a)
        for row in [r for r in r['interruptions'] if r['order']==1]:self.assertTrue(row['first_action_sequence_error']);self.assertTrue(row['recovery_observed']);self.assertGreater(row['recovery_ms'],row['first_action_ms'])
        for row in [r for r in r['interruptions'] if r['order']==4]:self.assertFalse(row['recovery_observed']);self.assertIsNone(row['recovery_ms']);self.assertEqual(row['unobserved_reason'],'order_ended')
    def test_out_of_order_batch_sorted_and_offline_retry(self):
        d=Driver(self.store)
        a=dict(id=uuid.uuid4().hex,seq=1,segment=d.segment,origin=100000,mono=10,type='document',payload={})
        b=a|dict(id=uuid.uuid4().hex,seq=2,mono=20,type='consent',payload={'agree':True})
        self.assertEqual(self.store.ingest(d.id,d.tab,[b,a]),2);self.assertEqual(self.store.ingest(d.id,d.tab,[a,b]),2)
        self.assertEqual(d.snap['state']['phase'],'device')
    def test_export_default_separation_recomputation_and_csv(self):
        from server import app
        old=app.STORE;app.STORE=self.store
        try:
            d=Driver(self.store);d.run()
            with zipfile.ZipFile(io.BytesIO(app.bundle())) as z:self.assertEqual(json.loads(z.read('bundle.json'))['tables']['sessions'],[])
            with self.store.db() as db:db.execute('INSERT INTO annotations(session,author,reason,kind,created) VALUES(?,?,?,?,?)',(d.id,'researcher','=HYPERLINK("bad")','note','2026-01-01T00:00:00Z'))
            with zipfile.ZipFile(io.BytesIO(app.bundle('demo',quality_filter=True))) as z:
                b=json.loads(z.read('bundle.json'));self.assertEqual(len(b['tables']['summaries']),3);self.assertEqual(len(b['tables']['clean_recovery_summaries']),3);self.assertNotIn(d.session['code'],z.read('bundle.json').decode());self.assertIn("'=HYPERLINK",z.read('annotations.csv').decode());self.assertEqual(b['tables']['summaries'][0]['accuracy_denominator'],48)
            with self.store.db() as db:db.execute('INSERT INTO annotations(session,author,reason,kind,created) VALUES(?,?,?,?,?)',(d.id,'researcher','Protocol deviation','exclude','2026-01-01T00:00:00Z'))
            with zipfile.ZipFile(io.BytesIO(app.bundle('demo'))) as z:
                b=json.loads(z.read('bundle.json'));self.assertEqual(b['tables']['summaries'],[]);self.assertGreater(len(b['tables']['raw_events']),0)
        finally:app.STORE=old

class APITests(unittest.TestCase):
    def setUp(self):
        from server import app
        self.app=app;self.tmp=tempfile.TemporaryDirectory();self.old=(app.STORE,app.ADMIN);app.STORE=Store(self.tmp.name+'/api.sqlite');app.ADMIN='test-only-long-password';app.login_attempts=[]
        self.url='http://127.0.0.1:8000'
    def tearDown(self):self.app.STORE,self.app.ADMIN=self.old;self.tmp.cleanup()
    def request(self,path,data=None,cookie=None,origin=None):
        headers={'Content-Type':'application/json'}
        if cookie:headers['Cookie']=cookie
        if origin:headers['Origin']=origin
        # Exercise the actual HTTP parser/handler in memory; sandbox denies socket binding.
        payload=json.dumps(data).encode() if data is not None else b''
        headers.update({'Host':'127.0.0.1:8000','Content-Length':str(len(payload)),'Connection':'close'})
        raw=(('POST' if data is not None else 'GET')+' '+path+' HTTP/1.1\r\n'+''.join(k+': '+v+'\r\n' for k,v in headers.items())+'\r\n').encode()+payload
        class Connection:
            def __init__(self):self.output=bytearray()
            def makefile(self,*a):return io.BytesIO(raw)
            def sendall(self,b):self.output.extend(b)
        conn=Connection();self.app.Handler(conn,('127.0.0.1',0),None)
        head,body=bytes(conn.output).split(b'\r\n\r\n',1)
        lines=head.decode().split('\r\n');hs=dict(line.split(': ',1) for line in lines[1:])
        return int(lines[0].split()[1]),body,hs
    def test_authenticated_roles_csrf_and_secret_redaction(self):
        self.assertEqual(self.request('/api/admin/overview')[0],401);self.assertEqual(self.request('/api/admin/export')[0],401)
        status,_,h=self.request('/api/login',{'password':self.app.ADMIN});self.assertEqual(status,200);admin=h['Set-Cookie'].split(';')[0]
        _,raw,_=self.request('/api/admin/sessions',{'mode':'demo','protocol':DEFAULT['version']},admin);code=json.loads(raw)['code']
        _,_,h=self.request('/api/join',{'code':code});cookie=h['Set-Cookie'].split(';')[0];self.assertIn('HttpOnly',h['Set-Cookie'])
        self.assertEqual(self.request('/api/admin/overview',cookie=cookie)[0],401);self.assertEqual(self.request('/api/session')[0],401)
        status,raw,_=self.request('/api/session',cookie=cookie);self.assertEqual(status,200);self.assertNotIn(b'answer_keys',raw);self.assertNotIn(code.encode(),raw)
        self.assertEqual(self.request('/api/session/allocate',{},cookie,origin='https://evil.invalid')[0],401)
