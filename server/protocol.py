import hashlib, json, random, itertools
CATEGORIES = ['product','quantity','packaging','delivery']
RULES = {'fragile':'padded','chilled':'insulated','standard':'ordinary'}
SCHEDULE = {1:2,3:3,4:2,7:3,9:2,11:3}
METRICS = 'hmc-metrics-2'
LEGACY_DEFAULT = dict(version='pilot-1', target=36, pilot_target=[4,6], orders=12, blocks=3,
    interruption_ms=10000, item_ms=2000, acknowledgement_ms=300, break_ms=60000,
    min_width=1280,min_height=720, training_attempts=2, contact='', study_information='',
    seed=481516, schedule_id='irregular-1', metrics_version='hmc-metrics-1',
    questionnaire_version='custom-workload-1', input_method='mouse',
    cue='actual-last-until-first-action', recovery_rule='unobserved-at-order-end',
    instructions='Work accurately and steadily. Check product code, quantity, packaging, then delivery code.',
    consent='Participation is voluntary. You may stop at any time. Previously saved anonymous observations are retained, with withdrawal recorded, and excluded from default analysis exports. Contact the researcher with your completion identifier for the applicable retention policy.')
QUESTIONS = [dict(key='effort',text='Mental effort',low='no effort',high='extreme effort'),dict(key='tracking',text='Difficulty keeping track of progress',low='not difficult',high='extremely difficult'),dict(key='frustration',text='Frustration',low='not frustrated',high='extremely frustrated')]
V2_DEFAULT = LEGACY_DEFAULT | dict(version='pilot-2', metrics_version=METRICS,
    questionnaire_version='raw-tlx-1', training_attempts=6, training_consecutive=2)
# pilot-3 changes presentation only (interface, card salience/label, TLX response format); events and metrics are unchanged.
INTERFACE = 'ergonomic-3'
V3_DEFAULT = V2_DEFAULT | dict(version='pilot-3', questionnaire_version='raw-tlx-2', interface_version=INTERFACE)
PROCEDURE_METRICS = 'hmc-metrics-3'
PROCEDURE_CATEGORIES = ['product','batch','quantity','packaging','delivery','service','dispatch','seal']
PROCEDURE_SCHEDULE = {0:3,1:6,2:2,3:5,4:7,5:4}
DEFAULT = V3_DEFAULT | dict(version='pilot-4', orders=6, schedule_id='eight-check-1',
    metrics_version=PROCEDURE_METRICS, interface_version='placekeeping-4',
    instructions='Work accurately and steadily. Check Product code, Batch code, Quantity, Packaging, Delivery code, Shipping service, Dispatch date, then Seal code.')
def procedural(c): return c.get('metrics_version') == PROCEDURE_METRICS
def categories(c): return PROCEDURE_CATEGORIES if procedural(c) else CATEGORIES
def schedule(c): return PROCEDURE_SCHEDULE if procedural(c) else SCHEDULE
def revised(c): return c.get('metrics_version') in [METRICS, PROCEDURE_METRICS]
def current(c): return procedural(c) and c.get('interface_version') == 'placekeeping-4'
def interface(c): return c.get('interface_version') or ('pilot-2-interface' if revised(c) else 'pilot-1-interface')
def template(c): return DEFAULT if procedural(c) else V3_DEFAULT if 'interface_version' in c else V2_DEFAULT if revised(c) else LEGACY_DEFAULT
def canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(x): return hashlib.sha256(canonical(x).encode()).hexdigest()
def validate_config(c):
    fixed=template(c)
    if set(c)!=set(fixed): raise ValueError('Configuration fields must match the versioned schema')
    for k in fixed:
        if type(c[k]) is not type(fixed[k]): raise ValueError('Invalid configuration type: '+k)
    for k in ['orders','blocks','interruption_ms','item_ms','acknowledgement_ms','break_ms','min_width','min_height','training_attempts','metrics_version','cue','recovery_rule','input_method','schedule_id','questionnaire_version','instructions','consent']+(['interface_version'] if 'interface_version' in c else []):
        if k=='training_attempts' and revised(c): continue
        if c[k]!=fixed[k]: raise ValueError('This implementation supports the fixed protocol only: '+k)
    if revised(c) and not 1<=c['training_consecutive']<=c['training_attempts']<=6: raise ValueError('Invalid practice criterion')
    if not c['version'].strip() or len(c['version'])>80 or c['target']<1: raise ValueError('Invalid version/target')
    if any(len(c[k])>10000 for k in ['contact','study_information']): raise ValueError('Text too long')
    return c

def fixtures():
    sets={}
    for s,offset in [('X',0),('Y',100),('Z',200),('P',300)]:
        rows=[]
        for i in range(12 if s!='P' else 1):
            handling=list(RULES)[i%3]; code=f'PR-{1200+offset+i*7}'; delivery=f'DL-{3400+offset+i*7}'
            match=[(i+j)%4<2 for j in range(4)]
            q=2+i%7
            row=dict(id=f'{s}-{i+1:02}',requested=dict(product=code,quantity=q,handling=handling,delivery=delivery),packed=dict(product=code if match[0] else code[:-1]+str((int(code[-1])+1)%10),quantity=q if match[1] else q+1,packaging=RULES[handling] if match[2] else list(RULES.values())[(i%3+1)%3],delivery=delivery if match[3] else delivery[:-1]+str((int(delivery[-1])+1)%10)))
            rows.append(row)
        sets[s]=rows
    return sets
LEGACY_FIXTURES=fixtures()
# Main X/Y/Z records are unchanged. Extend only separate practice materials.
FIXTURES=fixtures()
FIXTURES['P']=[]
for i in range(9):
    from copy import deepcopy
    o=deepcopy(LEGACY_FIXTURES['X'][i]);o['id']=f'P-{i+1:02}'
    for source in ['requested','packed']:
        for field in ['product','delivery']:
            code=o[source][field];o[source][field]=code[:3]+str(int(code[3:])+3000)
    FIXTURES['P'].append(o)
def answers(o):
    result = dict(product=o['requested']['product']==o['packed']['product'],quantity=o['requested']['quantity']==o['packed']['quantity'],packaging=RULES[o['requested']['handling']]==o['packed']['packaging'],delivery=o['requested']['delivery']==o['packed']['delivery'])
    for field in ['batch','service','dispatch','seal']:
        if field in o['requested']:result[field]=o['requested'][field]==o['packed'][field]
    return result
def secondary(form,episode):
    # Distinct forms, same distance and digit width; balanced left/right.
    return [[31+episode*2+j*3+(7 if form=='V' else 0),35+episode*2+j*3+(7 if form=='V' else 0)][::(-1 if (episode+j)%2 else 1)] for j in range(5)]
def manifest(c,build):
    from .questionnaire import VERSIONS
    fs=PROCEDURE_FIXTURES if procedural(c) else FIXTURES if revised(c) else LEGACY_FIXTURES
    items,instrument=VERSIONS.get(c['questionnaire_version'],(QUESTIONS,{'id':'custom-workload-1'}))
    return dict(config=c,stimulus_version='synthetic-3-eight-check' if procedural(c) else 'synthetic-2-practice' if revised(c) else 'synthetic-1',stimulus_hash=digest(fs),fixtures=fs,answer_keys={s:{o['id']:answers(o) for o in rows} for s,rows in fs.items()},schedule=schedule(c),secondary={f:[(procedure_secondary if procedural(c) else secondary)(f,i) for i in range(6)] for f in ['U','V']},questions=items,questionnaire=instrument,build=build)
def allocation(seed,cycle=0):
    rng=random.Random(f'{seed}:{cycle}'); cs=[''.join(x) for x in itertools.permutations('ABC')]; ts=[''.join(x) for x in itertools.permutations('XYZ')]
    maps={c:rng.sample(ts,6) for c in cs}; rows=[]
    for batch in range(6):
        for c in rng.sample(cs,6):
            rows.append(dict(slot=cycle*36+len(rows),cycle=cycle,batch=batch,conditions=c,task_sets=maps[c][batch],b_form='U' if (batch+cs.index(c))%2==0 else 'V'))
    return rows


def procedure_fixtures():
    """Fixed, reproducible stimulus design; no participant outcomes enter generation.

    Two orders per handling type, one match and one mismatch per category within
    each handling pair. Each set shares the multiset of mismatch counts (2..6),
    but different full answer vectors and record order. Numeric codes are 7 chars.
    """
    sets={}
    # Three complementary pairs: 2/6, 3/5, 4/4 mismatches.
    base=[[False]*2+[True]*6,[False]*3+[True]*5,[False]*4+[True]*4]
    for name,offset in [('X',0),('Y',100),('Z',200),('P',300)]:
        rng=random.Random('eight-check-fixtures-1:'+name)
        rows=[]
        for h,pattern in enumerate(base):
            pattern=pattern.copy();rng.shuffle(pattern)
            for complement in [False,True]:
                matches=[not x if complement else x for x in pattern]
                i=len(rows); handling=list(RULES)[h]
                requested=dict(product=f'PR-{1200+offset+i*7}',batch=f'BT-{2200+offset+i*7}',quantity=2+i,
                    handling=handling,delivery=f'DL-{3400+offset+i*7}',service=['standard','express'][i%2],
                    dispatch=f'2030-06-{11+i:02}',seal=f'SE-{5600+offset+i*7}')
                packed={k:v for k,v in requested.items() if k!='handling'};packed['packaging']=RULES[handling]
                for cat,match in zip(PROCEDURE_CATEGORIES,matches):
                    if match:continue
                    if cat in ['product','batch','delivery','seal']:packed[cat]=packed[cat][:-1]+str((int(packed[cat][-1])+1)%10)
                    elif cat=='quantity':packed[cat]+=1
                    elif cat=='packaging':packed[cat]=list(RULES.values())[(h+1)%3]
                    elif cat=='service':packed[cat]='express' if requested[cat]=='standard' else 'standard'
                    elif cat=='dispatch':packed[cat]=f'2030-06-{12+i:02}'
                rows.append(dict(requested=requested,packed=packed))
        rng.shuffle(rows)
        if name=='P':
            from copy import deepcopy
            for j in range(3):
                row=deepcopy(rows[j])
                for source in ['requested','packed']:
                    for field in ['product','batch','delivery','seal']:
                        code=row[source][field];row[source][field]=code[:3]+str(int(code[3:])+1000)
                rows.append(row)
        for i,row in enumerate(rows):row['id']=f'{name}-E8-{i+1:02}'
        sets[name]=rows
    return sets
PROCEDURE_FIXTURES=procedure_fixtures()

def procedure_secondary(form,episode):
    # Balanced 15 left / 15 right per form, shuffled once, no alternating rule.
    sides=[0]*15+[1]*15
    random.Random('secondary-2:'+form).shuffle(sides)
    return [[31+episode*2+j*3+(7 if form=='V' else 0),35+episode*2+j*3+(7 if form=='V' else 0)][::(-1 if sides[episode*5+j] else 1)] for j in range(5)]
