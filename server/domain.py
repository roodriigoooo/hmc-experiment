"""Version-dispatched deterministic reducers. Historical semantics remain in legacy_domain."""
from copy import deepcopy
from .legacy_domain import initial as legacy_initial, transition as legacy_transition, require
from .protocol import CATEGORIES, SCHEDULE, FIXTURES, answers, revised, procedural, categories, schedule, PROCEDURE_FIXTURES
from .questionnaire import ITEMS, valid_rating

def expected(s): return next((c for c in s.get('categories',CATEGORIES) if c not in s['submitted']),None)

def initial(config=None):
    s=legacy_initial()
    if config and revised(config): s.update(judgment=None,practice_index=0,streak=0,practice_history=[],practice_selections=[],practice_result=None,available=False,secondary_seen=False,return_expected=None)
    if config and procedural(config):s.update(categories=categories(config),schedule=schedule(config))
    return s

def condition(s,a):
    return ('ABC'[s['practice_index']] if s['practice_index']<3 else 'A') if s['practice'] else a['conditions'][s['block']]

def checkpoint(s):
    return len(s['submitted'])==(2 if s['practice'] and s['practice_index'] in [1,2] else {int(k):v for k,v in s.get('schedule',SCHEDULE).items()}.get(s['order']) if not s['practice'] else -1)

def reset_order(s):
    s.update(submitted=[],selected=None,judgment=None,last=None,cue=None,available=False,return_expected=None,secondary_seen=False,practice_history=[],practice_selections=[])

def transition(old,t,p,config,assignment=None):
    if not revised(config): return legacy_transition(old,t,p,config,assignment)
    s=deepcopy(old); phase=s['phase']; cats=categories(config)
    allowed={
      'document':{'reason','width','height','dpr'}, 'withdraw':set(),
      'environment':{'reason','width','height','dpr','hidden','supported'},
      'input_problem':{'reason','input'}, 'pause':{'reason'}, 'resume':{'reason'},
      'consent':{'agree'},'device':{'width','height','input'},'practice_start':set(),'practice_next':set(),
      'select':{'category','expected','cue_removed','input'},'judge':{'judgment','input'},
      'submit':{'category','expected','judgment','input'},'finish':{'expected','cue_removed','input'},
      'ack_end':{'checkpoint','form','episode','acknowledgement_ms'},
      'secondary_ready':set(),'secondary_item':{'item','pair','elapsed_ms'},'secondary_response':{'item','choice','elapsed_ms','input'},
      'return':set(),'task_return_ready':{'expected','cue_appears'},'task_ready':{'kind'},
      'block_start':set(),'questionnaire':{q['key'] for q in ITEMS},'questionnaire_item':{'key','value'},'break_end':set()}
    require(t in allowed and set(p)<=allowed[t],'Invalid event payload fields')
    for k,v in p.items():
        if k in ['width','height','dpr','elapsed_ms','acknowledgement_ms']:require(type(v) in [int,float] and 0<=v<1e12,'Invalid numeric payload')
        if k in ['hidden','supported','cue_removed','cue_appears','checkpoint']:require(type(v) is bool,'Invalid boolean payload')
        if k=='input':require(v in ['mouse','keyboard'],'Invalid input method')
    if t in ['environment','input_problem']:
        require(isinstance(p.get('reason'),str) and len(p['reason'])<=100)
        return s
    if t=='document':
        if phase in ['order','ack','secondary','resumed','returning','break','paused']:
            s['pause_from']=s.get('pause_from') or phase;s['phase']='paused';s['available']=False
        return s
    if t=='withdraw':require(phase not in ['complete','withdrawn']);s['phase']='withdrawn';return s
    if t=='pause':
        require(phase in ['order','ack','secondary','resumed','returning','break'])
        require(p.get('reason') in ['blur','hidden','viewport','technical','unscheduled','external','assistance','input'])
        s.update(pause_from=phase,phase='paused',available=False,selected=None,judgment=None);return s
    if t=='resume':
        require(phase=='paused');previous=s['pause_from'];s.update(pause_from=None,available=False,selected=None,judgment=None)
        s['phase']='returning' if previous in ['secondary','returning'] else 'order' if previous in ['order','resumed','ack'] else previous
        s['cue']=s['last'] if s['phase']=='returning' and condition(s,assignment)=='C' else None
        return s
    if t=='consent':require(phase=='consent' and p.get('agree') is True);s['phase']='device'
    elif t=='device':
        require(phase=='device' and p.get('width',0)>=config['min_width'] and p.get('height',0)>=config['min_height'] and p.get('input')==config['input_method']);s['phase']='instructions'
    elif t in ['practice_start','practice_next']:
        require(phase==('instructions' if t=='practice_start' else 'practice_feedback'))
        if t=='practice_next':
            if s['practice_index']>=3 and s['streak']>=config['training_consecutive']:s['phase']='ready';return s
            if s['practice_index']>=3 and s['training']>=config['training_attempts']:s['phase']='incomplete_training';return s
            s['practice_index']+=1
        reset_order(s);s.update(phase='order',practice=True)
        if s['practice_index']>=3:s['training']+=1
    elif t=='block_start':
        require(phase in ['ready','block'] and assignment is not None);reset_order(s);s.update(phase='order',practice=False,order=0)
    elif t=='task_ready':
        require(phase=='order' and not s['available']);s['available']=True
    elif t=='select':
        require(phase in ['order','resumed'] and s['available'] and p.get('category') in cats)
        require(p.get('expected')==expected(s),'Expected category mismatch')
        s.update(selected=p['category'],judgment=None,cue=None)
        if s['practice']:s['practice_selections'].append(p['category'])
    elif t=='judge':
        require(phase in ['order','resumed'] and s['available'] and s['selected'] and type(p.get('judgment')) is bool)
        s['judgment']=p['judgment']
    elif t=='submit':
        require(phase in ['order','resumed'] and s['available'] and s['selected'] is not None and type(s['judgment']) is bool)
        require(p.get('category')==s['selected'] and type(p.get('judgment')) is bool and p['judgment']==s['judgment'] and p.get('expected')==expected(s),'Submission context mismatch')
        if s['practice']:s['practice_history'].append(dict(category=s['selected'],judgment=s['judgment']))
        s['submitted'].append(s['selected']);s.update(last=s['selected'],selected=None,judgment=None,phase='ack',available=False)
    elif t=='ack_end':
        require(phase=='ack');s['phase']='secondary' if checkpoint(s) and condition(s,assignment)!='A' else 'order';s['available']=False
    elif t=='secondary_ready':require(phase=='secondary' and not s['available']);s['available']=True;s['secondary_seen']=True
    elif t in ['secondary_item','secondary_response']:
        require(phase=='secondary' and s['available'] and type(p.get('item')) is int and 0<=p['item']<5)
        if t=='secondary_response':require(type(p.get('choice')) is int and p['choice'] in [0,1])
    elif t=='return':
        require(phase=='secondary');s.update(phase='returning',available=False,selected=None,judgment=None,cue=s['last'] if condition(s,assignment)=='C' else None)
    elif t=='task_return_ready':
        require(phase=='returning' and not s['available']);require(p.get('expected')==expected(s) and p.get('cue_appears')==(condition(s,assignment)=='C'))
        s.update(phase='resumed',available=True,return_expected=expected(s))
    elif t=='finish':
        require(phase in ['order','resumed'] and s['available']);s.update(cue=None,available=False,selected=None,judgment=None)
        if s['practice']:
            # Guided demonstration requires exposure to the whole procedure before progression.
            if s['practice_index']<3:
                require(all(c in s['submitted'] for c in cats) and (s['practice_index']==0 or s['secondary_seen']),'Complete the demonstration checks')
            key=answers((PROCEDURE_FIXTURES if procedural(config) else FIXTURES)['P'][s['practice_index']]);history=s['practice_history']
            sequence=s['submitted']==cats and s['practice_selections']==cats
            correct=len(history)==len(cats) and all(x['judgment']==key[x['category']] for x in history)
            s['practice_result']=dict(passed=sequence and correct,sequence=sequence,correct=correct,answer_key=key,history=history)
            if s['practice_index']>=3:s['streak']=s['streak']+1 if sequence and correct else 0
            s['phase']='practice_feedback'
        elif s['order']==config['orders']-1:s['phase']='questionnaire'
        else:reset_order(s);s.update(phase='order',order=s['order']+1)
    elif t=='questionnaire_item':
        require(phase=='questionnaire' and p.get('key') in {q['key'] for q in ITEMS} and valid_rating(p.get('value')))
    elif t=='questionnaire':
        require(phase=='questionnaire' and set(p)=={q['key'] for q in ITEMS} and all(valid_rating(v) for v in p.values()))
        s['phase']='complete' if s['block']==2 else 'break'
    elif t=='break_end':require(phase=='break');s['block']+=1;s['phase']='block'
    return s
