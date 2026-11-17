export const $=document.querySelector<HTMLDivElement>('#app')!;
export const esc=(v:unknown)=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]!));
export async function api(path:string,data?:unknown){const r=await fetch('/api'+path,{method:data===undefined?'GET':'POST',headers:{'Content-Type':'application/json'},body:data===undefined?undefined:JSON.stringify(data)});if(!r.ok)throw new Error((await r.json()).error);return r.json();}
export function on(id:string,fn:()=>void){document.getElementById(id)?.addEventListener('click',fn);}
export function error(e:unknown){const el=document.getElementById('message');if(el)el.textContent=String(e).replace(/^Error: /,'');else alert(String(e));}
export const journey=['Setup','Training','Block 1','Block 2','Block 3','Done'];
type ShellOptions={stage?:number|null;task?:boolean;link?:boolean};
/** The participant brand is not a link: leaving the page mid-task would force a reload pause. */
export function shell(body:string,tag='',{stage=null,task=false,link=true}:ShellOptions={}){
 const brand=`<span class="mark" aria-hidden="true">▦</span> Digital checks`;
 const steps=stage===null?'':`<ol class="journey" aria-label="Study progress">${journey.map((s,i)=>`<li class="${i<stage?'done':i===stage?'current':''}"${i===stage?' aria-current="step"':''}><span class="dot" aria-hidden="true">${i<stage?'✓':''}</span>${s}</li>`).join('')}</ol>`;
 $.innerHTML=`<header>${link?`<a href="/" class="brand">${brand}</a>`:`<span class="brand">${brand}</span>`}${steps}${tag?`<span class="mode">${esc(tag)}</span>`:''}</header><main>${body}</main>${task?'':'<footer>Human–Machine Collaboration · Research study</footer>'}`;
}
