/** A screen epoch changes only when availability changes, not on a selection. */
export class FreshInput {
 epoch=0; pointer:{epoch:number;target:EventTarget|null}|null=null;
 key:{epoch:number;target:EventTarget|null;key:string}|null=null;
 invalidate(){this.epoch++;this.pointer=null;this.key=null;}
 press(target:EventTarget|null){this.pointer={epoch:this.epoch,target};}
 keydown(target:EventTarget|null,key:string,repeat:boolean){if(!repeat&&['Enter',' '].includes(key))this.key={epoch:this.epoch,target,key};}
 accept(target:EventTarget|null,detail:number){
  const origin=detail===0?this.key:this.pointer;
  const ok=detail<=1&&origin?.epoch===this.epoch&&origin.target===target;
  if(detail!==0)this.pointer=null;else this.key=null;
  return !!ok;
 }
}
