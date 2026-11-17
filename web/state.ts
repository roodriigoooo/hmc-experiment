export const cats=['product','quantity','packaging','delivery'] as const;
export type Category=typeof cats[number];
export type State={phase:string;block:number;order:number;submitted:Category[];selected:Category|null;judgment:boolean|null;training:number;cue:Category|null;last:Category|null;practice:boolean;pause_from:string|null;practice_index:number;streak:number;practice_history:{category:Category;judgment:boolean}[];practice_selections:Category[];practice_result:any;available:boolean;secondary_seen:boolean;return_expected:Category|null};
export type Event={id:string;seq:number;segment:string;origin:number;mono:number;type:string;payload:Record<string,any>};
export type Assignment={conditions:string;task_sets:string;b_form:string;slot:number};
export const schedule:Record<number,number>={1:2,3:3,4:2,7:3,9:2,11:3};
export const expected=(s:State)=>cats.find(c=>!s.submitted.includes(c))??null;
export const condition=(s:State,a:Assignment|null)=>s.practice?(s.practice_index<3?'ABC'[s.practice_index]:'A'):a!.conditions[s.block];
export const checkpoint=(s:State)=>s.submitted.length===(s.practice?([1,2].includes(s.practice_index)?2:-1):schedule[s.order]);
export function answerKey(o:any){return {product:o.requested.product===o.packed.product,quantity:o.requested.quantity===o.packed.quantity,packaging:({fragile:'padded',chilled:'insulated',standard:'ordinary'} as Record<string,string>)[o.requested.handling]===o.packed.packaging,delivery:o.requested.delivery===o.packed.delivery};}
function reset(s:State){Object.assign(s,{submitted:[],selected:null,judgment:null,last:null,cue:null,available:false,return_expected:null,secondary_seen:false,practice_history:[],practice_selections:[]});}
export function reduce(old:State,t:string,p:Record<string,any>,a:Assignment|null,config:any={training_attempts:6,training_consecutive:2},fixtures:any=null):State{
 const s=structuredClone(old);
 if(t==='document'){if(['order','ack','secondary','resumed','returning','break','paused'].includes(s.phase)){s.pause_from=s.pause_from||s.phase;s.phase='paused';s.available=false;}return s;}
 if(t==='withdraw'){s.phase='withdrawn';return s;}
 if(t==='pause'){Object.assign(s,{pause_from:s.phase,phase:'paused',available:false,selected:null,judgment:null});return s;}
 if(t==='resume'){const previous=s.pause_from;Object.assign(s,{pause_from:null,available:false,selected:null,judgment:null});s.phase=['secondary','returning'].includes(previous!)?'returning':['order','resumed','ack'].includes(previous!)?'order':previous!;s.cue=s.phase==='returning'&&condition(s,a)==='C'?s.last:null;return s;}
 if(t==='consent')s.phase='device';
 if(t==='device')s.phase='instructions';
 if(t==='practice_start'||t==='practice_next'){
  if(t==='practice_next'){
   if(s.practice_index>=3&&s.streak>=config.training_consecutive){s.phase='ready';return s;}
   if(s.practice_index>=3&&s.training>=config.training_attempts){s.phase='incomplete_training';return s;}
   s.practice_index++;
  }
  reset(s);s.phase='order';s.practice=true;if(s.practice_index>=3)s.training++;
 }
 if(t==='block_start'){reset(s);Object.assign(s,{phase:'order',practice:false,order:0});}
 if(t==='task_ready')s.available=true;
 if(t==='select'){s.selected=p.category;s.judgment=null;s.cue=null;if(s.practice)s.practice_selections.push(p.category);}
 if(t==='judge')s.judgment=p.judgment;
 if(t==='submit'){if(s.practice)s.practice_history.push({category:s.selected!,judgment:s.judgment!});s.submitted.push(s.selected!);Object.assign(s,{last:s.selected,selected:null,judgment:null,phase:'ack',available:false});}
 if(t==='ack_end'){s.phase=checkpoint(s)&&condition(s,a)!=='A'?'secondary':'order';s.available=false;}
 if(t==='secondary_ready'){s.available=true;s.secondary_seen=true;}
 if(t==='return')Object.assign(s,{phase:'returning',available:false,selected:null,judgment:null,cue:condition(s,a)==='C'?s.last:null});
 if(t==='task_return_ready')Object.assign(s,{phase:'resumed',available:true,return_expected:expected(s)});
 if(t==='finish'){
  Object.assign(s,{cue:null,available:false,selected:null,judgment:null});
  if(s.practice){
   const key=answerKey(fixtures.P[s.practice_index]);const sequence=JSON.stringify(s.submitted)===JSON.stringify(cats)&&JSON.stringify(s.practice_selections)===JSON.stringify(cats);const correct=s.practice_history.length===4&&s.practice_history.every(x=>x.judgment===key[x.category]);
   s.practice_result={passed:sequence&&correct,sequence,correct,answer_key:key,history:s.practice_history};if(s.practice_index>=3)s.streak=sequence&&correct?s.streak+1:0;s.phase='practice_feedback';
  }else if(s.order===11)s.phase='questionnaire';else{reset(s);s.order++;s.phase='order';}
 }
 if(t==='questionnaire')s.phase=s.block===2?'complete':'break';
 if(t==='break_end'){s.block++;s.phase='block';}return s;
}
