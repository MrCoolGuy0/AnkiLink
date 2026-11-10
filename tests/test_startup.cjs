/* Cold-head/delayed-bridge regression. Full controller/WebEngine flow is separate. */
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(__dirname+'/../anki_link/web/app.js','utf8');
const handlers={},timers=[],sent=[],app={innerHTML:'opening'},modals={innerHTML:''};
let nodesReady=false;
const doc={readyState:'loading',querySelector:s=>nodesReady?(s==='#link-app'?app:s==='#modal-root'?modals:null):null,querySelectorAll:()=>[],addEventListener:(n,fn)=>(handlers[n]??=[]).push(fn),body:{classList:{toggle(){},remove(){}}}};
const window={addEventListener(){}};const context={window,document:doc,console,setTimeout:fn=>(timers.push(fn),timers.length),clearTimeout(){},setInterval:()=>1,Date,Math,crypto:globalThis.crypto};
vm.runInNewContext(source,context);
assert.equal(window.ankiLink,undefined,'head execution waits for body');
nodesReady=true;doc.readyState='complete';for(const fn of handlers.DOMContentLoaded||[])fn();
assert.ok(window.ankiLink);assert.equal(sent.length,0,'bridge can be late');
context.pycmd=m=>sent.push(JSON.parse(m.slice(10)));
timers.shift()();assert.equal(sent.at(-1).action,'ready');
window.ankiLink.receive('setup',{url:'https://example.com',dark:false,remember_available:false});
assert.match(app.innerHTML,/auth-form/);assert.match(app.innerHTML,/https:\/\/example.com/);
const before=sent.length;for(let i=0;i<4&&timers.length;i++)timers.shift()();assert.equal(sent.length,before,'ready responses stop retries');
console.log('AnkiLink startup passed: head-before-body, delayed bridge, sign-in rendering, retries stop after connection.');

{
 const timers=[],handlers={},app={innerHTML:'opening'},modals={innerHTML:''},calls=[];
 const doc={readyState:'complete',querySelector:s=>s==='#link-app'?app:s==='#modal-root'?modals:null,querySelectorAll:()=>[],addEventListener:(n,fn)=>(handlers[n]??=[]).push(fn),body:{classList:{toggle(){},remove(){}}}};
 const window={addEventListener(){}};const c={window,document:doc,console,setTimeout:fn=>(timers.push(fn),1),clearTimeout(){},setInterval:()=>1,Date,Math,crypto:globalThis.crypto};
 vm.runInNewContext(source,c);
 for(let i=0;i<65&&timers.length;i++)timers.shift()();
 assert.match(app.innerHTML,/could not connect/);assert.match(app.innerHTML,/startup-retry/);
 c.pycmd=m=>calls.push(JSON.parse(m.slice(10)));
 for(const fn of handlers.click||[])fn({target:{closest:s=>s==='button'?{dataset:{action:'startup-retry'}}:null}});
 assert.equal(calls.at(-1).action,'ready');window.ankiLink.receive('setup',{url:'https://example.com'});assert.match(app.innerHTML,/auth-form/);
 console.log('AnkiLink timeout/retry passed: failed bridge shows recovery UI and Retry reconnects.');
}
