// Route existing sessions to their original interface and stylesheet.
let ui:'legacy'|'v2'|'v3'|'current'='current';
if(location.pathname!=='/admin'&&!new URLSearchParams(location.search).has('join')){
 try{const r=await fetch('/api/session');if(r.ok){const s=await r.json();ui=s.config.metrics_version==='hmc-metrics-1'?'legacy':s.config.interface_version==='ergonomic-3'?'v3':s.config.interface_version?'current':'v2';}}catch{}
}
const sheet=document.querySelector<HTMLLinkElement>('link[rel=stylesheet]')!;
if(location.pathname==='/admin'){const {admin}=await import('./admin.js');void admin();}
else if(ui==='legacy'){sheet.href='/web/legacy-style.css';await import('./legacy-main.js');}
else if(ui==='v2'){sheet.href='/web/v2-style.css';await import('./v2-main.js');}
else if(ui==='v3'){sheet.href='/web/v3-style.css';await import('./v3-main.js');}
else await import('./main.js');
export {};
