"""Versioned administration; exact NASA scale-sheet questions, not weighted TLX."""
SOURCE='https://human-factors.arc.nasa.gov/groups/TLX/downloads/TLXScale.pdf'
METHOD='https://www.nasa.gov/wp-content/uploads/2026/01/hfes-2006-paper.pdf'
INSTRUMENT=dict(id='raw-tlx-1', name='Unweighted Raw NASA-TLX', verified=True,
    wording_source=SOURCE, method_source=METHOD, verified_date='2026-10-30',
    minimum=0, maximum=100, step=5, orientation='displayed score equals workload score; no reversal',
    aggregation='arithmetic mean of all six TLX ratings; no pairwise weights; incomplete = null',
    instruction='Rate the entire preceding block, including secondary tasks where present. Choose a number from 0 to 100 in steps of 5 for every item. You may withdraw instead of answering.')
ITEMS=[]
for key,title,text in [
 ('mental','Mental Demand','How mentally demanding was the task?'),
 ('physical','Physical Demand','How physically demanding was the task?'),
 ('temporal','Temporal Demand','How hurried or rushed was the pace of the task?'),
 ('performance','Performance','How successful were you in accomplishing what you were asked to do?'),
 ('effort','Effort','How hard did you have to work to accomplish your level of performance?'),
 ('frustration','Frustration','How insecure, discouraged, irritated, stressed, and annoyed were you?')]:
    ITEMS.append(dict(key=key,title=title,text=text,low='Perfect' if key=='performance' else 'Very Low',
        high='Failure' if key=='performance' else 'Very High',step=5,aggregate=True,orientation='identity',source=SOURCE))
ITEMS.append(dict(key='tracking',title='Exploratory progress tracking (separate item)',
    text='How difficult was it to keep track of which checks you had already submitted?',
    low='not at all difficult',high='extremely difficult',step=5,aggregate=False,orientation='identity',source='Study-specific; not independently validated'))
TLX_KEYS=[q['key'] for q in ITEMS if q['aggregate']]
# raw-tlx-2: identical TLX wording, keys, range and scoring; administered as a 21-mark scale per item
# (the scale-sheet layout) instead of typed numbers, and the exploratory item has a plain participant title.
INSTRUMENT_V2=INSTRUMENT|dict(id='raw-tlx-2',
    administration='one horizontal 21-mark scale per item (0-100 in steps of 5), endpoint labels only, no numerals, no default mark',
    instruction='Rate the entire preceding block, including secondary tasks where present. Click one mark on each scale. Every item needs an answer. You may withdraw instead of answering.')
ITEMS_V2=[q|dict(title='Keeping track') if q['key']=='tracking' else dict(q) for q in ITEMS]
VERSIONS={'raw-tlx-1':(ITEMS,INSTRUMENT),'raw-tlx-2':(ITEMS_V2,INSTRUMENT_V2)}
def valid_rating(v): return type(v) is int and 0<=v<=100 and v%5==0

def score(responses):
    values=[responses.get(k) for k in TLX_KEYS]
    return sum(values)/6 if all(valid_rating(v) for v in values) else None
