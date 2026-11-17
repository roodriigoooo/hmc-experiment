"""Pure version-dispatched derivation. All behavioral intervals use document clocks."""
import statistics
from .legacy_metrics import derive as legacy_derive, union, delta
from .protocol import CATEGORIES, SCHEDULE, answers, revised, METRICS, procedural, categories, schedule
from .questionnaire import score

def first(events,kind):return next((e for e in events if e['type']==kind),None)
def point(e):return {'seq':e['seq'],'mono':e['mono'],'segment':e['segment']} if e else None

def latency(start,action,end,expected=True):
    value=delta(start,action) if expected else None
    reason=None if value is not None else ('not_applicable_no_remaining_check' if not expected else 'return_not_observed' if not start else 'clock_discontinuity' if action else 'order_ended' if end and end['type']=='finish' else 'withdrawn' if end and end['type']=='withdraw' else 'incomplete_session')
    return dict(ms=value,observed=value is not None,reason=reason)

def describe(rows,field):
    values=[r[field] for r in rows if r.get(field) is not None]
    return dict(observed=len(values),unobserved=sum(r.get('applicable',True) and r.get(field) is None for r in rows),not_applicable=sum(not r.get('applicable',True) for r in rows),mean=statistics.mean(values) if values else None,median=statistics.median(values) if values else None)

def derive(events,manifest,assignment):
    if not procedural(manifest['config']):
        from .v2_metrics import derive as previous_derive
        return previous_derive(events,manifest,assignment)
    CATEGORIES=categories(manifest['config']);SCHEDULE=schedule(manifest['config'])
    tables={k:[] for k in ['orders','checks','submitted_checks','interruptions','transitions','secondary_items','intervals','questionnaires','questionnaire_items','summaries','quality','practice_attempts','participant_contrasts']}
    config=manifest['config']
    for e in events:
        if e['type'] in ['environment','input_problem','pause','document','resume']:
            tables['quality'].append(dict(seq=e['seq'],block=e['context']['block'],order=e['context']['order'],practice=e['context']['practice'],event=e['type'],segment=e['segment'],mono=e['mono'],reason=e['payload'].get('reason',e['type']),details=e['payload'],technical=True))
    # Training remains exportable even when no main allocation is ever issued.
    for index in sorted({e['context'].get('practice_index') for e in events if e['context']['practice'] and e['context'].get('practice_index') is not None}):
        es=[e for e in events if e['context']['practice'] and e['context'].get('practice_index')==index]
        start=first(es,'task_ready');finish=first(es,'finish')
        if not start:continue
        submitted=[e for e in es if e['type']=='submit'];selected=[e['payload']['category'] for e in es if e['type']=='select']
        key=answers(manifest['fixtures']['P'][index])
        passed=bool(finish and selected==CATEGORIES and [e['payload']['category'] for e in submitted]==CATEGORIES and all(e['payload']['judgment']==key[e['payload']['category']] for e in submitted))
        tables['practice_attempts'].append(dict(practice_index=index,stage='demonstration' if index<3 else 'assessed',attempt=None if index<3 else index-2,condition='ABC'[index] if index<3 else 'A',start=point(start),end=point(finish),passed=passed if finish else None,submitted=len(submitted),sequence=selected,interruption_exposures=sum(e['type']=='secondary_ready' for e in es),cue_exposures=sum(e['type']=='task_return_ready' and e['payload']['cue_appears'] for e in es)))
    if not assignment:return tables
    for block in range(1,4):
        block_start=next((e for e in events if e['type']=='block_start' and e['context']['block']==block),None)
        if not block_start:continue
        es=[e for e in events if e['seq']>block_start['seq'] and e['context']['block']==block and not e['context']['practice']]
        cond=assignment['conditions'][block-1];taskset=assignment['task_sets'][block-1]
        base=dict(block=block,condition=cond,task_set=taskset)
        start=first(es,'task_ready');finishes=[e for e in es if e['type']=='finish']
        end=finishes[-1] if finishes and finishes[-1]['context']['order']==config['orders']-1 else None
        last=end or next((e for e in es if e['type']=='withdraw'),None) or (es[-1] if es else block_start)
        timing_events=[e for e in es if e['seq']<=last['seq']]
        spans=[]
        for e in timing_events:
            if e['type']=='pause':
                stop=next((r for r in timing_events if r['seq']>e['seq'] and r['type'] in ['task_ready','task_return_ready']),None)
                spans.append((e,stop,'pause',e['payload']['reason']))
        block_rows=[];block_orders=[];block_checks=[]
        for oi in range(config['orders']):
            oe=[e for e in es if e['context']['order']==oi]
            finish=first(oe,'finish');sub=[e for e in oe if e['type']=='submit'];sels=[e for e in oe if e['type']=='select']
            exposed=first(oe,'task_ready') is not None
            key=answers(manifest['fixtures'][taskset][oi]);ob=base|dict(order=oi,stimulus_id=manifest['fixtures'][taskset][oi]['id'])
            check_rows=[]
            for cat in CATEGORIES:
                attempts=[e for e in sub if e['payload']['category']==cat]
                row=ob|dict(category=cat,exposed=exposed,completed=finish is not None,attempts=len(attempts),omitted=not attempts,first=attempts[0]['payload']['judgment'] if attempts else None,final=attempts[-1]['payload']['judgment'] if attempts else None,first_correct=bool(attempts and attempts[0]['payload']['judgment']==key[cat]),final_correct=bool(attempts and attempts[-1]['payload']['judgment']==key[cat]))
                check_rows.append(row)
            tables['checks']+=check_rows;block_checks+=check_rows
            for e in sub:tables['submitted_checks'].append(ob|dict(seq=e['seq'],segment=e['segment'],mono=e['mono'],category=e['payload']['category'],judgment=e['payload']['judgment'],correct=e['payload']['judgment']==key[e['payload']['category']],expected=e['context']['expected'],out_of_sequence=e['payload']['category']!=e['context']['expected']))
            checkpoints=[e for e in oe if e['type']=='ack_end' and e['payload'].get('checkpoint')]
            o=ob|dict(exposed=exposed,completed=finish is not None,correct=sum(c['final_correct'] for c in check_rows),first_correct=sum(c['first_correct'] for c in check_rows),denominator=len(CATEGORIES),omissions=sum(c['omitted'] for c in check_rows),duplicates=sum(max(0,c['attempts']-1) for c in check_rows),out_of_sequence_selections=sum(e['payload']['category']!=e['context']['expected'] for e in sels),out_of_sequence_submissions=sum(e['payload']['category']!=e['context']['expected'] for e in sub),premature_finish=bool(finish and finish['context']['expected'] is not None),scheduled_checkpoint=oi in SCHEDULE,missed_checkpoint=oi in SCHEDULE and not checkpoints,missed_reason=None if oi not in SCHEDULE or checkpoints else 'order_ended_before_checkpoint' if finish else 'not_exposed' if not exposed else 'incomplete_or_disrupted')
            tables['orders'].append(o);block_orders.append(o)
            for checkpoint in checkpoints:
                after_checkpoint=[e for e in oe if e['seq']>checkpoint['seq']]
                onset=first(after_checkpoint,'secondary_ready') if cond!='A' else None
                ret=first(after_checkpoint,'task_return_ready') if cond!='A' else first(after_checkpoint,'task_ready')
                stop=next((e for e in after_checkpoint if e['type'] in ['return','pause','document','withdraw']),None) if cond!='A' else None
                if cond!='A':spans.append((checkpoint,stop,'secondary','standardized_secondary_task'))
                expected=ret['context']['expected'] if ret else checkpoint['context']['expected']
                after=[e for e in oe if ret and e['seq']>ret['seq'] and (not finish or e['seq']<=finish['seq'])]
                window_end=finish or next((e for e in after if e['type']=='withdraw'),None) or (oe[-1] if oe else checkpoint)
                actions=[e for e in after if e['type'] in ['select','finish']]
                action=actions[0] if actions else None
                selection=next((e for e in after if e['type']=='select' and e['payload']['category']==expected),None)
                submission=first(after,'submit')
                expected_submission=next((e for e in after if e['type']=='submit' and e['payload']['category']==expected),None)
                selection_latency=latency(ret,selection,window_end,expected is not None)
                submission_latency=latency(ret,expected_submission,window_end,expected is not None)
                history=[dict(seq=e['seq'],category=e['payload']['category'],judgment=e['payload']['judgment']) for e in sub if e['seq']<checkpoint['seq']]
                technical=[e for e in oe if e['type'] in ['pause','document','input_problem'] or e['type']=='environment' and e['payload'].get('reason') in ['blur','hidden','viewport','external','assistance','input']]
                reasons=sorted(set(e['payload'].get('reason',e['type']) for e in technical))
                if not ret:reasons.append('return_not_observed')
                if ret and any(e['segment']!=ret['segment'] for e in [checkpoint,window_end]):reasons.append('clock_discontinuity')
                duration=delta(checkpoint,stop);exposure=delta(onset,stop)
                if cond!='A' and (exposure is None or abs(exposure-config['interruption_ms'])>250):reasons.append('secondary_duration_deviation')
                engagement=[e for e in after_checkpoint if not ret or e['seq']<ret['seq']]
                items=[e for e in engagement if e['type']=='secondary_item']
                responses={e['payload']['item']:e for e in engagement if e['type']=='secondary_response'}
                if cond!='A' and (len(items)!=5 or any(delta(onset,item) is None or abs(delta(onset,item)-item['payload']['item']*config['item_ms'])>250 for item in items)):
                    reasons.append('secondary_item_exposure_deviation')
                form=checkpoint['payload']['form'];episode=checkpoint['payload']['episode'];pairs=manifest['secondary'][form][episode]
                for j in range(5) if cond!='A' else []:
                    item=next((e for e in items if e['payload']['item']==j),None)
                    item_end=next((e for e in engagement if item and e['seq']>item['seq'] and e['type'] in ['secondary_item','return','pause','document','withdraw']),None)
                    response=responses.get(j)
                    tables['secondary_items'].append(ob|dict(interruption_id=checkpoint['id'],form=form,episode=episode,item=j,pair=pairs[j],onset=point(item),end=point(item_end),actual_exposure_ms=delta(item,item_end),displayed=item is not None,response=point(response),choice=response['payload']['choice'] if response else None,omitted=response is None,correct=bool(response and pairs[j][response['payload']['choice']]==max(pairs[j]))))
                row=ob|dict(interruption_id=checkpoint['id'],measurement='ordinary_transition' if cond=='A' else 'interruption_return',checkpoint_position=len(history),secondary_form=form if cond!='A' else None,secondary_episode=episode,segment=checkpoint['segment'],start_ms=checkpoint['mono'],secondary_end_ms=stop['mono'] if stop else None,secondary_end_segment=stop['segment'] if stop else None,return_ms=ret['mono'] if ret else None,return_segment=ret['segment'] if ret else None,return_ready=point(ret),secondary_onset=point(onset),actual_secondary_ms=duration,stimulus_exposure_ms=exposure,pre_interruption_history=history,last_submitted=history[-1]['category'] if history else None,expected_at_return=expected,expected_next_check=expected,applicable=expected is not None,not_applicable_reason='no_remaining_check' if expected is None else None,prior_sequence_deviation=any(e['payload']['category']!=e['context']['expected'] for e in oe if e['seq']<checkpoint['seq'] and e['type'] in ['select','submit']),technically_compromised=bool(reasons),invalid_timing_reasons=reasons,recovery_ms=selection_latency['ms'],appropriate_next_check_selection_ms=selection_latency['ms'],recovery_observed=selection_latency['observed'],unobserved_reason=selection_latency['reason'],window_end=point(window_end),window_end_ms=window_end['mono'],window_end_segment=window_end['segment'],first_action_ms=delta(ret,action),first_action_type=action['type'] if action else None,first_action_category=action['payload'].get('category') if action else None,first_action_sequence_error=(action['payload'].get('category')!=expected if action['type']=='select' else expected is not None) if action and expected is not None else None,first_submission_ms=delta(ret,submission),first_submission_category=submission['payload']['category'] if submission else None,first_submission_correct=submission['payload']['judgment']==key[submission['payload']['category']] if submission else None,expected_check_submission_ms=submission_latency['ms'],expected_submission_observed=submission_latency['observed'],expected_submission_unobserved_reason=submission_latency['reason'],expected_submission_correct=expected_submission['payload']['judgment']==key[expected] if expected_submission else None,secondary_responses=len(responses),secondary_omissions=5-len(responses) if cond!='A' else None,secondary_correct=sum(pairs[j][e['payload']['choice']]==max(pairs[j]) for j,e in responses.items()) if cond!='A' else None)
                # Executed continuation is distinct from initial selection and judgment accuracy.
                committed=next((e for e in after if e['type'] in ['submit','finish']),None)
                procedure_error=(committed['type']=='finish' or committed['payload']['category']!=expected) if committed and ret and expected is not None else None
                observed=procedure_error is not None
                reason=None if observed else 'not_applicable_no_remaining_check' if expected is None else 'return_not_observed' if not ret else 'withdrawn' if window_end['type']=='withdraw' else 'no_committed_action_before_window_end'
                # Flags concern exposure and the continuation window, not unrelated later actions.
                procedure_stop=committed or window_end
                disruptions=[e for e in oe if checkpoint['seq']<=e['seq']<=procedure_stop['seq'] and (e['type'] in ['pause','document','input_problem'] or e['type']=='environment' and e['payload'].get('reason') in ['blur','hidden','viewport','external','assistance','input'])]
                procedure_reasons=sorted(set(e['payload'].get('reason',e['type']) for e in disruptions))
                procedure_reasons+= [r for r in reasons if r in ['return_not_observed','secondary_duration_deviation','secondary_item_exposure_deviation']]
                row.update(primary_outcome='first_committed_continuation_error',first_committed_action=point(committed),
                    first_committed_type=committed['type'] if committed else None,
                    first_committed_category=committed['payload'].get('category') if committed else None,
                    first_committed_correct=committed['payload']['judgment']==key[committed['payload']['category']] if committed and committed['type']=='submit' else None,
                    first_committed_ms=delta(ret,committed),procedure_error=procedure_error,
                    procedure_observed=observed,procedure_unobserved_reason=reason,procedure_window_end=point(procedure_stop),
                    procedure_review_reasons=procedure_reasons,procedure_flagged=bool(procedure_reasons),
                    corrected_selection_before_commit=bool(action and action['type']=='select' and row['first_action_sequence_error'] and observed and not procedure_error))
                tables['transitions' if cond=='A' else 'interruptions'].append(row)
                if cond!='A':block_rows.append(row)
        # Preserve all interval components. Only valid same-segment spans enter unions.
        interval_groups={'secondary':{},'pause':{}}
        for begin,stop,kind,reason in spans:
            duration=delta(begin,stop)
            clipped=None
            if duration is not None and start and start['segment']==begin['segment'] and last['segment']==begin['segment']:
                clipped=(max(start['mono'],begin['mono']),min(last['mono'],stop['mono']))
                if clipped[1]>=clipped[0]:interval_groups[kind].setdefault(begin['segment'],[]).append(clipped)
            tables['intervals'].append(base|dict(kind=kind,reason=reason,start=point(begin),end=point(stop),duration_ms=duration,clipped=clipped,invalid_reason='clock_discontinuity_or_open_interval' if duration is None else None))
        sec=sum(union(v) for v in interval_groups['secondary'].values());pause=sum(union(v) for v in interval_groups['pause'].values())
        segments=set(interval_groups['secondary'])|set(interval_groups['pause'])
        excluded=sum(union(interval_groups['secondary'].get(seg,[])+interval_groups['pause'].get(seg,[])) for seg in segments)
        cross=len({e['segment'] for e in timing_events+[block_start]})>1
        elapsed=delta(start,end) if not cross else None
        invalid=[]
        if cross:invalid.append('clock_discontinuity')
        if not start:invalid.append('start_not_observed')
        if not end:invalid.append('incomplete_block')
        if any(delta(a,b) is None for a,b,_,_ in spans):invalid.append('open_or_discontinuous_interval')
        qevent=first(es,'questionnaire');ratings=qevent['payload'] if qevent else {}
        changes=[e for e in es if e['type']=='questionnaire_item']
        draft={e['payload']['key']:e['payload']['value'] for e in changes}
        for q in manifest['questions']:
            value=ratings.get(q['key'],draft.get(q['key']))
            tables['questionnaire_items'].append(base|dict(instrument=config['questionnaire_version'],key=q['key'],title=q['title'],wording=q['text'],low=q['low'],high=q['high'],step=q['step'],included_in_tlx=q['aggregate'],displayed_response=value,oriented_score=value,orientation=q['orientation'],answered=value is not None,submitted=qevent is not None))
        tlx=score(ratings) if qevent else None
        tables['questionnaires'].append(base|dict(version=config['questionnaire_version'],responses=ratings or draft,submitted=qevent is not None,answered_items=len(ratings or draft),raw_tlx=tlx,exploratory_tracking=(ratings or draft).get('tracking')))
        observed=describe(block_rows,'recovery_ms');all_outcomes={field:describe(block_rows,field) for field in ['appropriate_next_check_selection_ms','first_action_ms','first_submission_ms','expected_check_submission_ms']}
        quality=any(q['block']==block and not q['practice'] for q in tables['quality'])
        tables['summaries'].append(base|dict(metrics_version=config['metrics_version'],condition_order=assignment['conditions'],prior_cue_exposure='C' in assignment['conditions'][:block-1],practice_cue_exposure=True,scheduled_checkpoints=len(SCHEDULE),actual_interruptions=sum(r['secondary_onset'] is not None for r in block_rows),eligible_recoveries=sum(r['applicable'] for r in block_rows),observed_recoveries=observed['observed'],unobserved_recoveries=observed['unobserved'],not_applicable_recoveries=observed['not_applicable'],flagged_recoveries=sum(r['technically_compromised'] for r in block_rows),mean_recovery_ms=observed['mean'],median_recovery_ms=observed['median'],latency_summaries=all_outcomes,first_action_sequence_error_numerator=sum(r['first_action_sequence_error'] is True for r in block_rows),first_action_sequence_error_denominator=sum(r['first_action_sequence_error'] is not None for r in block_rows),total_elapsed_ms=elapsed,secondary_union_ms=sec,technical_pause_union_ms=pause,excluded_union_ms=excluded,active_ms=max(0,elapsed-excluded) if elapsed is not None and not invalid else None,invalid_timing_reasons=invalid,timing_compromised=quality or bool(invalid),completed_orders=sum(o['completed'] for o in block_orders),exposed_orders=sum(o['exposed'] for o in block_orders),accuracy_numerator=sum(c['final_correct'] for c in block_checks),accuracy_denominator=config['orders']*len(CATEGORIES),exposed_accuracy_denominator=sum(c['exposed'] for c in block_checks),first_accuracy_numerator=sum(c['first_correct'] for c in block_checks),first_accuracy_denominator=config['orders']*len(CATEGORIES),omissions=sum(c['omitted'] for c in block_checks),exposed_omissions=sum(c['omitted'] and c['exposed'] for c in block_checks),duplicates=sum(o['duplicates'] for o in block_orders),out_of_sequence_selections=sum(o['out_of_sequence_selections'] for o in block_orders),out_of_sequence_submissions=sum(o['out_of_sequence_submissions'] for o in block_orders),premature_finishes=sum(o['premature_finish'] for o in block_orders),raw_tlx=tlx,workload=ratings or None))
    for summary in tables['summaries']:
        b=summary['block'];episodes=[r for r in tables['interruptions']+tables['transitions'] if r['block']==b]
        observed=[r for r in episodes if r['procedure_observed']]
        clean=[r for r in observed if not r['procedure_flagged']]
        finished=[r for r in tables['checks'] if r['block']==b and r['completed']]
        summary.update(primary_outcome='first_committed_continuation_error',
            procedure_error_numerator=sum(r['procedure_error'] for r in observed),procedure_error_denominator=len(observed),
            procedure_error_rate=sum(r['procedure_error'] for r in observed)/len(observed) if observed else None,
            procedure_unobserved=sum(r['applicable'] and not r['procedure_observed'] for r in episodes),
            procedure_not_applicable=sum(not r['applicable'] for r in episodes),
            checkpoints_not_reached=summary['scheduled_checkpoints']-len(episodes),
            procedure_flagged_observed=sum(r['procedure_flagged'] for r in observed),
            unflagged_procedure_error_numerator=sum(r['procedure_error'] for r in clean),unflagged_procedure_error_denominator=len(clean),
            corrected_selections=sum(r['corrected_selection_before_commit'] for r in episodes),
            planned_accuracy_denominator=config['orders']*len(CATEGORIES),
            accuracy_numerator=sum(r['final_correct'] for r in finished),accuracy_denominator=len(finished),
            first_accuracy_numerator=sum(r['first_correct'] for r in finished),first_accuracy_denominator=len(finished),
            omissions=sum(r['omitted'] for r in finished),
            unfinished_exposed_checks=sum(r['block']==b and r['exposed'] and not r['completed'] for r in tables['checks']))
    by_condition={s['condition']:s for s in tables['summaries']}
    b,c=by_condition.get('B'),by_condition.get('C')
    paired=bool(b and c and b['procedure_error_denominator'] and c['procedure_error_denominator'])
    tables['participant_contrasts'].append(dict(comparison='C_minus_B',outcome='first_committed_continuation_error',
        metrics_version=config['metrics_version'],paired_observed=paired,
        difference=c['procedure_error_rate']-b['procedure_error_rate'] if paired else None,
        missing_pair_reason=None if paired else 'one_or_both_conditions_have_no_observed_applicable_outcome',
        b_numerator=b['procedure_error_numerator'] if b else 0,b_denominator=b['procedure_error_denominator'] if b else 0,
        c_numerator=c['procedure_error_numerator'] if c else 0,c_denominator=c['procedure_error_denominator'] if c else 0,
        complete_opportunities=bool(paired and b['procedure_error_denominator']==len(SCHEDULE) and c['procedure_error_denominator']==len(SCHEDULE)),
        b_unobserved=b['procedure_unobserved'] if b else None,c_unobserved=c['procedure_unobserved'] if c else None,
        b_missed_checkpoints=b['checkpoints_not_reached'] if b else len(SCHEDULE),c_missed_checkpoints=c['checkpoints_not_reached'] if c else len(SCHEDULE)))
    return tables
