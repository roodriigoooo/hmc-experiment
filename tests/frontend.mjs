import test from 'node:test';
import assert from 'node:assert/strict';
import {reduce,expected,cats} from '../dist/web/legacy-state.js';
const initial=()=>({phase:'consent',block:0,order:0,submitted:[],selected:null,training:0,cue:null,last:null,practice:true,pause_from:null});
const assignment={conditions:'ABC',task_sets:'ZYX',b_form:'U',slot:0};
test('all three conditions: only C shows actual last submission after interruption',()=>{
 for(let block=0;block<3;block++){
  let s={...initial(),phase:'ready',practice:false,block,order:1};
  s=reduce(s,'block_start',{},assignment);s.order=1;
  for(const c of ['delivery','product']){s=reduce(s,'select',{category:c},assignment);s=reduce(s,'submit',{judgment:false},assignment);s=reduce(s,'ack_end',{},assignment);}
  assert.equal(s.selected,null);assert.equal(s.phase,block===0?'order':'secondary');
  if(block){s=reduce(s,'return',{},assignment);assert.equal(s.cue,block===2?'product':null);assert.equal(expected(s),'quantity');s=reduce(s,'select',{category:'delivery'},assignment);assert.equal(s.cue,null);}
 }
});
test('complete flow mirrors server through all blocks, questionnaires, breaks',()=>{
 let s=initial();for(const [t,p] of [['consent',{}],['device',{}],['practice_start',{}]])s=reduce(s,t,p,assignment);
 for(const c of cats){s=reduce(s,'select',{category:c},assignment);s=reduce(s,'submit',{},assignment);s=reduce(s,'ack_end',{},assignment);if(s.phase==='secondary')s=reduce(s,'return',{},assignment);}
 s=reduce(s,'finish',{},assignment);s=reduce(s,'comprehension',{sequence:cats.join(','),return:'automatic'},assignment);assert.equal(s.phase,'ready');
 for(let block=0;block<3;block++){
  s=reduce(s,'block_start',{},assignment);
  for(let order=0;order<12;order++){for(const c of cats){s=reduce(s,'select',{category:c},assignment);s=reduce(s,'submit',{},assignment);s=reduce(s,'ack_end',{},assignment);if(s.phase==='secondary')s=reduce(s,'return',{},assignment);}s=reduce(s,'finish',{},assignment);}
  assert.equal(s.phase,'questionnaire');s=reduce(s,'questionnaire',{},assignment);if(block<2){assert.equal(s.phase,'break');s=reduce(s,'break_end',{},assignment);}
 }
 assert.equal(s.phase,'complete');
});
test('repeat, omission, wrong sequence and reload preserve submitted history',()=>{
 let s={...initial(),phase:'order',practice:false};
 for(let i=0;i<2;i++){s=reduce(s,'select',{category:'quantity'},assignment);s=reduce(s,'submit',{},assignment);s=reduce(s,'ack_end',{},assignment);}
 assert.equal(expected(s),'product');assert.equal(s.submitted.length,2);s=reduce(s,'document',{},assignment);assert.equal(s.phase,'paused');s=reduce(s,'resume',{},assignment);assert.equal(s.submitted.length,2);s=reduce(s,'finish',{},assignment);assert.equal(s.order,1);assert.equal(s.submitted.length,0);
});

import {FreshInput} from '../dist/web/input.js';
import {reduce as revisedReduce, cats as revisedCats} from '../dist/web/state.js';
test('fresh gestures: return invalidates secondary press/held key; duplicates rejected',()=>{
 const g=new FreshInput(),button={};g.press(button);g.invalidate();assert.equal(g.accept(button,1),false);
 g.keydown(button,' ',false);g.invalidate();g.keydown(button,' ',true);assert.equal(g.accept(button,0),false);
 g.press(button);assert.equal(g.accept(button,1),true);assert.equal(g.accept(button,1),false);
 g.press(button);assert.equal(g.accept(button,2),false);
 g.keydown(button,'Enter',false);assert.equal(g.accept(button,0),true);
 g.press({});assert.equal(g.accept(button,1),false);
});
test('revised B/C return states differ only in cue; passive events preserve card',()=>{
 const base={...initial(),phase:'secondary',practice:false,submitted:['delivery','delivery'],last:'delivery',judgment:null,available:true,practice_index:0,practice_selections:[],practice_history:[],practice_result:null,streak:0,secondary_seen:true,return_expected:null};
 const b=revisedReduce(base,'return',{}, {...assignment,conditions:'BAC'}), c=revisedReduce(base,'return',{}, {...assignment,conditions:'CAB'});
 assert.deepEqual({...b,cue:null},{...c,cue:null});assert.equal(b.cue,null);assert.equal(c.cue,'delivery');
 let s=revisedReduce(c,'task_return_ready',{expected:'product',cue_appears:true},{...assignment,conditions:'CAB'});
 for(const t of ['environment','input_problem']){s=revisedReduce(s,t,{},assignment);assert.equal(s.cue,'delivery');}
 s=revisedReduce(s,'select',{category:'quantity'},assignment);assert.equal(s.cue,null);assert.equal(s.return_expected,'product');
 s=revisedReduce(s,'judge',{judgment:false},assignment);s=revisedReduce(s,'submit',{judgment:false},assignment);assert.equal(s.selected,null);assert.equal(s.judgment,null);
});

import {reduce as procedureReduce, expected as procedureExpected, cats as procedureCats} from '../dist/web/v4-state.js';
test('eight-check return preserves actual history and frozen expectation, including Finish removal',()=>{
 const base={...initial(),phase:'secondary',practice:false,submitted:['seal','batch','seal'],last:'seal',judgment:null,available:true,practice_index:0,practice_selections:[],practice_history:[],practice_result:null,streak:0,secondary_seen:true,return_expected:null,categories:[...procedureCats],schedule:{0:3,1:6,2:2,3:5,4:7,5:4}};
 const b=procedureReduce(base,'return',{}, {...assignment,conditions:'BAC'}),c=procedureReduce(base,'return',{}, {...assignment,conditions:'CAB'});
 assert.deepEqual({...b,cue:null},{...c,cue:null});assert.equal(c.cue,'seal');assert.equal(procedureExpected(c),'product');
 let s=procedureReduce(c,'task_return_ready',{}, {...assignment,conditions:'CAB'});
 s=procedureReduce(s,'environment',{},assignment);assert.equal(s.cue,'seal');assert.equal(s.return_expected,'product');
 const selected=procedureReduce(s,'select',{category:'dispatch'},assignment);assert.equal(selected.cue,null);assert.equal(selected.return_expected,'product');
 const finished=procedureReduce(s,'finish',{},assignment);assert.equal(finished.cue,null);assert.equal(finished.order,1);
});
