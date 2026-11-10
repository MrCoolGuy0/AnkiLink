/* Group destination capture, independent invitations, menus and delayed UI. */
const {JSDOM}=require('jsdom'),fs=require('node:fs'),assert=require('node:assert/strict');
const people=[{id:'a',name:'Jay'},{id:'b',name:'Mia'},{id:'c',name:'Third member'}];
const group={id:'group',kind:'group',title:'Study group <safe>',members:people,unread:0};
const invitations=['b','c'].map((recipient,i)=>({id:'invite-'+recipient,sender:'a',recipient,thread:'group',nonce:'shared-once',sender_name:'Jay',state:'pending',created:10,summary:{title:'Science',cards:60,filtered_decks:1}}));
function fixture(uid){
 const dom=new JSDOM('<div id="link-app"></div><div id="modal-root"></div><div id="toast"></div>',{runScripts:'outside-only'}),w=dom.window,d=w.document,calls=[];
 w.pycmd=raw=>calls.push(JSON.parse(raw.slice(10)));w.setTimeout=()=>1;
 w.eval(fs.readFileSync(__dirname+'/../anki_link/web/app.js','utf8'));d.dispatchEvent(new w.Event('DOMContentLoaded'));
 const q=s=>d.querySelector(s),click=s=>{assert.ok(q(s),s);q(s).click();},recv=(e,v)=>w.ankiLink.receive(e,v),S=w.ankiLink.state;
 const me=people.find(p=>p.id===uid),other=people.find(p=>p.id!==uid);
 const boot={user:{...me,code:'TEST'},friends:[{...other,status:'accepted'}],threads:[group,{id:'direct',kind:'direct',title:other.name,members:[me,other],unread:0}],invites:[],features:{group_deck_shares:true}};
 recv('setup',{muted:[]});recv('bootstrap',boot);click('[data-thread=group]');return {dom,w,d,calls,q,click,recv,S,boot};
}
{
 const e=fixture('a'),{q,click,recv,calls,S,w}=e;
 q('#message-input').value='My group draft';q('#message-input').dispatchEvent(new w.Event('input',{bubbles:true}));
 click('[data-action=share]');const catalog=calls.at(-1);assert.equal(catalog.action,'catalog');
 // A late catalog cannot reopen after the user changes conversation.
 click('[data-action=close-modal]');click('[data-thread=direct]');recv('operation',{request:catalog._request,phase:'done',event:'catalog',data:[]});assert.equal(q('.modal'),null);
 click('[data-thread=group]');click('[data-action=share]');const request=calls.at(-1);
 recv('operation',{request:request._request,phase:'done',event:'catalog',data:[{id:'1',name:'Science'},{id:'2',name:'Science::Lesson 1'}]});
 assert.equal(q('[data-share-group]').dataset.shareGroup,'group');assert.equal(q('[data-recipient]'),null);assert.ok(!q('.modal-body script'));
 q('[data-deck="1"]').checked=true;q('[data-deck="1"]').dispatchEvent(new w.Event('change',{bubbles:true}));
 click('[data-action=share-send]');const share=calls.at(-1);assert.equal(share.action,'share');assert.equal(share.thread,'group');assert.equal(share.recipients,undefined);assert.deepEqual([...share.decks],['1']);
 click('[data-action=share-send]');assert.equal(calls.at(-1),share,'double send does not start another operation');
 recv('operation',{request:share._request,phase:'done',event:'shared',data:{thread:'group',invitations:['invite-b','invite-c']}});
 assert.equal(S.thread,'group');assert.equal(q('#message-input').value,'My group draft');
 // The direct/global flow remains an explicit friend selection.
 click('[data-thread=direct]');click('[data-action=share]');recv('operation',{request:calls.at(-1)._request,phase:'done',event:'catalog',data:[]});assert.ok(q('[data-recipient]'));assert.equal(q('[data-share-group]'),null);click('[data-action=close-modal]');
 e.dom.window.close();
}
for(const uid of ['a','b','c']){
 const e=fixture(uid),{q,recv,S}=e;
 const own=uid==='a'?invitations:invitations.filter(i=>i.recipient===uid);
 recv('messages',{thread:'group',messages:[{id:10,thread:'group',nonce:'shared-once',sender:'a',name:'Jay',kind:'deck',text:'Science',invite:uid==='c'?'invite-c':'invite-b',created:10}],invites:own});
 assert.equal(e.d.querySelectorAll('.deck-bubble').length,1);
 if(uid==='a'){assert.equal(q('[data-action=preview]'),null);assert.match(q('.deck-bubble .status').textContent,/0 accepted.*2 pending/);}
 else{assert.equal(q('[data-action=preview]').dataset.id,'invite-'+uid);}
 recv('bootstrap',{...e.boot,invites:[]});
 if(uid!=='a')assert.equal(q('[data-action=preview]').dataset.id,'invite-'+uid,'old/history invite survives the limited bootstrap list');
 recv('bootstrap',{...e.boot,invites:own.map(i=>({...i,state:i.recipient==='b'?'accepted':'rejected'}))});
 if(uid==='a')assert.match(q('.deck-bubble .status').textContent,/1 accepted.*0 pending.*1 declined/);
 else{assert.equal(q('[data-action=preview]'),null);assert.equal(q('.deck-bubble .status').textContent,uid==='b'?'accepted':'rejected');}
 recv('messages',{thread:'group',messages:[],invites:own});
 if(uid!=='a')assert.equal(q('[data-action=preview]'),null,'late pending data cannot undo a final decision');
 recv('signed_out');assert.equal(Object.keys(S.deckInvites).length,0);e.dom.window.close();
}
{
 const e=fixture('b'),{q,click,recv,d,w,calls}=e;const draft=q('#message-input');draft.value='Keep my text';draft.focus();
 for(let n=0;n<30;n++){
  click('[data-action=conversation-options]');const modal=q('.modal'),check=q('#chat-notifications');assert.equal(d.activeElement,modal);
  recv('bootstrap',{...e.boot,threads:e.boot.threads.map(t=>({...t,unread:n%2}))});recv('status',{people:[],receipts:[],typing:[]});
  assert.equal(q('.modal'),modal);assert.equal(q('#chat-notifications'),check);assert.equal(check.dataset.threadId,'group');
  draft.focus();assert.ok(modal.contains(d.activeElement),'background composer cannot retain dialog focus');
  if(n%2){d.activeElement.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Escape',bubbles:true}));}else click('[data-action=close-modal].btn');
  assert.equal(q('.modal'),null);assert.equal(draft.value,'Keep my text');
 }
 click('[data-action=conversation-options]');q('#chat-notifications').checked=false;q('#chat-notifications').dispatchEvent(new w.Event('change',{bubbles:true}));assert.equal(calls.at(-1).action,'mute_thread');assert.equal(calls.at(-1).id,'group');recv('notification_settings',{muted:['group']});assert.equal(q('#chat-notifications').checked,false);
 assert.ok(!calls.some(c=>c.action==='message'));e.dom.window.close();
}
console.log('Group share UI passed: explicit group target, no DM expansion, independent invitation IDs/states, history, retry scope, stable notification modal/focus, drafts and direct-share compatibility.');
