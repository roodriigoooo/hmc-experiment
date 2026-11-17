"""Pure recomputation from accepted raw events; milliseconds, never cross-clock subtraction."""
import statistics
from .protocol import answers, CATEGORIES, SCHEDULE
METRICS = 'hmc-metrics-1'

def union(intervals):
    end=None;total=0
    for a,b in sorted(intervals):
        if b<a: continue
        total+=max(0,b-max(a,end if end is not None else a));end=max(b,end if end is not None else b)
    return total

def delta(a,b): return b['mono']-a['mono'] if a and b and a['segment']==b['segment'] else None

def derive(events,manifest,assignment):
    checks=[];orders=[];interruptions=[];questionnaires=[];summaries=[];quality=[]
    for e in events:
        if e['type'] in ['pause','document','resume'] and not e['context']['practice']: quality.append(dict(seq=e['seq'],block=e['context']['block'],order=e['context']['order'],reason=e['payload'].get('reason',e['type']),segment=e['segment']))
    for block in range(1,4):
        es=[e for e in events if not e['context']['practice'] and e['context']['block']==block]
        # block_start is recorded with pre-transition practice=True in block 1.
        starts=[e for e in events if e['type']=='block_start' and e['context']['block']==block]
        if not starts: continue
        cond=assignment['conditions'][block-1];taskset=assignment['task_sets'][block-1]
        secondary_intervals={};pause_intervals={};block_interruptions=[]
        for oi in range(12):
            oe=[e for e in es if e['context']['order']==oi];sub=[e for e in oe if e['type']=='submit'];finish=next((e for e in oe if e['type']=='finish'),None)
            if not oe: continue
            key=answers(manifest['fixtures'][taskset][oi]);oc=[]
            for cat in CATEGORIES:
                attempts=[e for e in sub if e['payload']['category']==cat]
                row=dict(block=block,condition=cond,task_set=taskset,order=oi,category=cat,attempts=len(attempts),first=attempts[0]['payload']['judgment'] if attempts else None,final=attempts[-1]['payload']['judgment'] if attempts else None,first_correct=bool(attempts and attempts[0]['payload']['judgment']==key[cat]),final_correct=bool(attempts and attempts[-1]['payload']['judgment']==key[cat]),omitted=not attempts,completed=finish is not None)
                checks.append(row);oc.append(row)
            orders.append(dict(block=block,condition=cond,task_set=taskset,order=oi,completed=finish is not None,correct=sum(x['final_correct'] for x in oc),denominator=4,omissions=sum(x['omitted'] for x in oc),duplicates=sum(max(0,x['attempts']-1) for x in oc),out_of_sequence=sum(e['payload'].get('category')!=e['context']['expected'] for e in oe if e['type'] in ['select','submit']),missed_checkpoint=bool(finish and oi in SCHEDULE and not any(e['type']=='ack_end' and e['payload'].get('checkpoint') for e in oe)),missed_reason=('order_ended_early' if len(sub)<SCHEDULE[oi] else 'technical_disruption') if finish and oi in SCHEDULE and not any(e['type']=='ack_end' and e['payload'].get('checkpoint') for e in oe) else None))
            for start in [e for e in oe if e['type']=='ack_end' and e['payload'].get('checkpoint')]:
                if cond=='A': continue
                ret=next((e for e in oe if e['seq']>start['seq'] and e['type'] in ['return','resume']),None)
                visible_end=next((e for e in oe if e['seq']>start['seq'] and e['type'] in ['pause','document','return','resume']),None)
                dur=delta(start,visible_end)
                if dur is not None: secondary_intervals.setdefault(start['segment'],[]).append((start['mono'],visible_end['mono']))
                expected=ret['context']['expected'] if ret else start['context']['expected']
                after=[e for e in oe if ret and e['seq']>ret['seq']]
                actions=[e for e in after if e['type'] in ['select','finish']]
                appropriate=next((e for e in actions if e['type']=='select' and e['payload']['category']==expected),None)
                first=actions[0] if actions else None;fs=next((e for e in after if e['type']=='submit'),None)
                bad=any(e['type'] in ['pause','document'] for e in oe)
                items=[e for e in oe if start['seq']<e['seq'] and (not ret or e['seq']<ret['seq']) and e['type']=='secondary_response']
                unique={e['payload']['item']:e for e in items};form=start['payload'].get('form');pairs=manifest['secondary'].get(form,[[]]*6)[start['payload'].get('episode',0)]
                row=dict(block=block,condition=cond,task_set=taskset,order=oi,interruption_id=start['id'],segment=start['segment'],start_ms=start['mono'],secondary_end_ms=visible_end['mono'] if visible_end else None,secondary_end_segment=visible_end['segment'] if visible_end else None,return_ms=ret['mono'] if ret else None,actual_secondary_ms=dur,expected_at_return=expected,prior_sequence_deviation=any(e['payload'].get('category')!=e['context']['expected'] for e in oe if e['seq']<start['seq'] and e['type'] in ['select','submit']),technically_compromised=bad or dur is None or abs(dur-10000)>250 or any(abs(e['mono']-start['mono']-e['payload']['item']*2000)>250 for e in oe if e['type']=='secondary_item' and e['seq']>start['seq']),recovery_ms=delta(ret,appropriate),recovery_observed=appropriate is not None and delta(ret,appropriate) is not None,unobserved_reason=None if appropriate and delta(ret,appropriate) is not None else ('no_remaining_check' if expected is None else 'clock_discontinuity' if appropriate else 'order_ended' if finish else 'incomplete_session'),window_end_ms=finish['mono'] if finish else (oe[-1]['mono'] if oe else None),window_end_segment=finish['segment'] if finish else (oe[-1]['segment'] if oe else None),first_action_ms=delta(ret,first),first_action_sequence_error=bool(first and expected is not None and (first['type']=='finish' or first['payload'].get('category')!=expected)),first_submission_ms=delta(ret,fs),first_submission_category=fs['payload']['category'] if fs else None,first_submission_correct=(fs['payload']['judgment']==key[fs['payload']['category']]) if fs else None,secondary_form=form,secondary_responses=len(unique),secondary_omissions=5-len(unique),secondary_correct=sum(pairs[j][e['payload']['choice']]==max(pairs[j]) for j,e in unique.items()) if pairs else None)
                interruptions.append(row);block_interruptions.append(row)
        for i,e in enumerate(es):
            if e['type']=='pause':
                r=next((r for r in es[i+1:] if r['type']=='resume'),None)
                if delta(e,r) is not None:pause_intervals.setdefault(e['segment'],[]).append((e['mono'],r['mono']))
        q=next((e['payload'] for e in es if e['type']=='questionnaire'),None)
        if q:questionnaires.append(dict(block=block,condition=cond,version=manifest['config']['questionnaire_version'],**q))
        end=next((e for e in reversed(es) if e['type']=='finish'),None);elapsed=delta(starts[0],end)
        cross=len({e['segment'] for e in [starts[0]]+es})>1
        if cross or not end or end['context']['order']!=11: elapsed=None
        sec=sum(union(v) for v in secondary_intervals.values());pause=sum(union(v) for v in pause_intervals.values());excluded=sum(union(secondary_intervals.get(k,[])+pause_intervals.get(k,[])) for k in secondary_intervals.keys()|pause_intervals.keys())
        completed=[o for o in orders if o['block']==block and o['completed']];observed=[r['recovery_ms'] for r in block_interruptions if r['recovery_observed']]
        summaries.append(dict(metrics_version=METRICS,block=block,condition=cond,condition_order=assignment['conditions'],task_set=taskset,prior_cue_exposure='C' in assignment['conditions'][:block-1],practice_cue_exposure=True,eligible_recoveries=sum(r['expected_at_return'] is not None for r in block_interruptions),observed_recoveries=len(observed),unobserved_recoveries=sum(not r['recovery_observed'] for r in block_interruptions),flagged_recoveries=sum(r['technically_compromised'] for r in block_interruptions),valid_recoveries=sum(r['recovery_observed'] and not r['technically_compromised'] for r in block_interruptions),mean_recovery_ms=statistics.mean(observed) if observed else None,median_recovery_ms=statistics.median(observed) if observed else None,total_elapsed_ms=elapsed,secondary_union_ms=sec,technical_pause_union_ms=pause,excluded_union_ms=excluded,active_ms=max(0,elapsed-excluded) if elapsed is not None else None,timing_compromised=cross or any(q['block']==block for q in quality),completed_orders=len(completed),accuracy_numerator=sum(o['correct'] for o in completed),accuracy_denominator=4*len(completed),omissions=sum(o['omissions'] for o in completed),duplicates=sum(o['duplicates'] for o in completed),sequence_errors=sum(o['out_of_sequence'] for o in completed),workload=q))
    practice_attempts=[]
    for start in [e for e in events if e['type']=='practice_start']:
        end=next((e for e in events if e['seq']>start['seq'] and e['type']=='comprehension'),None)
        attempts=[e for e in events if e['seq']>start['seq'] and (not end or e['seq']<end['seq']) and e['context']['practice']]
        practice_attempts.append(dict(attempt=len(practice_attempts)+1,start_seq=start['seq'],end_seq=end['seq'] if end else None,submissions=sum(e['type']=='submit' for e in attempts),comprehension=end['payload'] if end else None,completed=end is not None))
    return dict(orders=orders,checks=checks,interruptions=interruptions,questionnaires=questionnaires,summaries=summaries,quality=quality,practice_attempts=practice_attempts)
