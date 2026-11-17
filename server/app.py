import os,json,secrets,hmac,time,io,zipfile,csv,mimetypes
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from http.cookies import SimpleCookie
from urllib.parse import urlparse,parse_qs
from pathlib import Path
from .store import Store,utc,canonical
from .metrics import derive
from .protocol import METRICS,interface,revised,PROCEDURE_METRICS
STORE=None  # Initialized only when serving; importing tests/exports never opens a collection database.
ADMIN=os.environ.get('ADMIN_PASSWORD','');auth_sessions={};login_attempts=[]

def bundle(mode='main',protocol=None,quality_filter=False,include_all=False):
    with STORE.db() as db:
        ss=[dict(s) for s in db.execute('SELECT id,protocol,mode,synthetic,status,state,assignment,last_seq,created FROM sessions WHERE mode=?',(mode,)) if (mode!='main' or not s['synthetic']) and (not protocol or s['protocol']==protocol)]
        tables={k:[] for k in ['sessions','allocations','raw_events','annotations','orders','checks','interruptions','questionnaires','summaries','quality','practice_attempts','submitted_checks','transitions','secondary_items','intervals','questionnaire_items','participant_contrasts']};manifests={}
        for s in ss:
            annotations=[dict(x) for x in db.execute('SELECT * FROM annotations WHERE session=?',(s['id'],))]
            tables['annotations']+=annotations
            excluded=s['status']=='withdrawn' or any(x['kind']=='exclude' for x in annotations)
            st=json.loads(s['state'])
            session_row={k:v for k,v in s.items() if k not in ['state','assignment']}|{'excluded_from_analysis':excluded,'training_attempts':st['training'],'training_outcome':'passed' if s['assignment'] or st['phase']=='ready' else 'incomplete_training' if st['phase']=='incomplete_training' else 'not_yet_passed'}
            tables['sessions'].append(session_row)
            m=json.loads(db.execute('SELECT manifest FROM protocols WHERE id=?',(s['protocol'],)).fetchone()[0]);manifests[s['protocol']]=m
            versions=dict(metrics_version=m['config']['metrics_version'],build=m['build'],stimulus_version=m['stimulus_version'],questionnaire_version=m['config']['questionnaire_version'],interface_version=interface(m['config']))
            session_row.update(versions,configuration=m['config'])
            events=[]
            for row in db.execute('SELECT * FROM events WHERE session=? ORDER BY seq',(s['id'],)):
                e=json.loads(row['body']);e.update(session=s['id'],context=json.loads(row['context']),server_receipt_utc=row['receipt']);events.append(e)
            tables['raw_events']+=events
            a=json.loads(s['assignment']) if s['assignment'] else None
            if a:tables['allocations'].append(dict(session=s['id'],protocol=s['protocol'],mode=s['mode'],**a))
            if a or revised(m['config']):
                d=derive(events,m,a)
                db.execute('INSERT OR IGNORE INTO derived_versions VALUES(?,?,?,?,?)',(s['id'],m['config']['metrics_version'],s['last_seq'],canonical(d),utc()))
                for k,rows in d.items():
                    if excluded and not include_all: continue
                    for row in rows:
                        tables[k].append(dict(session=s['id'],protocol=s['protocol'],**versions)|row)
        selected={s['id'] for s in ss}
        tables['audit']=[dict(x) for x in db.execute('SELECT * FROM audit') if x['actor'] in selected or json.loads(x['detail']).get('session') in selected]
        if quality_filter:
            import statistics
            clean=[r for r in tables['interruptions'] if not r['technically_compromised'] and (r['metrics_version']==PROCEDURE_METRICS or not r['prior_sequence_deviation'])]
            tables['clean_interruptions']=clean
            tables['unflagged_procedure_episodes']=[r for r in tables['interruptions'] if r['metrics_version']==PROCEDURE_METRICS and not r['procedure_flagged']]
            tables['clean_recovery_summaries']=[]
            for summary in tables['summaries']:
                rows=[r for r in clean if r['session']==summary['session'] and r['block']==summary['block']]
                values=[r['recovery_ms'] for r in rows if r['recovery_observed']]
                tables['clean_recovery_summaries'].append(dict(session=summary['session'],protocol=summary['protocol'],metrics_version=summary['metrics_version'],build=summary['build'],stimulus_version=summary['stimulus_version'],questionnaire_version=summary['questionnaire_version'],interface_version=summary['interface_version'],block=summary['block'],condition=summary['condition'],eligible=sum(r['expected_at_return'] is not None for r in rows),observed=len(values),unobserved=sum(not r['recovery_observed'] and (summary['metrics_version']=='hmc-metrics-1' or r['expected_at_return'] is not None) for r in rows),not_applicable=sum(r['expected_at_return'] is None for r in rows),excluded_by_filter=sum(r['session']==summary['session'] and r['block']==summary['block'] for r in tables['interruptions'])-len(rows),mean_recovery_ms=statistics.mean(values) if values else None,median_recovery_ms=statistics.median(values) if values else None))
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('bundle.json',json.dumps(dict(metrics_version=next(iter({m['config']['metrics_version'] for m in manifests.values()})) if len({m['config']['metrics_version'] for m in manifests.values()})==1 else None,metrics_versions=sorted({m['config']['metrics_version'] for m in manifests.values()}),interface_versions=sorted({interface(m['config']) for m in manifests.values()}),exported_utc=utc(),mode=mode,quality_filter=quality_filter,tables=tables,manifests=manifests),indent=2))
        for name,rows in tables.items():
            f=io.StringIO();cols=list(dict.fromkeys(k for row in rows for k in row));w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
            for row in rows:
                safe={}
                for k,v in row.items():
                    if isinstance(v,(dict,list)):v=canonical(v)
                    if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@','\t','\r')):v="'"+v
                    safe[k]=v
                w.writerow(safe)
            z.writestr(name+'.csv',f.getvalue())
        z.writestr('manifests.json',json.dumps(manifests,indent=2))
        for f in ['data-dictionary.md','analysis.md','researcher-script.md','pilot-checklist.md','protocol-v2.md','protocol-v3.md','protocol-v4.md','questionnaire-sources.md','legacy/data-dictionary-v1.md','legacy/analysis-v1.md','legacy/analysis-v2-v3.md','legacy/data-dictionary-v2-v3.md']: z.writestr(f,Path('docs/'+f).read_text())
    return out.getvalue()
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*a): pass # No IP or credential request logging.
    def send(self,status,data,kind='application/json',cookie=None):
        raw=json.dumps(data).encode() if kind=='application/json' else data
        self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer');self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'")
        if cookie:self.send_header('Set-Cookie',cookie)
        self.end_headers();self.wfile.write(raw)
    def cookies(self):
        c=SimpleCookie();c.load(self.headers.get('Cookie',''));return {k:v.value for k,v in c.items()}
    def admin(self):
        t=self.cookies().get('admin','')
        if auth_sessions.get(t,0)<time.time():raise PermissionError('Researcher login required')
    def participant(self):return STORE.auth(self.cookies().get('participant',''))
    def do_GET(self):self.handle_request('GET')
    def do_POST(self):self.handle_request('POST')
    def handle_request(self,method):
        try:
            url=urlparse(self.path);path=url.path;p={}
            if method=='POST':
                origin=self.headers.get('Origin')
                if origin and urlparse(origin).netloc!=self.headers.get('Host'):raise PermissionError('Cross-origin request rejected')
                n=int(self.headers.get('Content-Length',0))
                if n<0 or n>2000000:raise ValueError('Request too large')
                p=json.loads(self.rfile.read(n) or b'{}')
            secure='; Secure' if os.environ.get('COOKIE_SECURE')=='1' else ''
            if path=='/api/login' and method=='POST':
                global login_attempts
                login_attempts=[t for t in login_attempts if t>time.time()-60]
                if len(login_attempts)>=10:raise PermissionError('Wait one minute before retrying')
                login_attempts.append(time.time())
                if len(ADMIN)<16 or not hmac.compare_digest(str(p.get('password','')),ADMIN):raise PermissionError('Invalid login or administrator not configured')
                token=secrets.token_urlsafe(32);auth_sessions[token]=time.time()+8*3600
                return self.send(200,{'ok':True},cookie=f'admin={token}; HttpOnly; SameSite=Strict; Path=/{secure}')
            if path.startswith('/api/admin'):
                self.admin()
                if path=='/api/admin/overview':
                    with STORE.db() as db:
                        data={k:[dict(r) for r in db.execute(q)] for k,q in dict(protocols='SELECT * FROM protocols',sessions='SELECT id,protocol,mode,synthetic,status,state,assignment,last_seq,created FROM sessions',annotations='SELECT * FROM annotations',slots='SELECT * FROM slots').items()}
                    with STORE.db() as db:
                        for session in data['sessions']:
                            rows=list(db.execute('SELECT body,context,receipt FROM events WHERE session=? ORDER BY seq',(session['id'],)))
                            session['last_receipt_utc']=rows[-1]['receipt'] if rows else None
                            session['consented']=any(json.loads(r['body'])['type']=='consent' for r in rows)
                            session['deviations']=[dict(seq=json.loads(r['body'])['seq'],reason=json.loads(r['body'])['payload'].get('reason',json.loads(r['body'])['type']),block=json.loads(r['context'])['block'],order=json.loads(r['context'])['order']) for r in rows if not json.loads(r['context'])['practice'] and json.loads(r['body'])['type'] in ['pause','document','environment','input_problem']]
                    return self.send(200,data)
                if path=='/api/admin/sessions' and method=='POST':return self.send(201,STORE.create(p['mode'],p['protocol'],p.get('synthetic',False)))
                if path=='/api/admin/protocols' and method=='POST':STORE.create_protocol(p);return self.send(201,{'ok':True})
                if path=='/api/admin/annotations' and method=='POST':
                    if p.get('kind') not in ['exclude','quality','note'] or not str(p.get('reason','')).strip() or len(p['reason'])>2000:raise ValueError('Reason and valid annotation kind required')
                    with STORE.db() as db:db.execute('INSERT INTO annotations(session,author,reason,kind,created) VALUES(?,?,?,?,?)',(p['session'],'researcher',p['reason'],p['kind'],utc()))
                    STORE.audit('researcher','annotation_added',p);return self.send(201,{'ok':True})
                if path=='/api/admin/abort' and method=='POST':
                    with STORE.db() as db:db.execute("UPDATE sessions SET status='aborted' WHERE id=? AND status NOT IN ('completed','withdrawn')",(p['session'],))
                    STORE.audit('researcher','session_aborted',p);return self.send(200,{'ok':True})
                if path=='/api/admin/export':
                    q=parse_qs(url.query);return self.send(200,bundle(q.get('mode',['main'])[0],q.get('protocol',[None])[0],q.get('quality',['all'])[0]=='clean',q.get('include_excluded',['false'])[0]=='true'),'application/zip')
                raise ValueError('Unknown researcher route')
            if path=='/api/join' and method=='POST':
                s=STORE.auth(p['code']);return self.send(200,{'id':s['id']},cookie=f"participant={p['code']}; HttpOnly; SameSite=Strict; Path=/{secure}")
            if path.startswith('/api/session'):
                s=self.participant()
                if path=='/api/session' and method=='GET':return self.send(200,STORE.snapshot(s['id']))
                if path=='/api/session/lease':STORE.lease(s['id'],p['tab']);return self.send(200,{'ok':True})
                if path=='/api/session/allocate':return self.send(200,STORE.allocate(s['id']))
                if path=='/api/session/events':return self.send(200,{'last_seq':STORE.ingest(s['id'],p['tab'],p['events'])})
            if path.startswith('/api'):return self.send(404,{'error':'Not found'})
            if path=='/admin':
                try:self.admin()
                except PermissionError:path='/index.html' # Login shell contains no researcher data.
            target=Path('dist')/path.lstrip('/')
            if not target.is_file():target=Path('dist/index.html')
            if not target.resolve().is_relative_to(Path('dist').resolve()):raise PermissionError('Invalid path')
            return self.send(200,target.read_bytes(),mimetypes.guess_type(target)[0] or 'application/octet-stream')
        except PermissionError as ex:self.send(401,{'error':str(ex)})
        except (ValueError,KeyError,TypeError) as ex:self.send(409,{'error':str(ex)})
        except Exception:
            import traceback;traceback.print_exc();self.send(500,{'error':'Server could not save this request. Please retry; records are retained.'})
if __name__=='__main__':
    import subprocess
    build=os.environ.get('BUILD_ID') or subprocess.check_output([os.sys.executable,'scripts/build-id.py'],text=True).strip()
    STORE=Store(os.environ.get('DATABASE_PATH','data/study.sqlite'),build)
    print(f"Study server: http://{os.environ.get('HOST','127.0.0.1')}:{os.environ.get('PORT','8000')}",flush=True)
    ThreadingHTTPServer((os.environ.get('HOST','127.0.0.1'),int(os.environ.get('PORT','8000'))),Handler).serve_forever()
