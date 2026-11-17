export const cats=['product','quantity','packaging','delivery'] as const;
export type Category=typeof cats[number];
export type State={phase:string;block:number;order:number;submitted:Category[];selected:Category|null;training:number;cue:Category|null;last:Category|null;practice:boolean;pause_from:string|null};
export type Event={id:string;seq:number;segment:string;origin:number;mono:number;type:string;payload:Record<string,any>};
export type Assignment={conditions:string;task_sets:string;b_form:string;slot:number};
export const schedule:Record<number,number>={1:2,3:3,4:2,7:3,9:2,11:3};
export const expected=(s:State)=>cats.find(c=>!s.submitted.includes(c))??null;
export function reduce(old:State,t:string,p:Record<string,any>,a:Assignment|null):State{
 const s=structuredClone(old),condition=s.practice?'C':a?.conditions[s.block];
 if(t==='document'){if(['order','ack','secondary','resumed','break','paused'].includes(s.phase)){s.pause_from=s.pause_from||s.phase;s.phase='paused';}return s;}
 if(t==='withdraw'){s.phase='withdrawn';return s;}
 if(t==='pause'){s.pause_from=s.phase;s.phase='paused';return s;}
 if(t==='resume'){s.phase=s.pause_from!;s.pause_from=null;if(['secondary','ack'].includes(s.phase)){s.phase='resumed';s.cue=condition==='C'?s.last:null;}return s;}
 if(t==='consent')s.phase='device';
 if(t==='device')s.phase='instructions';
 if(t==='practice_start'){Object.assign(s,{phase:'order',practice:true,submitted:[],selected:null,last:null,cue:null});s.training++;}
 if(t==='select'){s.selected=p.category;s.cue=null;}
 if(t==='submit'){s.submitted.push(s.selected!);s.last=s.selected;s.selected=null;s.phase='ack';}
 if(t==='ack_end')s.phase=s.submitted.length===(s.practice?2:schedule[s.order])&&condition!=='A'?'secondary':'order';
 if(t==='return'){s.phase='resumed';s.cue=condition==='C'?s.last:null;}
 if(t==='finish'){s.cue=null;if(s.practice)s.phase='comprehension';else if(s.order===11)s.phase='questionnaire';else Object.assign(s,{phase:'order',order:s.order+1,submitted:[],selected:null,last:null});}
 if(t==='comprehension'){const pass=p.sequence==='product,quantity,packaging,delivery'&&p.return==='automatic'&&cats.every(c=>s.submitted.includes(c));s.phase=pass?'ready':s.training<2?'instructions':'incomplete_training';}
 if(t==='block_start')Object.assign(s,{phase:'order',practice:false,order:0,submitted:[],selected:null,cue:null,last:null});
 if(t==='questionnaire')s.phase=s.block===2?'complete':'break';
 if(t==='break_end'){s.block++;s.phase='block';}return s;
}
