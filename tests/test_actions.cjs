/* Deliberately withheld/misordered replies: pending feedback must not lock navigation. */
const {JSDOM}=require('jsdom'),fs=require('node:fs'),assert=require('node:assert/strict');
const dom=new JSDOM('<div id="link-app"></div><div id="modal-root"></div><div id="toast"></div>',{url:'https://test.invalid',runScripts:'outside-only'}),w=dom.window,d=w.document,calls=[];
w.setTimeout=()=>1;w.clearTimeout=()=>{};w.pycmd=raw=>calls.push(JSON.parse(raw.slice(10)));
w.eval(fs.readFileSync(__dirname+'/../anki_link/web/app.js','utf8'));d.dispatchEvent(new w.Event('DOMContentLoaded'));
const q=s=>d.querySelector(s),receive=(event,data)=>w.ankiLink.receive(event,data),S=w.ankiLink.state;
const me={id:'me',name:'Me',code:'TEST'},friend={id:'friend',name:'Friend',status:'accepted',incoming:false};
const boot={user:me,friends:[friend],invites:[],threads:[{id:'chat',title:'Friend',kind:'direct',members:[me,friend],unread:0}]};
const click=s=>{assert.ok(q(s),'missing '+s);q(s).click();},last=action=>calls.filter(x=>x.action===action).at(-1);
const finish=(call,event,data)=>receive('operation',{request:call._request,phase:'done',event,data});
receive('setup',{});receive('bootstrap',boot);click('[data-thread=chat]');
const retainedTab=q('[data-tab=chats]');retainedTab.focus();receive('bootstrap',boot);assert.equal(q('[data-tab=chats]'),retainedTab,'unchanged refresh preserves navigation nodes');assert.equal(d.activeElement,retainedTab,'unchanged refresh preserves keyboard focus');
for(let i=0;i<20;i++){
 receive('refresh_state',{loading:true});assert.equal(q('[data-tab=chats]').getAttribute('aria-busy'),'false','routine background checks must not animate the tab');
 receive('bootstrap',boot);receive('refresh_state',{loading:false});
}
assert.equal(q('[data-tab=chats]'),retainedTab,'silent checks preserve the actual tab node');assert.equal(d.activeElement,retainedTab);
click('[data-action=new-group]');q('#group-name').value='Study group';q('[data-recipient]').checked=true;click('[data-action=create-group]');
const group=last('group');assert.ok(group._request);assert.match(q('.operation-status').textContent,/Creating group/);assert.equal(q('[data-action=create-group]').disabled,true);assert.equal(d.body.classList.contains('busy'),false);assert.equal(q('[data-action=close-modal]').disabled,false);
receive('refresh_state',{loading:true});receive('refresh_state',{loading:false});assert.equal(q('[data-tab=chats]').getAttribute('aria-busy'),'true','routine check completion cannot clear a real pending group action');
click('[data-action=create-group]');assert.equal(calls.filter(x=>x.action==='group').length,1,'pending duplicate clicks are suppressed');
const spinner=q('.operation-status .profile-spinner');receive('bootstrap',boot);assert.equal(q('.operation-status .profile-spinner'),spinner,'refresh retains loading animation');
click('[data-action=close-modal]');click('[data-tab=friends]');click('[data-tab=inbox]');assert.equal(S.tab,'inbox');assert.equal(q('[data-tab=chats]').getAttribute('aria-busy'),'true');
finish(group,'social_result',{thread:'group'});assert.equal(S.tab,'inbox','late creation cannot drag the user out of Decks');assert.equal(q('[data-tab=chats]').getAttribute('aria-busy'),'false');
const newGroup={id:'group',title:'Study group',kind:'group',members:[me,friend],unread:0};receive('bootstrap',{...boot,threads:[newGroup,...boot.threads]});click('[data-tab=chats]');assert.ok(q('[data-thread=group]'));click('[data-thread=group]');assert.ok(q('#message-input'));
// An acknowledged group waits for its snapshot without becoming a dead, empty screen.
click('[data-action=new-group]');q('#group-name').value='Second';q('[data-recipient]').checked=true;click('[data-action=create-group]');finish(last('group'),'social_result',{thread:'second'});assert.match(q('.workspace').textContent,/Opening conversation/);click('[data-tab=friends]');assert.equal(S.tab,'friends');
// Adding a friend settles at its own ACK, not at an unrelated/old bootstrap.
click('[data-action=add-friend]');q('#friend-code').value='NEW';click('[data-action=friend-send]');const add=last('friend_request');receive('bootstrap',boot);assert.ok(q('#friend-code'));assert.match(q('.operation-status').textContent,/Sending request/);finish(add,'social_result',{ok:true});assert.equal(q('.modal'),null);assert.match(q('#toast').textContent,/Friend request sent/);
const incoming={id:'new',name:'New person',status:'pending',incoming:true};receive('bootstrap',{...boot,friends:[friend,incoming]});assert.match(q('.sidebar').textContent,/New person/);click('[data-friend-accept=new]');const accept=last('friend_decide');assert.equal(q('[data-friend-accept=new]').disabled,true);receive('bootstrap',{...boot,friends:[friend,incoming]});assert.equal(q('[data-friend-accept=new]').disabled,true,'replacement rows retain pending state');
receive('operation',{request:accept._request,phase:'failed',message:'Offline'});assert.equal(q('[data-friend-accept=new]').disabled,false);assert.match(q('#toast').textContent,/Offline/);
// Share dialog can be closed/reopened while catalog is pending; reuse the actual request.
click('[data-tab=chats]');click('[data-thread=chat]');click('[data-action=share]');const catalog=last('catalog');assert.match(q('.operation-status').textContent,/Loading your decks/);click('[data-action=close-modal]');click('[data-action=share]');assert.equal(last('catalog'),catalog);assert.match(q('.operation-status').textContent,/Loading your decks/);
finish(catalog,'catalog',[{id:'deck',name:'Science',filtered:false}]);assert.ok(q('#deck-tree'));q('[data-deck]').checked=true;q('[data-deck]').dispatchEvent(new w.Event('change',{bubbles:true}));q('[data-recipient]').checked=true;click('[data-action=share-send]');const share=last('share');assert.equal(q('[data-action=share-send]').disabled,true);assert.match(q('.operation-status').textContent,/Preparing decks/);receive('operation',{request:share._request,phase:'loading',message:'Uploading decks…'});assert.match(q('.operation-status').textContent,/Uploading decks/);
click('[data-action=close-modal]');click('[data-action=account]');const account=q('.modal');finish(share,'shared',{ok:true});assert.equal(q('.modal'),account,'late deck completion cannot close Account');assert.match(q('#toast').textContent,/Deck invitations sent/);
// An obsolete completion cannot clear a different operation or close a new modal.
click('[data-action=close-modal]');click('[data-tab=friends]');click('[data-action=add-friend]');q('#friend-code').value='BAD';click('[data-action=friend-send]');const failed=last('friend_request');receive('operation',{request:failed._request,phase:'failed',message:'Invalid <script>code</script>'});assert.equal(q('.modal-error script'),null);assert.match(q('.modal-error').textContent,/Invalid <script>/);assert.equal(q('[data-action=friend-send]').disabled,false);click('[data-action=friend-send]');const retry=last('friend_request');assert.notEqual(retry._request,failed._request);finish(failed,'social_result',{ok:true});assert.equal(q('[data-action=friend-send]').disabled,true);assert.ok(q('.modal'));
receive('signed_out');assert.equal(q('.modal'),null);assert.equal(Object.keys(S.operations).length,0);finish(retry,'social_result',{ok:true});assert.ok(q('#auth-form'));
dom.window.close();console.log('Action DOM checks passed: immediate progress, duplicate protection, navigation during delayed replies, stale snapshots, current-group hydration, fresh friends, reopening, per-request errors and sign-out.');
