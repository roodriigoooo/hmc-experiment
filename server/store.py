import sqlite3,json,os,secrets,hashlib,time
from contextlib import contextmanager
from datetime import datetime,timezone
from .protocol import *
from .domain import *

def utc(): return datetime.now(timezone.utc).isoformat()
def token_hash(t): return hashlib.sha256(t.encode()).hexdigest()
SCHEMA='''
CREATE TABLE IF NOT EXISTS protocols(id TEXT PRIMARY KEY, manifest TEXT NOT NULL, frozen INTEGER NOT NULL DEFAULT 0, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, token_hash TEXT UNIQUE NOT NULL, protocol TEXT REFERENCES protocols(id), mode TEXT NOT NULL, synthetic INTEGER NOT NULL, status TEXT NOT NULL, state TEXT NOT NULL, assignment TEXT, last_seq INTEGER NOT NULL DEFAULT 0, lease TEXT, lease_until REAL, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS slots(protocol TEXT, mode TEXT, slot INTEGER, assignment TEXT NOT NULL, session TEXT UNIQUE REFERENCES sessions(id), PRIMARY KEY(protocol,mode,slot));
CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY, session TEXT REFERENCES sessions(id), seq INTEGER, body TEXT NOT NULL, context TEXT NOT NULL, receipt TEXT NOT NULL, UNIQUE(session,seq));
CREATE TABLE IF NOT EXISTS annotations(id INTEGER PRIMARY KEY, session TEXT REFERENCES sessions(id), author TEXT, reason TEXT, kind TEXT, created TEXT);
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, actor TEXT, action TEXT, detail TEXT, created TEXT);
CREATE TABLE IF NOT EXISTS derived(session TEXT PRIMARY KEY, metrics_version TEXT, through_seq INTEGER, tables TEXT);
CREATE TABLE IF NOT EXISTS derived_versions(session TEXT REFERENCES sessions(id), metrics_version TEXT, through_seq INTEGER, tables TEXT, created TEXT, PRIMARY KEY(session,metrics_version,through_seq));
CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'append only'); END;
CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'append only'); END;
CREATE TRIGGER IF NOT EXISTS manifest_no_update BEFORE UPDATE OF manifest ON protocols BEGIN SELECT RAISE(ABORT,'immutable manifest'); END;
'''
class Store:
    def __init__(self,path,build='development'):
        self.path=path;self.build=build;os.makedirs(os.path.dirname(path) or '.',exist_ok=True)
        with self.db() as db:
            db.executescript(SCHEMA)
            db.execute('INSERT OR IGNORE INTO protocols VALUES(?,?,0,?)',(LEGACY_DEFAULT['version'],canonical(manifest(LEGACY_DEFAULT,build)),utc()))
            db.execute('INSERT OR IGNORE INTO protocols VALUES(?,?,0,?)',(V2_DEFAULT['version'],canonical(manifest(V2_DEFAULT,build)),utc()))
            db.execute('INSERT OR IGNORE INTO protocols VALUES(?,?,0,?)',(V3_DEFAULT['version'],canonical(manifest(V3_DEFAULT,build)),utc()))
            db.execute('INSERT OR IGNORE INTO protocols VALUES(?,?,0,?)',(DEFAULT['version'],canonical(manifest(DEFAULT,build)),utc()))
    @contextmanager
    def db(self):
        db=sqlite3.connect(self.path,timeout=30);db.row_factory=sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON');db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL')
        try: yield db;db.commit()
        except: db.rollback();raise
        finally: db.close()
    def audit(self,actor,action,detail):
        with self.db() as db: db.execute('INSERT INTO audit(actor,action,detail,created) VALUES(?,?,?,?)',(actor,action,canonical(detail),utc()))
    def create_protocol(self,c):
        validate_config(c)
        with self.db() as db: db.execute('INSERT INTO protocols VALUES(?,?,0,?)',(c['version'],canonical(manifest(c,self.build)),utc()))
        self.audit('researcher','protocol_created',{'version':c['version']})
    def create(self,mode,protocol,synthetic=False):
        require(mode in ['demo','pilot','main']);require(type(synthetic) is bool)
        with self.db() as db:
            row=db.execute('SELECT * FROM protocols WHERE id=?',(protocol,)).fetchone();require(row is not None,'Unknown protocol')
            m=json.loads(row['manifest'])
            require(mode=='demo' or revised(m['config']),'New live sessions require the revised protocol')
            require(mode=='demo' or current(m['config']),'New live sessions require the current interface protocol (pilot-4 or a version derived from it)')
            require(mode=='demo' or m['build']==self.build,'Create a protocol version for the current application build')
            require(mode=='demo' or (m['config']['contact'].strip() and m['config']['study_information'].strip()),'Populate study information and contact in a new version before live collection')
            sid=secrets.token_hex(8);token=secrets.token_urlsafe(32)
            db.execute('INSERT INTO sessions(id,token_hash,protocol,mode,synthetic,status,state,created) VALUES(?,?,?,?,?,?,?,?)',(sid,token_hash(token),protocol,mode,int(synthetic or mode=='demo'),'created',canonical(initial(m['config'])),utc()))
            if mode=='main': db.execute('UPDATE protocols SET frozen=1 WHERE id=?',(protocol,))
        self.audit('researcher','session_created',{'session':sid,'mode':mode});return {'id':sid,'code':token}
    def auth(self,token):
        with self.db() as db: row=db.execute('SELECT * FROM sessions WHERE token_hash=?',(token_hash(token),)).fetchone()
        if row is None: raise PermissionError('Invalid session credential')
        return dict(row)
    def snapshot(self,sid):
        with self.db() as db:
            s=dict(db.execute('SELECT * FROM sessions WHERE id=?',(sid,)).fetchone());m=json.loads(db.execute('SELECT manifest FROM protocols WHERE id=?',(s['protocol'],)).fetchone()[0])
        require(s['mode']=='demo' or m['build']==self.build,'This session requires its original application build; contact the researcher')
        return dict(id=sid,state=json.loads(s['state']),assignment=json.loads(s['assignment']) if s['assignment'] else None,last_seq=s['last_seq'],mode=s['mode'],synthetic=bool(s['synthetic']),config=m['config'],build=m['build'],fixtures=m['fixtures'],secondary=m['secondary'],questions=m['questions'],questionnaire=m.get('questionnaire',{}),stimulus_version=m['stimulus_version'])
    def lease(self,sid,tab):
        require(isinstance(tab,str) and 10<=len(tab)<=100)
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE');s=db.execute('SELECT * FROM sessions WHERE id=?',(sid,)).fetchone()
            require(s['lease'] in [None,tab] or (s['lease_until'] or 0)<time.time(),'Another tab owns this session. Close it and wait 20 seconds.')
            db.execute('UPDATE sessions SET lease=?,lease_until=? WHERE id=?',(tab,time.time()+20,sid))
    def allocate(self,sid):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE');s=db.execute('SELECT * FROM sessions WHERE id=?',(sid,)).fetchone()
            if s['assignment']: return json.loads(s['assignment'])
            require(json.loads(s['state'])['phase']=='ready','Training must be completed')
            pool=s['mode']+(':synthetic' if s['synthetic'] and s['mode']!='demo' else '')
            c=json.loads(db.execute('SELECT manifest FROM protocols WHERE id=?',(s['protocol'],)).fetchone()[0])['config']
            row=db.execute('SELECT * FROM slots WHERE protocol=? AND mode=? AND session IS NULL ORDER BY slot LIMIT 1',(s['protocol'],pool)).fetchone()
            if row is None:
                n=db.execute('SELECT COUNT(*) FROM slots WHERE protocol=? AND mode=?',(s['protocol'],pool)).fetchone()[0]
                for a in allocation(c['seed'],n//36): db.execute('INSERT INTO slots VALUES(?,?,?,?,NULL)',(s['protocol'],pool,a['slot'],canonical(a)))
                row=db.execute('SELECT * FROM slots WHERE protocol=? AND mode=? AND session IS NULL ORDER BY slot LIMIT 1',(s['protocol'],pool)).fetchone()
            db.execute('UPDATE slots SET session=? WHERE protocol=? AND mode=? AND slot=?',(sid,s['protocol'],pool,row['slot']))
            db.execute("UPDATE sessions SET assignment=?,status='assigned' WHERE id=?",(row['assignment'],sid))
            return json.loads(row['assignment'])
    def ingest(self,sid,tab,events):
        require(isinstance(events,list) and len(events)<=500)
        try:
            with self.db() as db:
                db.execute('BEGIN IMMEDIATE');s=dict(db.execute('SELECT * FROM sessions WHERE id=?',(sid,)).fetchone())
                require(s['lease']==tab and s['lease_until']>time.time(),'Tab lease expired')
                m=json.loads(db.execute('SELECT manifest FROM protocols WHERE id=?',(s['protocol'],)).fetchone()[0]);c=m['config'];state=json.loads(s['state']);a=json.loads(s['assignment']) if s['assignment'] else None
                for e in sorted(events,key=lambda x:x['seq']):
                    require(set(e)=={'id','seq','segment','origin','mono','type','payload'},'Event schema mismatch')
                    require(isinstance(e['id'],str) and 10<=len(e['id'])<=100 and isinstance(e['segment'],str) and len(e['segment'])<=100)
                    require(type(e['seq']) is int and all(type(e[k]) in [int,float] and 0<=e[k]<1e16 for k in ['mono','origin']))
                    require(isinstance(e['payload'],dict));body=canonical(e)
                    prior=db.execute('SELECT body,session FROM events WHERE id=?',(e['id'],)).fetchone()
                    if prior: require(prior['session']==sid and prior['body']==body,'Conflicting event ID');continue
                    require(e['seq']==s['last_seq']+1,'Sequence gap; retry missing events first')
                    prev=db.execute('SELECT body FROM events WHERE session=? ORDER BY seq DESC LIMIT 1',(sid,)).fetchone()
                    if prev:
                        prev=json.loads(prev[0]);require(e['segment']!=prev['segment'] or e['mono']>=prev['mono'],'Clock moved backwards')
                        require(e['segment']==prev['segment'] or e['type']=='document','New clock requires document event')
                        if e['segment']!=prev['segment']:
                            require(not any(json.loads(r[0])['segment']==e['segment'] for r in db.execute('SELECT body FROM events WHERE session=?',(sid,))),'Clock segment reused')
                        else:require(e['origin']==prev['origin'],'Clock origin changed within segment')
                    elif revised(c):require(e['type']=='document','First event requires document clock segment')
                    context=dict(protocol=s['protocol'],build=m['build'],metrics_version=c['metrics_version'],stimulus_version=m['stimulus_version'],questionnaire_version=c['questionnaire_version'],interface_version=interface(c),condition=None if state['practice'] or not a else a['conditions'][state['block']],block=state['block']+1,task_set='P' if state['practice'] or not a else a['task_sets'][state['block']],order=state['order'],practice=state['practice'],expected=expected(state),last=state['last'],cue=state['cue'],input_method=c['input_method'],practice_index=state.get('practice_index'),training=state['training'],phase=state['phase'])
                    # Validate protocol-derived timing and checkpoint fields before reduction.
                    history=[json.loads(r[0]) for r in db.execute('SELECT body FROM events WHERE session=? ORDER BY seq',(sid,))]
                    def since(kind):
                        previous=next((r for r in reversed(history) if r['type']==kind),None)
                        return e['mono']-previous['mono'] if previous and previous['segment']==e['segment'] else None
                    if e['type']=='ack_end':
                        scheduled=(2 if state['practice'] else schedule(c).get(state['order'])) if not revised(c) else (2 if state['practice'] and state['practice_index'] in [1,2] else schedule(c).get(state['order']) if not state['practice'] else -1)
                        require(e['payload'].get('checkpoint')==(len(state['submitted'])==scheduled),'Incorrect checkpoint')
                        if len(state['submitted'])==scheduled:
                            cond=condition(state,a) if revised(c) else ('C' if state['practice'] else a['conditions'][state['block']])
                            form='U' if state['practice'] else a['b_form'] if cond=='B' else ('V' if a['b_form']=='U' else 'U')
                            require(e['payload'].get('form')==form,'Incorrect secondary form')
                            require(e['payload'].get('episode')==(0 if state['practice'] else list(schedule(c)).index(state['order'])),'Incorrect secondary episode')
                        require(since('submit') is not None and since('submit')>=c['acknowledgement_ms']-2,'Acknowledgement ended early')
                    if e['type']=='return':
                        onset_kind='secondary_ready' if revised(c) else 'ack_end'
                        require(since(onset_kind) is not None and since(onset_kind)>=c['interruption_ms']-2,'Secondary task ended early')
                    if e['type']=='break_end':
                        duration=since('questionnaire')
                        if duration is not None: require(duration>=c['break_ms']-2,'Break ended early')
                        else:
                            previous=next((r for r in reversed(history) if r['type']=='questionnaire'),None)
                            require(previous and e['origin']+e['mono']-previous['origin']-previous['mono']>=c['break_ms']-2,'Break ended early across reload')
                    if e['type'] in ['secondary_item','secondary_response']:
                        onset=next((r for r in reversed(history) if r['type']==('secondary_ready' if revised(c) else 'ack_end')),None)
                        require(onset is not None and onset['segment']==e['segment'],'Secondary clock missing')
                        elapsed=e['mono']-onset['mono']
                        if revised(c):
                            # Items are frame-committed. Responses refer to the actually displayed item.
                            shown=next((r for r in reversed(history) if r['type']=='secondary_item' and r['seq']>onset['seq']),None)
                            require(0<=elapsed<c['interruption_ms']+250,'Secondary exposure outside window')
                            if e['type']=='secondary_item':
                                j=e['payload'].get('item')
                                require(type(j) is int and 0<=j<5 and elapsed+250>=j*c['item_ms'] and (shown is None or j>shown['payload']['item']),'Secondary item timing mismatch')
                                ack=next(r for r in reversed(history) if r['type']=='ack_end')
                                require(e['payload'].get('pair')==m['secondary'][ack['payload']['form']][ack['payload']['episode']][j],'Incorrect secondary stimulus')
                            else:require(shown and shown['payload']['item']==e['payload'].get('item'),'Response to nonvisible item')
                        else: require(0<=elapsed and e['payload'].get('item')==min(4,int(elapsed//c['item_ms'])),'Secondary item timing mismatch')
                        if e['type']=='secondary_response':
                            require(elapsed<c['interruption_ms'],'Late secondary response')
                            require(not any(r['type']=='secondary_response' and r['seq']>onset['seq'] and r['payload']['item']==e['payload']['item'] for r in history),'Repeated secondary response')
                    if revised(c) and e['type']=='questionnaire':
                        ratings={}
                        for r in history:
                            if r['type']=='block_start':ratings={}
                            if r['type']=='questionnaire_item':ratings[r['payload']['key']]=r['payload']['value']
                        require(ratings==e['payload'],'Every rating requires an intentional recorded response')
                    state=transition(state,e['type'],e['payload'],c,a)
                    db.execute('INSERT INTO events VALUES(?,?,?,?,?,?)',(e['id'],sid,e['seq'],body,canonical(context),utc()));s['last_seq']=e['seq']
                    if e['type']=='block_start':s['status']='started'
                    if state['phase'] in ['complete','withdrawn','incomplete_training']:s['status']={'complete':'completed','withdrawn':'withdrawn','incomplete_training':'aborted'}[state['phase']]
                db.execute('UPDATE sessions SET state=?,last_seq=?,status=? WHERE id=?',(canonical(state),s['last_seq'],s['status'],sid))
            return s['last_seq']
        except (ValueError,KeyError,TypeError) as ex:
            self.audit(sid,'ingest_rejected',{'reason':str(ex)});raise ValueError(str(ex))
