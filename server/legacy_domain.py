"""Deterministic event reducer. Invalid events never mutate accepted state."""
from copy import deepcopy
from .protocol import CATEGORIES,SCHEDULE

def initial(): return dict(phase='consent',block=0,order=0,submitted=[],selected=None,training=0,cue=None,last=None,practice=True,pause_from=None)
def expected(s): return next((c for c in CATEGORIES if c not in s['submitted']),None)
def require(ok,message='Illegal transition'):
    if not ok: raise ValueError(message)
def transition(old,t,p,config,assignment=None):
    allowed={
        'document':{'reason','width','height'},'withdraw':set(),'pause':{'reason'},'resume':{'reason'},
        'secondary_item':{'item','pair','elapsed_ms'},'secondary_response':{'item','choice','elapsed_ms'},
        'consent':{'agree'},'device':{'width','height','input'},'practice_start':set(),
        'select':{'category','expected','cue_removed'},'submit':{'category','expected','judgment'},
        'ack_end':{'checkpoint','form','episode','acknowledgement_ms'},'return':{'expected','visible_duration_ms','cue_appears'},
        'finish':{'expected','cue_removed'},'comprehension':{'sequence','return'},'block_start':set(),
        'questionnaire':{'effort','tracking','frustration'},'break_end':set()}
    require(t in allowed and set(p)<=allowed[t],'Invalid event payload fields')
    for k,v in p.items():
        if k in ['elapsed_ms','visible_duration_ms','width','height','acknowledgement_ms']:require(type(v) in [int,float] and 0<=v<1e12,'Invalid numeric payload')
        if k in ['cue_removed','cue_appears','checkpoint']:require(type(v) is bool,'Invalid boolean payload')
    s=deepcopy(old); phase=s['phase']
    if t=='document':
        if phase in ['order','ack','secondary','resumed','break','paused']:
            s['pause_from']=s.get('pause_from') or phase; s['phase']='paused'
        return s
    if t=='withdraw': require(phase not in ['complete','withdrawn']); s['phase']='withdrawn'; return s
    if t=='pause':
        require(phase not in ['complete','withdrawn','paused']); require(p.get('reason') in ['blur','hidden','viewport','reload','storage','technical'])
        s['pause_from']=phase;s['phase']='paused';return s
    if t=='resume':
        require(phase=='paused')
        s['phase']=s['pause_from'];s['pause_from']=None
        # An interrupted timed secondary/ack cannot be replayed without a flag.
        if s['phase'] in ['secondary','ack']: s['phase']='resumed';s['cue']=s['last'] if s['practice'] or assignment['conditions'][s['block']]=='C' else None
        return s
    if t in ['secondary_item','secondary_response']:
        require(phase=='secondary');require(type(p.get('item')) is int and 0<=p['item']<5)
        if t=='secondary_response': require(p.get('choice') in [0,1])
        return s
    if t=='consent': require(phase=='consent' and p.get('agree') is True);s['phase']='device'
    elif t=='device': require(phase=='device' and p.get('width',0)>=config['min_width'] and p.get('height',0)>=config['min_height'] and p.get('input')=='mouse');s['phase']='instructions'
    elif t=='practice_start':
        require(phase=='instructions');s.update(phase='order',practice=True,submitted=[],selected=None,last=None,cue=None);s['training']+=1
    elif t=='select':
        require(phase in ['order','resumed'] and p.get('category') in CATEGORIES);require(p.get('expected')==expected(s),'Expected category mismatch')
        s['selected']=p['category'];s['cue']=None
    elif t=='submit':
        require(phase in ['order','resumed'] and s['selected'] is not None and type(p.get('judgment')) is bool)
        require(p.get('category')==s['selected'] and p.get('expected')==expected(s),'Submission context mismatch')
        s['submitted'].append(s['selected']);s['last']=s['selected'];s['selected']=None;s['phase']='ack'
    elif t=='ack_end':
        require(phase=='ack');scheduled=2 if s['practice'] else SCHEDULE.get(s['order'])
        hit=len(s['submitted'])==scheduled
        condition='C' if s['practice'] else assignment['conditions'][s['block']]
        s['phase']='secondary' if hit and condition!='A' else 'order'
    elif t=='return':
        require(phase=='secondary');require(p.get('expected')==expected(s));s['phase']='resumed'
        s['cue']=s['last'] if s['practice'] or assignment['conditions'][s['block']]=='C' else None
    elif t=='finish':
        require(phase in ['order','resumed']);s['cue']=None
        if s['practice']: s['phase']='comprehension'
        elif s['order']==11: s['phase']='questionnaire'
        else: s.update(phase='order',order=s['order']+1,submitted=[],selected=None,last=None)
    elif t=='comprehension':
        require(phase=='comprehension');require(type(p.get('sequence')) is str and type(p.get('return')) is str)
        # Practice must actually include all checks and the standard interruption.
        passed=p['sequence']=='product,quantity,packaging,delivery' and p['return']=='automatic' and len(s['submitted'])>=4 and all(c in s['submitted'] for c in CATEGORIES)
        s['phase']='ready' if passed else ('instructions' if s['training']<config['training_attempts'] else 'incomplete_training')
    elif t=='block_start':
        require(phase in ['ready','block'] and assignment is not None);s.update(phase='order',practice=False,order=0,submitted=[],selected=None,cue=None,last=None)
    elif t=='questionnaire':
        require(phase=='questionnaire');require(set(p)=={'effort','tracking','frustration'} and all(type(v) is int and 0<=v<=100 for v in p.values()))
        s['phase']='complete' if s['block']==2 else 'break'
    elif t=='break_end': require(phase=='break');s['block']+=1;s['phase']='block'
    else: raise ValueError('Unknown event type')
    return s
