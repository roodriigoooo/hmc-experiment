import {FreshInput} from './input.js';
import {cats,expected,reduce,schedule,condition,checkpoint,answerKey,type State,type Event,type Assignment,type Category} from './state.js';
import {esc,api,on,shell,error} from './ui.js';
const labels:Record<Category,string>={product:'Product code',quantity:'Quantity',packaging:'Packaging',delivery:'Delivery code'};
/** Row content: requested field label, packed field label, value readers, value style. */
const rows:Record<Category,[string,string,(o:any)=>unknown,(o:any)=>unknown,'code'|'word']>={
 product:['Product code','Product code',o=>o.requested.product,o=>o.packed.product,'code'],
 quantity:['Quantity','Quantity',o=>o.requested.quantity,o=>o.packed.quantity,'code'],
 packaging:['Handling','Packaging',o=>o.requested.handling,o=>o.packed.packaging,'word'],
 delivery:['Delivery code','Shipping label',o=>o.requested.delivery,o=>o.packed.delivery,'code']};
const rules=[['Fragile','Padded'],['Chilled','Insulated'],['Standard','Ordinary']];
const example={requested:{product:'PR-8200',quantity:4,handling:'fragile',delivery:'DL-8400'},packed:{product:'PR-8200',quantity:5,packaging:'padded',delivery:'DL-8401'}};
const taskPhases=['order','ack','resumed','returning'];
let state:State,assignment:Assignment|null=null,snapshot:any,queue:Event[]=[],seq=0,key='',segment=crypto.randomUUID(),tab=crypto.randomUUID(),saving=false,saved=0,leaseOk=false,locked=false;
let ratingDraft:Record<string,number>={},lastRenderAction='initial',onboardStep=0;
let timer:number|undefined,secondaryStart=0,item=-1,responded=new Set<number>(),breakDeadline=0,storageFailed=false;
const now=()=>performance.now();
const fresh=new FreshInput();let inputMethod='mouse',renderEpoch=0;
const passiveEvents=new Set(['secondary_response','secondary_item','environment','input_problem','questionnaire_item','task_ready','task_return_ready','secondary_ready']);
function persist(){localStorage.setItem(key,JSON.stringify({queue,seq,state,assignment,breakDeadline,ratingDraft}));}
function emit(type:string,payload:Record<string,any>={}){
 if(storageFailed)return;
 const e:Event={id:crypto.randomUUID(),seq:seq+1,segment,origin:performance.timeOrigin,mono:now(),type,payload};
 const next=reduce(state,type,payload,assignment,snapshot.config,snapshot.fixtures);const old=state;
 queue.push(e);seq++;state=next;
 try{persist();}catch{queue.pop();seq--;state=old;storageFailed=true;shell('<h1>Work paused</h1><p>This browser could not safely store an event. Keep this tab open and contact the researcher.</p>','',{link:false});return;}
 if(!passiveEvents.has(type))render();
 void flush();return e;
}
function saveStatus(){const el=document.getElementById('save-state');if(!el)return;el.textContent=queue.length?'Saving…':'All responses saved';el.classList.toggle('pending',queue.length>0);}
async function flush(){if(saving||!queue.length||!leaseOk)return;saving=true;try{await api('/session/lease',{tab});const batch=queue.slice(0,400);const r=await api('/session/events',{tab,events:batch});saved=r.last_seq;queue=queue.filter(e=>e.seq>saved);persist();if(state.phase==='complete'||state.phase==='withdrawn')render();else saveStatus();}catch(e){const el=document.getElementById('save-state');if(el){el.textContent='Waiting to save · keep this tab open';el.classList.add('pending');}const msg=document.getElementById('message');if(msg)msg.textContent=String(e);if(String(e).includes('tab')||String(e).includes('lease'))leaseOk=false;}finally{saving=false;}}
const button=(id:string,text:string,cls='')=>`<button id="${id}" class="${cls}">${text}</button>`;
const check=(ok:boolean)=>`<span class="mark-${ok?'ok':'no'}" aria-hidden="true">${ok?'✓':'✗'}</span>`;
const bookmark='<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4.5L5 21V4a1 1 0 0 1 1-1z" fill="currentColor"/></svg>';
/** Card wording is fixed by the protocol; the category uses the same label as its button. */
const cueCard=(c:Category)=>`<div class="cue-card"><span class="cue-icon">${bookmark}</span><span>Last submitted check: <b>${labels[c]}</b>.</span></div>`;
function stage(){
 const p=state.phase;if(['consent','device','instructions'].includes(p))return 0;if(p==='complete')return 5;if(['withdrawn','incomplete_training'].includes(p))return null;
 if(['ready','block'].includes(p))return 2+state.block;return state.practice?1:2+state.block;
}
type Sheet={interactive:boolean;selected?:Category|null;step?:number;coach?:string;disabled?:boolean;results?:Record<Category,boolean>};
function sheet(o:any,{interactive,selected=null,step=0,coach='',disabled=false,results}:Sheet){
 const control=(c:Category,i:number)=>{const inner=`<span class="num">${i+1}</span><span>${labels[c]}</span>`;
  return interactive?`<button id="category-${c}" class="cat${coach==='category-'+c?' coach':''}" aria-pressed="${selected===c}"${disabled?' disabled':''}>${inner}</button>`:`<span class="cat btn${selected===c?' is-pressed':''}">${inner}</span>`;};
 const cell=(field:string,value:unknown,kind:string)=>`<td><span class="field">${field}</span><span class="value ${kind}">${esc(value)}</span></td>`;
 return `<table class="compare"><thead><tr><th scope="col" class="step-head${step===1?' active':''}"><span class="step-label"><span class="badge">1</span>Select a check</span></th><th scope="col">Requested order</th><th scope="col">Packed order / shipping</th>${results?'<th scope="col">Judgment</th>':''}</tr></thead><tbody>${cats.map((c,i)=>{const [rf,pf,rv,pv,kind]=rows[c];
  return `<tr class="${selected===c?'is-selected':''}"><th scope="row">${control(c,i)}</th>${cell(rf,rv(o),kind)}${cell(pf,pv(o),kind)}${results?`<td class="result">${check(results[c])}${results[c]?'Matches':'Does not match'}</td>`:''}</tr>`;}).join('')}</tbody></table>
 <div class="rules" role="group" aria-label="Handling rules"><h2>Handling rules<span>for Packaging</span></h2><table><tr><th scope="row">Handling</th>${rules.map(r=>`<td>${r[0]}</td>`).join('')}</tr><tr><th scope="row">Required packaging</th>${rules.map(r=>`<td>${r[1]}</td>`).join('')}</tr></table></div>`;
}
type Panel={mock?:boolean;selected:Category|null;judgment:boolean|null;step:number;coach?:string;ack?:boolean;finishDisabled?:boolean};
function panel({mock=false,selected,judgment,step,coach='',ack=false,finishDisabled=false}:Panel){
 const b=(id:string,text:string,cls:string,pressed?:boolean,disabled=false)=>mock?`<span class="btn ${cls}${pressed?' is-pressed':''}">${text}</span>`:`<button id="${id}" class="${cls}${coach===id?' coach':''}"${pressed===undefined?'':` aria-pressed="${pressed}"`}${disabled?' disabled':''}>${text}</button>`;
 const noJudge=!selected,noSubmit=!selected||judgment===null;
 return `<section class="panel" aria-label="Record a check"><div class="step${step===2?' active':''}"><h2><span class="badge">2</span>Choose a judgment</h2><p class="selection">${selected?`Checking: <b>${labels[selected]}</b>`:'Select a check on the left first.'}</p><div class="judgments">${b('match','<span class="icon" aria-hidden="true">✓</span>Matches','judge secondary',judgment===true,noJudge)}${b('mismatch','<span class="icon" aria-hidden="true">✗</span>Does not match','judge secondary',judgment===false,noJudge)}</div></div>
 <div class="step${step===3?' active':''}"><h2><span class="badge">3</span>Submit the check</h2>${b('submit','Submit check','primary big',undefined,noSubmit)}<p class="ack" role="status">${ack?'<span aria-hidden="true">✓</span> Response recorded.':''}</p></div>
 <div class="finish-zone">${b('finish','Finish order <span aria-hidden="true">→</span>','secondary',undefined,finishDisabled)}<p>Moves to the next order. You cannot return to this one.</p></div></section>`;
}
const demoIntro=['Ordinary order. Follow the highlighted control at each step.','A number task will interrupt you after the second check. No card appears when you return.','A number task will interrupt you after the second check. When you return, a card names your last submitted check.'];
function orderScreen(p:string){
 const practice=state.practice,demo=practice&&state.practice_index<3;
 const o=snapshot.fixtures[practice?'P':assignment!.task_sets[state.block]][practice?state.practice_index:state.order];
 const e=expected(state),step=!state.selected?1:state.judgment===null?2:3;
 let coach='';
 if(demo)coach=!e?'finish':state.selected!==e?'category-'+e:state.judgment===null?(answerKey(o)[e]?'match':'mismatch'):'submit';
 const finishDisabled=!state.available||(demo&&!cats.every(c=>state.submitted.includes(c)));
 const title=demo?`Demonstration ${state.practice_index+1} of 3`:practice?`Practice order ${state.training}`:`Order ${state.order+1} of 12`;
 const pips=demo?[0,1,2].map(i=>`<li class="${i<state.practice_index?'done':i===state.practice_index?'current':''}"></li>`).join(''):practice?'':Array.from({length:12},(_,i)=>`<li class="${i<state.order?'done':i===state.order?'current':''}"></li>`).join('');
 const meta=demo?'':practice?`<p class="streak">Correct in a row <span class="pips small">${Array.from({length:snapshot.config.training_consecutive},(_,i)=>`<i class="${i<state.streak?'done':''}"></i>`).join('')}</span> ${state.streak} of ${snapshot.config.training_consecutive} needed · attempt ${state.training} of ${snapshot.config.training_attempts}</p>`:`<p class="block-label">Block ${state.block+1} of 3</p>`;
 const aside=demo?`<div class="coach-note" role="note"><span class="coach-tag">Guide</span><div><b>${demoIntro[state.practice_index]}</b><span>${e?`Next: ${labels[e]} → ${answerKey(o)[e]?'Matches':'Does not match'} → Submit check.`:'All four categories have submissions. You may now Finish order.'}</span></div></div>`:`<p class="sequence-hint">Work top to bottom: Product code → Quantity → Packaging → Delivery code</p>`;
 return `<div class="task-top"><div class="task-title"><h1>${title}</h1>${pips?`<ol class="pips" aria-hidden="true">${pips}</ol>`:''}${meta}</div>${aside}</div>
 <div class="workspace${p==='ack'?' is-busy':''}"><section class="sheet" aria-label="Order records"><div class="cue-slot" aria-live="polite">${state.cue?cueCard(state.cue):''}</div>${sheet(o,{interactive:true,selected:state.selected,step,coach,disabled:!state.available})}</section>${panel({selected:state.selected,judgment:state.judgment,step,coach,ack:p==='ack',finishDisabled})}</div>`;
}
const onboarding=[
 ()=>`<h2 class="slide-title">Your task: audit orders</h2><p class="lead">Each order shows what a customer <b>requested</b> and what was <b>packed</b> for shipping. Decide whether each detail matches.</p><div class="mock">${sheet(example,{interactive:false})}</div>`,
 ()=>`<h2 class="slide-title">Four checks, top to bottom</h2><p class="lead">${esc(snapshot.config.instructions)}</p><ol class="explain"><li><b>Product code.</b> Compare the requested and packed identifiers.</li><li><b>Quantity.</b> Compare the requested and packed quantities.</li><li><b>Packaging.</b> Look up the handling in the rule table, then compare it with the packed packaging.</li><li><b>Delivery code.</b> Compare the requested code and shipping label.</li></ol><div class="mock"><p class="mock-label">Worked example</p>${sheet(example,{interactive:false,results:answerKey(example)})}</div>`,
 ()=>`<h2 class="slide-title">Record each check in three steps</h2><div class="split steps-split"><div><div class="three-steps"><div><span class="badge">1</span><b>Select a check</b><span>Click its button at the left of the row.</span></div><div><span class="badge">2</span><b>Choose a judgment</b><span>Matches or Does not match.</span></div><div><span class="badge">3</span><b>Submit check</b><span>A short “Response recorded.” confirms it.</span></div></div><p>To revise a check, select the category again and submit a new judgment. When you are done with the order, press <b>Finish order</b>. You cannot return to a finished order.</p></div><div class="mock mock-panel">${panel({mock:true,selected:'quantity',judgment:false,step:3})}</div></div>`,
 ()=>`<h2 class="slide-title">Short interruptions</h2><div class="split"><div><p class="lead">Sometimes a quick number task replaces the order. Click the <b>larger number</b>. Items change automatically, and the order returns automatically.</p><div class="mock numbers mini" aria-hidden="true"><span class="btn">31</span><span class="btn">35</span></div></div><div><p class="lead">When you return, a card may state the last check you submitted. It names the category only. It does not say whether your judgment was right.</p><div class="mock">${cueCard('quantity')}</div></div></div>`,
 ()=>`<h2 class="slide-title">What happens next</h2><ol class="path"><li><b>Three guided demonstrations</b><span>Ordinary work, a number task without a card, and a number task with a card. A guide highlights each step.</span></li><li><b>Practice</b><span>Complete ${snapshot.config.training_consecutive} practice orders in a row with the taught sequence, all four submissions and correct judgments, within ${snapshot.config.training_attempts} attempts. Practice explains your results.</span></li><li><b>Three blocks of 12 orders</b><span>A few short questions after each block, and a 60-second break between blocks. The main blocks only confirm that each response was recorded.</span></li></ol>`];
function feedbackScreen(){
 const r=state.practice_result,config=snapshot.config,demo=state.practice_index<3;
 const done=!demo&&state.streak>=config.training_consecutive,last=!demo&&!done&&state.training>=config.training_attempts;
 const next=demo?(state.practice_index<2?`Continue to demonstration ${state.practice_index+2}`:'Start practice'):done?'Continue to the main study':last?'Continue':'Next practice order';
 const rowsHtml=cats.map(c=>{const subs=r.history.filter((h:any)=>h.category===c);const ok=subs.length>0&&subs.every((h:any)=>h.judgment===r.answer_key[c]);
  return `<tr><th scope="row">${labels[c]}</th><td>${subs.map((h:any)=>h.judgment?'Matches':'Does not match').join(', ')||'<i>No submission</i>'}</td><td>${r.answer_key[c]?'Matches':'Does not match'}</td><td class="result">${check(ok)}</td></tr>`;}).join('');
 const progress=demo?`<p class="progress-line">Demonstrations: <span class="pips">${[0,1,2].map(i=>`<i class="${i<=state.practice_index?'done':''}"></i>`).join('')}</span></p>`:`<p class="progress-line">Correct in a row: <span class="pips">${Array.from({length:config.training_consecutive},(_,i)=>`<i class="${i<state.streak?'done':''}"></i>`).join('')}</span> ${state.streak} of ${config.training_consecutive} needed</p><p class="progress-line">Attempts used: ${state.training} of ${config.training_attempts}</p>`;
 return `<div class="eyebrow">${demo?`Demonstration ${state.practice_index+1} of 3`:`Practice order ${state.training}`}</div><h1>${demo?'Demonstration complete':'Practice feedback'}</h1>
 <div class="feedback"><div><div class="verdict ${r.passed?'ok':'no'}">${check(r.passed)}<div><b>${r.passed?'All four checks were submitted correctly in the taught order.':'Not quite. Review the explanation before continuing.'}</b><span class="sub"><span>${check(r.sequence)}Taught order followed</span><span>${check(r.correct)}Judgments correct</span></span></div></div>
 <table class="scorecard"><thead><tr><th>Check</th><th>Your submissions</th><th>Correct judgment</th><th><span class="visually-hidden">Result</span></th></tr></thead><tbody>${rowsHtml}</tbody></table>
 <p class="hint">Use Product code → Quantity → Packaging → Delivery code. Select each category, choose a judgment, then Submit check. Finish after all four submissions. Packaging: fragile → padded, chilled → insulated, standard → ordinary. Other judgments compare the two values directly.</p></div>
 <aside class="next-card">${progress}${button('practice-next',next,'primary big')}</aside></div>`;
}
function questionnaireScreen(){
 const scale=(q:any)=>`<div class="scale" role="radiogroup" aria-label="${esc(q.title)}">${Array.from({length:21},(_,i)=>i*5).map(v=>`<button type="button" role="radio" class="tick${v===50?' mid':''}" data-key="${q.key}" data-value="${v}" aria-checked="${ratingDraft[q.key]===v}" aria-label="${v} of 100"></button>`).join('')}</div><div class="scale-ends"><span>${esc(q.low)}</span><span>${esc(q.high)}</span></div>`;
 const item=(q:any)=>`<li class="scale-item${ratingDraft[q.key]!==undefined?' answered':''}" id="item-${q.key}"><h2>${esc(q.title)}</h2><p>${esc(q.text)}</p>${scale(q)}</li>`;
 const tlx=snapshot.questions.filter((q:any)=>q.aggregate),extra=snapshot.questions.filter((q:any)=>!q.aggregate);
 return `<div class="eyebrow">Block ${state.block+1} of 3 complete</div><h1>Your experience</h1><p class="lead">${esc(snapshot.questionnaire.instruction)}</p><form id="ratings"><ol class="scales">${tlx.map(item).join('')}</ol>${extra.length?`<h2 class="divider">One more question</h2><ol class="scales">${extra.map(item).join('')}</ol>`:''}<div class="form-foot"><span id="answered" role="status"></span><button type="submit" id="save-ratings" class="primary big">Save ratings and continue</button></div></form>`;
}
function updateRatings(){
 const total=snapshot.questions.length,n=snapshot.questions.filter((q:any)=>ratingDraft[q.key]!==undefined).length;
 const a=document.getElementById('answered');if(a)a.textContent=`${n} of ${total} answered`;
 const s=document.getElementById('save-ratings') as HTMLButtonElement|null;if(s)s.disabled=n<total;
}
function screen(p:string){
 const config=snapshot.config;
 if(p==='consent')return `<div class="narrow"><div class="eyebrow">Welcome</div><h1>A study of digital checks</h1><p class="lead">You’ll complete fictional order checks using different interface configurations. Brief secondary tasks and progress reminders may occur.</p><ul class="facts"><li><b>About 25–30 minutes</b><span>The actual duration is being checked in the pilot.</span></li><li><b>Mouse or trackpad</b><span>On a desktop or laptop computer.</span></li><li><b>Voluntary</b><span>You may stop at any time.</span></li></ul><div class="card"><h2>Before you begin</h2><p>${esc(config.study_information||'Demo study information. Live participation is not enabled for this draft protocol.')}</p><p>${esc(config.consent)}</p><p>Researcher contact: ${esc(config.contact||'Not configured · demo only')}</p></div><label class="check big-check"><input type="checkbox" id="agree"><span>I have read the information, meet the researcher’s eligibility requirements, and freely agree to take part.</span></label>${button('consent','Agree and continue','primary big')}</div>`;
 if(p==='device')return `<div class="narrow"><div class="eyebrow">Setup</div><h1>Settle in</h1><p class="lead">Three quick checks before training.</p><ul class="checklist"><li id="viewport-item"><span class="status-dot" aria-hidden="true"></span><div><b>Window at least ${config.min_width} × ${config.min_height}</b><span id="viewport-now"></span></div></li><li><label><input type="checkbox" id="tick-notifications"><div><b>Personal notifications silenced</b><span>Phone and computer alerts are off or muted.</span></div></label></li><li><label><input type="checkbox" id="tick-pointer"><div><b>Using a mouse or trackpad</b><span>Click with it throughout the study, rather than the keyboard.</span></div></label></li></ul><p class="note">Supported setup: current desktop Chromium, English. Keep the window visible and at a stable size.</p>${button('device','My setup is ready','primary big')}</div>`;
 if(p==='instructions'){const last=onboardStep===onboarding.length-1;return `<div class="onboard"><div class="onboard-head"><div class="eyebrow">How it works · ${onboardStep+1} of ${onboarding.length}</div><ol class="dots" aria-hidden="true">${onboarding.map((_,i)=>`<li class="${i<=onboardStep?'done':''}"></li>`).join('')}</ol></div><div class="slide onboard-main">${onboarding[onboardStep]()}</div><div class="onboard-nav">${onboardStep?button('onboard-back','← Back','secondary'):'<span></span>'}${last?button('practice','Start demonstration 1','primary big'):button('onboard-next','Next →','primary big')}</div></div>`;}
 if(taskPhases.includes(p))return orderScreen(p);
 if(p==='secondary')return `<div class="secondary-task"><div class="eyebrow">Secondary task</div><h1>Choose the larger number</h1><p>The order checks will return automatically.</p><div id="numbers" class="numbers"></div><p id="secondary-status" class="status" role="status"></p></div>`;
 if(p==='practice_feedback')return feedbackScreen();
 if(['ready','block'].includes(p))return `<div class="narrow center-block">${p==='ready'?'<p class="badge-line">✓ Training complete</p>':''}<div class="eyebrow">Ready</div><h1>Block ${state.block+1} of 3</h1><p class="lead">12 orders. Work accurately and steadily.</p><div class="recap"><span><i class="badge">1</i>Select a check</span><span><i class="badge">2</i>Matches / Does not match</span><span><i class="badge">3</i>Submit check</span><span>Then <b>Finish order</b></span></div><p>The handling rules and checking sequence remain available throughout the task.</p>${button('begin',`Begin block ${state.block+1}`,'primary big')}</div>`;
 if(p==='questionnaire')return questionnaireScreen();
 if(p==='break')return `<div class="narrow center-block"><div class="eyebrow">Break</div><h1>A moment to rest</h1><p class="lead">Please remain at your computer. The next block will be available after this 60-second break.</p><div class="ring" role="timer" aria-live="off"><svg viewBox="0 0 120 120" aria-hidden="true"><circle cx="60" cy="60" r="52" class="track"/><circle cx="60" cy="60" r="52" class="fill" id="break-ring"/></svg><span><b id="break-count"></b>seconds</span></div><p class="hint">Look away from the screen and relax your hands. Next: Block ${state.block+2} of 3.</p></div>`;
 if(p==='paused')return `<div class="narrow"><div class="eyebrow">Paused</div><h1>Work paused</h1><p class="lead">Please return to a full-size, visible study window.</p><label for="pause-reason">Reason for this pause</label><select id="pause-reason"><option value="technical">Technical problem</option><option value="unscheduled">Unscheduled break</option><option value="external">External interruption</option><option value="assistance">Researcher assistance</option><option value="input">Input problem</option></select><p>Your submitted work is preserved. The pause will be recorded. If a secondary task was disrupted, it will not be replayed.</p>${button('resume','Resume','primary big')}</div>`;
 if(p==='complete')return `<div class="narrow"><div class="eyebrow">${queue.length?'Saving':'Complete'}</div><h1>${queue.length?'Saving your responses…':'Thank you for taking part'}</h1><p class="lead">${queue.length?'Please keep this tab open until saving is confirmed.':'All required events have been acknowledged by the server. You may close this tab.'}</p>${queue.length?'':'<ul class="done-list"><li>✓ Training</li><li>✓ Block 1</li><li>✓ Block 2</li><li>✓ Block 3</li></ul>'}<div class="card"><h2>About the study</h2><p>This study examines how brief interruptions relate to checking time, accuracy, and workload, and whether a last-submitted-check cue changes recovery during interrupted work. We do not yet know the results.</p><p>Completion identifier: <b class="code">${esc(snapshot.id)}</b></p><p>Contact: ${esc(config.contact||'Demo session')}</p></div></div>`;
 if(p==='withdrawn')return `<div class="narrow"><h1>Participation stopped</h1><p class="lead">${queue.length?'Saving your withdrawal. Please keep this tab open.':'Your withdrawal is saved.'}</p><p>Previously saved records are retained with withdrawal marked and excluded from default analysis tables.</p><p>Identifier: <b class="code">${esc(snapshot.id)}</b></p></div>`;
 if(p==='incomplete_training')return '<div class="narrow"><h1>Training has ended</h1><p class="lead">Please contact the researcher. No main-study allocation has been assigned.</p></div>';
 return '';
}
function utility(p:string){
 const pause=['order','resumed','ack','secondary','returning','break'].includes(p),withdraw=!['complete','withdrawn'].includes(p);
 return `<div class="utility"><span id="save-state" class="save${queue.length?' pending':''}">${queue.length?'Saving…':'All responses saved'}</span><span class="utility-actions">${pause?'<button id="pause" class="text-button">Pause / report a problem</button>':''}${withdraw?'<button id="withdraw" class="text-button">Withdraw from study</button><span id="withdraw-confirm" class="confirm" hidden>Stop taking part? <button id="withdraw-yes" class="danger">Yes, withdraw</button><button id="withdraw-no" class="secondary">Keep going</button></span>':''}</span></div><p id="message" role="status"></p>`;
}
function render(){
 clearTimeout(timer);const epoch=++renderEpoch;const p=state.phase;const config=snapshot.config;const focusId=(document.activeElement as HTMLElement)?.id;
 if(!state.available)fresh.invalidate();
 const tag=snapshot.mode==='main'?'':`${snapshot.mode.toUpperCase()}${snapshot.synthetic?' · SYNTHETIC':''}`;
 const task=taskPhases.includes(p);
 shell(screen(p)+utility(p),tag,{stage:stage(),task,link:false});document.body.classList.toggle('task-view',task);document.body.classList.toggle('secondary-view',p==='secondary');
 if(['select','judge'].includes(lastRenderAction)&&focusId)document.getElementById(focusId)?.focus({preventScroll:true});
 else if(['returning','order'].includes(p)&&!state.available){const heading=document.querySelector<HTMLElement>('h1');heading?.setAttribute('tabindex','-1');heading?.focus({preventScroll:true});}
 const agree=document.getElementById('agree') as HTMLInputElement|null,consent=document.getElementById('consent') as HTMLButtonElement|null;
 if(agree&&consent){consent.disabled=!agree.checked;agree.onchange=()=>{consent.disabled=!agree.checked;};}
 on('consent',()=>{if((document.getElementById('agree') as HTMLInputElement).checked)emit('consent',{agree:true});});
 if(p==='device'){updateDevice();['tick-notifications','tick-pointer'].forEach(id=>document.getElementById(id)!.addEventListener('change',updateDevice));}
 on('device',()=>{if(validViewport())emit('device',{width:innerWidth,height:innerHeight,input:'mouse'});else error(`Please enlarge the window to at least ${config.min_width} × ${config.min_height}.`);});
 on('onboard-next',()=>{onboardStep=Math.min(onboarding.length-1,onboardStep+1);render();});
 on('onboard-back',()=>{onboardStep=Math.max(0,onboardStep-1);render();});
 on('practice',()=>emit('practice_start'));
 on('practice-next',()=>emit('practice_next'));
 cats.forEach(c=>on('category-'+c,()=>{if(state.available){lastRenderAction='select';emit('select',{category:c,expected:expected(state),cue_removed:state.cue!==null,input:inputMethod});}}));
 for(const [id,judgment] of [['match',true],['mismatch',false]] as const){const b=document.getElementById(id) as HTMLButtonElement|null;if(b){b.disabled=!state.selected||!state.available;b.setAttribute('aria-pressed',String(state.judgment===judgment));b.onclick=()=>{lastRenderAction='judge';emit('judge',{judgment,input:inputMethod});};}}
 const submit=document.getElementById('submit') as HTMLButtonElement|null;
 if(submit){submit.disabled=!state.selected||state.judgment===null||!state.available;submit.onclick=()=>{lastRenderAction='submit';emit('submit',{category:state.selected,judgment:state.judgment,expected:expected(state),input:inputMethod});};}
 const finish=document.getElementById('finish') as HTMLButtonElement|null;
 if(finish)finish.disabled=!state.available||(state.practice&&state.practice_index<3&&!cats.every(c=>state.submitted.includes(c)));
 on('finish',()=>{lastRenderAction='finish';emit('finish',{expected:expected(state),cue_removed:state.cue!==null,input:inputMethod});});
 on('begin',()=>{(document.getElementById('begin') as HTMLButtonElement).disabled=true;void(async()=>{await flush();if(queue.length)throw Error('Please reconnect so training can be saved before allocation.');if(!assignment){assignment=await api('/session/allocate',{});persist();}emit('block_start');})().catch(e=>{error(e);const b=document.getElementById('begin') as HTMLButtonElement|null;if(b)b.disabled=false;});});
 if(p==='questionnaire'){updateRatings();document.querySelectorAll<HTMLButtonElement>('.tick').forEach(t=>t.addEventListener('click',()=>{const k=t.dataset.key!,v=Number(t.dataset.value);ratingDraft[k]=v;emit('questionnaire_item',{key:k,value:v});document.querySelectorAll<HTMLButtonElement>(`.tick[data-key="${k}"]`).forEach(x=>x.setAttribute('aria-checked',String(x===t)));document.getElementById('item-'+k)?.classList.add('answered');updateRatings();}));}
 document.getElementById('ratings')?.addEventListener('submit',e=>{e.preventDefault();if(snapshot.questions.some((q:any)=>ratingDraft[q.key]===undefined))return;breakDeadline=Date.now()+config.break_ms;const responses=Object.fromEntries(snapshot.questions.map((q:any)=>[q.key,ratingDraft[q.key]]));ratingDraft={};emit('questionnaire',responses);});
 on('resume',()=>{if(validViewport()&&!document.hidden){emit('environment',{reason:(document.getElementById('pause-reason') as HTMLSelectElement).value});emit('resume',{reason:'participant_ready'});}else error('Please restore the study window.');});
 on('pause',()=>emit('pause',{reason:'unscheduled'}));
 on('withdraw',()=>{document.getElementById('withdraw')!.hidden=true;document.getElementById('withdraw-confirm')!.hidden=false;});
 on('withdraw-no',()=>{document.getElementById('withdraw')!.hidden=false;document.getElementById('withdraw-confirm')!.hidden=true;});
 on('withdraw-yes',()=>emit('withdraw'));
 if(p==='ack')timer=window.setTimeout(()=>requestAnimationFrame(()=>{if(epoch!==renderEpoch||state.phase!=='ack')return;const hit=checkpoint(state);const f=secondaryForm();emit('ack_end',{checkpoint:hit,form:f,episode:episode(),acknowledgement_ms:config.acknowledgement_ms});}),config.acknowledgement_ms);
 if(p==='secondary'){item=-1;responded.clear();frameReady(epoch,()=>{const onset=emit('secondary_ready');if(onset){secondaryStart=onset.mono;secondaryTick();}});}
 if((p==='order'||p==='returning')&&!state.available)frameReady(epoch,()=>{enableTaskControls();emit(p==='returning'?'task_return_ready':'task_ready',p==='returning'?{expected:expected(state),cue_appears:condition(state,assignment)==='C'}:{kind:lastRenderAction});});
 if(p==='break')breakTick();
}
function updateDevice(){
 const ok=validViewport(),item=document.getElementById('viewport-item'),label=document.getElementById('viewport-now'),btn=document.getElementById('device') as HTMLButtonElement|null;if(!item||!label||!btn)return;
 item.classList.toggle('ok',ok);item.classList.toggle('bad',!ok);label.textContent=`Your window: ${innerWidth} × ${innerHeight}${ok?'':' · please enlarge it'}`;
 btn.disabled=!ok||!['tick-notifications','tick-pointer'].every(id=>(document.getElementById(id) as HTMLInputElement).checked);
}
function frameReady(epoch:number,callback:()=>void){requestAnimationFrame(()=>requestAnimationFrame(()=>{if(epoch===renderEpoch&&!document.hidden)callback();}));}
function enableTaskControls(){
 cats.forEach(c=>{const b=document.getElementById('category-'+c) as HTMLButtonElement|null;if(b)b.disabled=false;});
 const f=document.getElementById('finish') as HTMLButtonElement|null;if(f)f.disabled=state.practice&&state.practice_index<3&&!cats.every(c=>state.submitted.includes(c));
 fresh.invalidate();
}
function validViewport(){return innerWidth>=snapshot.config.min_width&&innerHeight>=snapshot.config.min_height;}
function secondaryForm(){return state.practice?'U':assignment!.conditions[state.block]==='B'?assignment!.b_form:assignment!.b_form==='U'?'V':'U';}
function episode(){return state.practice?0:Object.keys(schedule).map(Number).indexOf(state.order);}
function secondaryTick(){if(state.phase!=='secondary')return;const elapsed=now()-secondaryStart;const next=Math.floor(elapsed/snapshot.config.item_ms);
 if(next>=5){emit('return');return;}
 if(next!==item){fresh.invalidate();item=next;const pairs=snapshot.secondary[secondaryForm()][episode()];const box=document.getElementById('numbers')!;box.innerHTML=pairs[item].map((n:number,i:number)=>`<button id="number-${i}" class="number">${n}</button>`).join('');document.getElementById('secondary-status')!.textContent='';emit('secondary_item',{item,pair:pairs[item],elapsed_ms:elapsed});[0,1].forEach(choice=>on('number-'+choice,()=>{if(responded.has(item)||now()-secondaryStart>=snapshot.config.interruption_ms)return;responded.add(item);emit('secondary_response',{item,choice,elapsed_ms:now()-secondaryStart,input:inputMethod});document.getElementById('number-'+choice)?.classList.add('chosen');document.getElementById('secondary-status')!.textContent='Response recorded';}));}
 timer=window.setTimeout(secondaryTick,Math.max(1,Math.min(50,(item+1)*snapshot.config.item_ms-elapsed)));
}
function breakTick(){if(state.phase!=='break')return;const remaining=Math.max(0,breakDeadline-Date.now());const count=document.getElementById('break-count'),ring=document.getElementById('break-ring');if(count)count.textContent=String(Math.ceil(remaining/1000));if(ring)ring.style.strokeDashoffset=String(326.7*(1-remaining/snapshot.config.break_ms));if(!remaining){emit('break_end');return;}timer=window.setTimeout(breakTick,250);}
async function start(){snapshot=await api('/session');key='hmc-events-'+snapshot.id;await api('/session/lease',{tab});leaseOk=true;state=snapshot.state;assignment=snapshot.assignment;seq=snapshot.last_seq;saved=seq;
 const stored=JSON.parse(localStorage.getItem(key)||'null');if(stored){queue=stored.queue.filter((e:Event)=>e.seq>seq);for(const e of queue){state=reduce(state,e.type,e.payload,assignment||stored.assignment,snapshot.config,snapshot.fixtures);seq=e.seq;}assignment=assignment||stored.assignment;breakDeadline=stored.breakDeadline||0;}
 ratingDraft=stored?.ratingDraft||{};emit('document',{reason:'document_open',width:innerWidth,height:innerHeight,dpr:devicePixelRatio});
 setInterval(()=>{void api('/session/lease',{tab}).then(()=>{leaseOk=true;void flush();}).catch(()=>{leaseOk=false;});},5000);
 const pause=(reason:string)=>{if(['order','resumed','ack','secondary','returning','break'].includes(state.phase))emit('pause',{reason});};
 const environment=(reason:string)=>{emit('environment',{reason,width:innerWidth,height:innerHeight,dpr:devicePixelRatio,hidden:document.hidden,supported:validViewport()});pause(reason);};
 addEventListener('blur',()=>environment('blur'));document.addEventListener('visibilitychange',()=>{if(document.hidden)environment('hidden');else emit('environment',{reason:'visible',hidden:false});});addEventListener('resize',()=>{environment('viewport');if(state.phase==='device')updateDevice();});
 document.addEventListener('keydown',e=>{if(e.repeat&&['Enter',' '].includes(e.key)){e.preventDefault();return;}fresh.keydown(e.target,e.key,e.repeat);},true);
 document.addEventListener('pointerdown',e=>fresh.press(e.target),true);
 document.addEventListener('click',e=>{
  if(!['order','resumed','ack','secondary','returning'].includes(state.phase))return;
  const target=(e.target as HTMLElement).closest('button');if(!target)return;
  if(!fresh.accept(e.target,e.detail)){e.stopImmediatePropagation();e.preventDefault();emit('input_problem',{reason:'transition_or_duplicate_activation_blocked',input:e.detail===0?'keyboard':'mouse'});return;}
  inputMethod=e.detail===0?'keyboard':'mouse';if(inputMethod==='keyboard')emit('input_problem',{reason:'keyboard_used_in_mouse_protocol',input:inputMethod});
 },true);
}
async function acquire(){if(!navigator.locks)throw Error('This browser does not support the required single-tab lock. Use current desktop Chromium.');await navigator.locks.request('hmc-participant',{ifAvailable:true},async lock=>{if(!lock){shell('<div class="narrow"><h1>Study already open</h1><p class="lead">Continue in the other tab, or close it and reload this page.</p></div>','',{link:false});return;}locked=true;await start();await new Promise(()=>{});});}
async function participant(){try{if(new URLSearchParams(location.search).has('join'))throw Error('New session');await api('/session');void acquire().catch(error);}catch{shell(`<div class="narrow join"><div class="eyebrow">Welcome</div><h1>Digital checks study</h1><p class="lead">Enter the session code provided by your researcher.</p><form id="join"><label for="code">Session code</label><input id="code" name="code" class="code-input" autocomplete="off" spellcheck="false" required><button class="primary big">Continue</button></form><p id="message" role="status"></p><a class="research-link" href="/admin">Researcher sign in</a></div>`,'',{link:false});document.getElementById('code')!.focus();document.getElementById('join')!.onsubmit=e=>{e.preventDefault();void api('/join',{code:(document.getElementById('code') as HTMLInputElement).value.trim()}).then(()=>location.replace('/')).catch(error);};}}
void participant();
