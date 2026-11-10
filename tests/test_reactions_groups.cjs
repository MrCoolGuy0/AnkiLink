/* Actual DOM interactions for reactions, roles, membership and delayed replies. */
const {JSDOM}=require('jsdom'),fs=require('node:fs'),assert=require('node:assert/strict');
const dom=new JSDOM('<div id="link-app"></div><div id="modal-root"></div><div id="toast"></div>',{runScripts:'outside-only'}),w=dom.window,d=w.document,calls=[];
w.pycmd=raw=>calls.push(JSON.parse(raw.slice(10)));w.setTimeout=()=>1;w.clearTimeout=()=>{};
w.eval(fs.readFileSync(__dirname+'/../anki_link/web/app.js','utf8'));d.dispatchEvent(new w.Event('DOMContentLoaded'));
const q=s=>d.querySelector(s),all=s=>[...d.querySelectorAll(s)],receive=(event,data)=>w.ankiLink.receive(event,data),S=w.ankiLink.state;
const click=s=>{assert.ok(q(s),s);assert.equal(q(s).disabled,false,s);q(s).click();},last=action=>calls.filter(c=>c.action===action).at(-1);
const me={id:'me',name:'Me',username:'fixture_me'},admin={id:'admin',name:'Admin',username:'fixture_admin',admin:true},member={id:'member',name:'Member',username:'fixture_<script>alert(1)</script>'},friend={id:'friend',name:'A friend',username:'fixture_friend',status:'accepted'},pending={id:'pending',name:'Pending',status:'pending'};
const group={id:'group',kind:'group',title:'Group <b>safe</b>',owner:'me',membership_version:1,members:[me,admin,member],avatar:null,avatar_version:0,unread:0},direct={id:'direct',kind:'direct',title:'Friend',members:[me,friend],unread:0};
me.avatar={id:'me-avatar',mime:'image/png'};
const boot=features=>({user:me,friends:[friend,pending,{...member,status:'accepted'}],threads:[structuredClone(group),structuredClone(direct)],invites:[],features});
const features={message_reactions:true,group_administration:true};
receive('setup',{});receive('bootstrap',boot({}));click('[data-thread=group]');
const photo={id:'photo',mime:'image/png',name:'fixture.png'};
receive('blob',{id:'photo',src:'data:image/png;base64,IMAGE'});
receive('messages',{thread:'group',messages:[{id:10,thread:'group',sender:'member',name:member.name,kind:'image',attachment:photo,created:1,reactions:[]}]});
assert.equal(q('[data-react-message]'),null,'old servers have no reaction controls');click('[data-action=group-details]');assert.equal(q('[data-action=group-leave]'),null);click('[data-action=close-modal]');
receive('bootstrap',boot(features));assert.ok(q('[data-react-message="10"]'));
const article=q('[data-message-id="10"]'),image=q('.message-photo'),input=q('#message-input');input.value='Keep my draft';input.dispatchEvent(new w.Event('input',{bubbles:true}));
// The chooser is a viewport overlay: opening it never creates a message row.
const trigger=q('[data-react-message="10"]');
trigger.getBoundingClientRect=()=>({left:280,right:308,top:740,bottom:768,width:28,height:28});
w.innerWidth=300;w.innerHeight=780;
click('[data-react-message="10"]');
assert.equal(q('.reaction-picker').parentElement,d.body,'picker is portalled out of message flow');
assert.equal(q('.reaction-picker').style.position,'fixed');
assert.equal(trigger.getAttribute('aria-expanded'),'true');
assert.ok(Number.parseFloat(q('.reaction-picker').style.left)>=8,'picker stays inside left viewport edge');
click('[data-react-message="10"]');assert.equal(q('.reaction-picker'),null,'same button toggles closed');
click('[data-react-message="10"]');d.body.click();assert.equal(q('.reaction-picker'),null,'outside click closes');
click('[data-react-message="10"]');d.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Escape',bubbles:true}));assert.equal(q('.reaction-picker'),null);assert.equal(d.activeElement,trigger,'Escape restores trigger focus');
click('[data-react-message="10"]');q('.messages').dispatchEvent(new w.Event('scroll'));assert.equal(q('.reaction-picker'),null,'scroll closes floating chooser');
click('[data-react-message="10"]');assert.equal(all('[data-reaction-choice]').length,7);click('[data-reaction-choice="👍"]');let req=last('reaction');assert.equal(req.thread,'group');assert.equal(req.message,10);assert.equal(req.emoji,'👍');assert.ok(req._request);assert.equal(q('[data-react-message="10"]').disabled,false);assert.ok(q('[data-reaction-people="👍"]'),'reaction is visible before HTTP reply');
receive('operation',{request:req._request,phase:'done',event:'reaction_updated',data:{thread:'group',message:10,reactions:[{emoji:'👍',count:1,users:['me']}]}});
assert.equal(q('[data-reaction-people="👍"]').classList.contains('is-mine'),true);assert.equal(q('[data-message-id="10"]'),article);assert.equal(q('.message-photo'),image);assert.equal(q('#message-input'),input);assert.equal(input.value,'Keep my draft');
const beforeViewer=calls.filter(c=>c.action==='reaction').length;click('[data-reaction-people="👍"]');assert.match(q('.reaction-people').textContent,/Me/);assert.match(q('.reaction-people').textContent,/@fixture_me/);assert.ok(q('.reaction-person [data-avatar-user=me]'),'reactor profile picture has an initial fallback');assert.equal(q('.reaction-summary-count').textContent,'1 person');receive('blob',{id:'me-avatar',src:'data:image/png;base64,PROFILE'});assert.equal(q('.reaction-person [data-avatar-user=me] img').getAttribute('src'),'data:image/png;base64,PROFILE');assert.equal(calls.filter(c=>c.action==='reaction').length,beforeViewer,'viewing reactors never changes a reaction');assert.ok(q('[data-reaction-people="👍"]'));click('[data-action=close-modal]');click('[data-react-message="10"]');click('[data-reaction-choice="👍"]');req=last('reaction');assert.equal(req.emoji,'');receive('operation',{request:req._request,phase:'failed',message:'Network <script>failed</script>'});assert.equal(q('[data-react-message="10"]').disabled,false);assert.equal(q('#toast script'),null);
click('[data-react-message="10"]');click('[data-reaction-choice="❤️"]');req=last('reaction');assert.equal(req.emoji,'❤️','different emoji changes own reaction');
click('[data-thread=direct]');receive('operation',{request:req._request,phase:'done',event:'reaction_updated',data:{thread:'group',message:10,reactions:[{emoji:'❤️',count:1,users:['me']}]}});assert.equal(S.thread,'direct');assert.equal(S.drafts.group,'Keep my draft');
click('[data-thread=group]');const stable=q('[data-message-id="10"]'),stableImage=q('.message-photo');receive('status',{reactions:[{thread:'group',message:10,reactions:[{emoji:'😂',count:1,users:['member']}]}]});
assert.equal(q('[data-message-id="10"]'),stable);assert.equal(q('.message-photo'),stableImage);assert.equal(q('[data-reaction-people="😂"]').title,'@'+member.username);assert.equal(q('.reaction-host script'),null);assert.equal(q('[data-reaction-people="😂"]').classList.contains('is-mine'),false);
click('[data-reaction-people="😂"]');assert.ok(q('.reaction-people').textContent.includes('@'+member.username));assert.equal(q('.reaction-people script'),null);receive('reaction_updated',{thread:'group',message:10,reactions:[]});assert.match(q('.reaction-people').textContent,/No one/);click('[data-action=close-modal]');assert.equal(q('[data-reaction-people]'),null);assert.equal(q('[data-message-id="10"]'),stable);
receive('messages',{thread:'group',messages:[],reactions:[{thread:'group',message:10,reactions:[{emoji:'🎉',count:2,users:['me','member']}]}]});assert.equal(q('[data-reaction-people="🎉"] span').textContent,'2');assert.equal(q('[data-message-id="10"]'),stable,'HTTP catchup updates only reaction controls');
receive('reaction_updated',{thread:'group',message:10,reaction_version:10,reactions:[{emoji:'❤️',count:2,users:['me','member']}]});
receive('reaction_updated',{thread:'group',message:10,reaction_version:9,reactions:[]});assert.ok(q('[data-reaction-people="❤️"]'),'late ACK cannot overwrite newer reaction state');
receive('messages',{thread:'group',messages:[{...S.messages.group[0],reaction_version:9,reactions:[]}]});assert.ok(q('[data-reaction-people="❤️"]'),'late history cannot overwrite newer reaction state');
q('#message-input').value='Unsent';click('[data-action=send]');assert.ok(q('[data-outgoing-nonce]'));assert.equal(q('[data-outgoing-nonce] [data-react-message]'),null);
// System notices are plain text activity, including malicious-looking snapshot names.
receive('messages',{thread:'group',messages:[{id:11,thread:'group',sender:'me',name:'Me',kind:'system',text:'Me added <img src=x onerror=alert(1)> & Member',created:2,reactions:[{emoji:'👍',count:1,users:['me']}],invite:'spoof'}]});
const notice=q('[data-message-id="11"]');assert.ok(notice.classList.contains('message-system'));assert.equal(notice.textContent,'Me added <img src=x onerror=alert(1)> & Member');assert.equal(notice.querySelector('img,button,.avatar,.bubble,.message-meta,.delivery-status,.deck-symbol,.reaction-host'),null);
click('[data-react-message="10"]');click('[data-action=group-details]');assert.equal(q('.reaction-picker'),null,'modal navigation closes reaction chooser');click('[data-action=close-modal]');
click('[data-react-message="10"]');click('[data-thread=direct]');assert.equal(q('.reaction-picker'),null,'thread navigation closes reaction chooser');click('[data-thread=group]');
// Color changes are local, scoped and leave the existing chat nodes in place.
const themedMessage=q('[data-message-id="10"]');click('[data-action=conversation-options]');
assert.ok(q('.chat-color-options'));click('[data-chat-color="#6854dc"]');assert.equal(S.chatThemes.group,'#6854dc');assert.equal(last('chat_theme').color,'#6854dc');assert.ok(q('.workspace').style.getPropertyValue('--mine'));assert.equal(q('[data-message-id="10"]'),themedMessage);
q('#custom-chat-color').value='#ffffff';q('#custom-chat-color').dispatchEvent(new w.Event('change',{bubbles:true}));assert.equal(S.chatThemes.group,'#ffffff');assert.equal(q('.workspace').style.getPropertyValue('--accent'),'rgb(115,115,115)');
click('[data-chat-color="default"]');assert.equal(S.chatThemes.group,undefined);assert.equal(q('.workspace').style.getPropertyValue('--mine'),'');click('[data-action=close-modal]');
// Each appearance offers its own presets and keeps a saved hex color on switch.
const palettes = new Set();
for (const appearance of ['default','ankiretro','ankiretro-baby-blue','ankiretro-maroon','ankirise','ankimessage']) {
 receive('appearance',appearance);
 click('[data-action=conversation-options]');
 const swatches=all('[data-chat-color]:not([data-chat-color="default"])').map(b=>b.dataset.chatColor);
 assert.equal(swatches.length,5);
 palettes.add(swatches.join(','));
 assert.equal(q('[data-chat-color="default"]').getAttribute('aria-pressed'),'true');
 assert.equal(q('#custom-chat-color').value,swatches[0]);
 click('[data-action=close-modal]');
}
assert.equal(palettes.size,6,'each appearance has a distinct chat palette');
receive('appearance','ankiretro-baby-blue');
click('[data-action=conversation-options]');
const bluePreset=q('[data-chat-color]:not([data-chat-color="default"])').dataset.chatColor;
click('[data-chat-color="'+bluePreset+'"]');
const paletteModal=q('.modal'),customColor=q('#custom-chat-color');
receive('appearance','ankiretro-maroon');
assert.equal(q('.modal'),paletteModal);
assert.equal(q('#custom-chat-color'),customColor);
assert.equal(customColor.value,bluePreset);
assert.equal(S.chatThemes.group,bluePreset);
assert.equal(q('[data-chat-color="'+bluePreset+'"]'),null);
click('[data-chat-color="default"]');
assert.equal(q('[data-chat-color="default"]').getAttribute('aria-pressed'),'true');
assert.equal(q('#custom-chat-color').value,q('[data-chat-color]:not([data-chat-color="default"])').dataset.chatColor);
click('[data-action=close-modal]');
receive('appearance','default');
// Rapid clicks remain enabled and coalesce to the last desired choice.
const beforeReacts=calls.filter(c=>c.action==='reaction').length;
click('[data-react-message="10"]');click('[data-reaction-choice="👍"]');const slow=last('reaction');
click('[data-react-message="10"]');click('[data-reaction-choice="😮"]');assert.ok(q('[data-reaction-people="😮"]'));assert.equal(calls.filter(c=>c.action==='reaction').length,beforeReacts+1);
receive('operation',{request:slow._request,phase:'done',event:'reaction_updated',data:{thread:'group',message:10,reaction_version:11,reactions:[{emoji:'👍',count:1,users:['me']}]}});
const latest=last('reaction');assert.equal(latest.emoji,'😮');assert.ok(q('[data-reaction-people="😮"]'));
receive('operation',{request:latest._request,phase:'done',event:'reaction_updated',data:{thread:'group',message:10,reaction_version:12,reactions:[{emoji:'😮',count:1,users:['me']}]}});assert.ok(q('[data-reaction-people="😮"]'));assert.equal(Object.keys(S.reactionPending).length,0);
// Both people appear; losing group access also dismisses the names dialog.
receive('reaction_updated',{thread:'group',message:10,reaction_version:13,reactions:[{emoji:'😮',count:2,users:['me','member']}]});
click('[data-reaction-people="😮"]');assert.equal(all('.reaction-person').length,2);assert.equal(q('.reaction-summary-count').textContent,'2 people');assert.equal(all('.reaction-person .avatar').length,2);assert.match(q('.reaction-people').textContent,/Me/);assert.ok(q('.reaction-people').textContent.includes('@'+member.username));assert.equal(q('.reaction-people script'),null);click('[data-action=close-modal]');
// Owner controls exclude owner removal and include accepted friends only.
click('[data-action=group-details]');assert.match(q('.member-role').textContent,/Owner/);assert.equal(q('[data-action=group-remove][data-user=me]'),null);assert.equal(q('[data-action=group-admin]'),null,'actions are absent until menu opens');
assert.equal(q('[data-member-menu=me]'),null,'owner has no actions menu');
click('[data-member-menu=admin]');assert.equal(q('.member-menu').parentElement,d.body);assert.equal(q('.member-menu').getAttribute('role'),'menu');assert.ok(q('[data-action=group-admin][data-user=admin]'));assert.ok(q('[data-action=group-remove][data-user=admin]'));
const menuTrigger=q('[data-member-menu=admin]');
d.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Escape',bubbles:true}));assert.equal(q('.member-menu'),null);assert.equal(d.activeElement,menuTrigger);
click('[data-member-menu=admin]');d.body.click();assert.equal(q('.member-menu'),null);assert.equal(d.activeElement,menuTrigger);
click('[data-member-menu=admin]');click('[data-member-menu=admin]');assert.equal(q('.member-menu'),null,'member trigger toggles');
click('[data-member-menu=admin]');click('[data-member-menu=member]');assert.equal(q('[data-action=group-admin]').dataset.user,'member','only one member menu is open');
const profile=q('.group-profile'),photoProgress=q('#group-photo-progress');receive('bootstrap',boot(features));assert.equal(q('.group-profile'),profile);assert.equal(q('#group-photo-progress'),photoProgress);
click('[data-action=group-add]');assert.equal(all('[data-group-recipient]').length,1);assert.equal(q('[data-group-recipient]').value,'friend');click('[data-action=group-add-confirm]');assert.match(q('.modal-error').textContent,/Choose friends/);q('[data-group-recipient]').checked=true;click('[data-action=group-add-confirm]');req=last('group_add');assert.deepEqual(req.users,['friend']);assert.equal(q('[data-action=group-add-confirm]').disabled,true);
receive('operation',{request:req._request,phase:'done',event:'group_result',data:{thread:'group',owner:'me',membership_version:2,members:[me,admin,member,friend]}});assert.equal(all('.group-member').length,4);
click('[data-member-menu=member]');click('[data-action=group-admin][data-user=member]');req=last('group_admin');assert.equal(req.admin,true);receive('operation',{request:req._request,phase:'done',event:'group_result',data:{thread:'group',owner:'me',membership_version:3,members:[me,admin,{...member,admin:true},friend]}});click('[data-member-menu=member]');assert.equal(q('[data-action=group-admin][data-user=member]').textContent,'Remove admin');
click('[data-member-menu=admin]');click('[data-action=group-remove][data-user=admin]');assert.match(q('.modal').textContent,/lose access/);const removals=calls.filter(c=>c.action==='group_remove').length;click('[data-action=group-details]');assert.equal(calls.filter(c=>c.action==='group_remove').length,removals,'cancel never removes');click('[data-member-menu=admin]');click('[data-action=group-remove][data-user=admin]');click('[data-action=group-remove-confirm]');req=last('group_remove');assert.equal(req.user,'admin');
click('[data-action=close-modal]');click('[data-thread=direct]');click('[data-action=account]');const account=q('.modal');receive('operation',{request:req._request,phase:'done',event:'group_result',data:{thread:'group',owner:'me',membership_version:4,members:[me,{...member,admin:true},friend]}});assert.equal(q('.modal'),account,'late membership completion preserves new modal/navigation');assert.equal(S.thread,'direct');click('[data-action=close-modal]');click('[data-thread=group]');click('[data-action=group-details]');assert.equal(all('.group-member').length,3);
click('[data-action=group-leave]');assert.match(q('.modal').textContent,/randomly chosen/);click('[data-action=group-details]');
// Admins cannot appoint admins or remove admins/owner; ordinary members can only leave.
const adminBoot=boot(features);adminBoot.threads[0]={...group,owner:'admin',membership_version:5,members:[{...me,admin:true},admin,{...member,admin:true},friend]};receive('bootstrap',adminBoot);assert.equal(q('[data-action=group-admin]'),null);assert.equal(q('[data-action=group-remove][data-user=member]'),null);assert.equal(q('[data-action=group-remove][data-user=admin]'),null);assert.equal(q('[data-member-menu=member]'),null);assert.equal(q('[data-member-menu=admin]'),null);click('[data-member-menu=friend]');assert.ok(q('[data-action=group-remove][data-user=friend]'));assert.equal(q('[data-action=group-admin]'),null);assert.ok(q('[data-action=group-add]'));
const plainBoot=structuredClone(adminBoot);plainBoot.threads[0].membership_version=6;plainBoot.threads[0].members[0].admin=false;receive('bootstrap',plainBoot);assert.equal(q('[data-action=group-remove]'),null);assert.equal(q('[data-action=group-add]'),null);assert.ok(q('[data-action=group-leave]'));
// A status omission removes all local conversation state and ignores delayed frames.
click('[data-action=close-modal]');q('#message-input').value='Private draft';q('#message-input').dispatchEvent(new w.Event('input',{bubbles:true}));assert.ok(S.messages.group);assert.ok(S.images.photo);
receive('status',{group_memberships:[]});assert.equal(S.thread,null);assert.equal(S.messages.group,undefined);assert.equal(S.drafts.group,undefined);assert.equal(S.images.photo,undefined);assert.equal(Object.values(S.outbox).filter(m=>m.thread==='group').length,0);assert.equal(q('[data-thread=group]'),null);assert.equal(q('.message-photo'),null);
receive('messages',{thread:'group',messages:[{id:99,thread:'group',sender:'member',kind:'text',text:'obsolete',created:1}]});receive('blob',{id:'photo',src:'data:image/png;base64,LATE'});receive('reaction_updated',{thread:'group',message:10,reactions:[{emoji:'👍',count:1,users:['member']}]});assert.equal(S.messages.group,undefined);assert.equal(S.images.photo,undefined);
receive('bootstrap',plainBoot);assert.equal(q('[data-thread=group]'),null,'stale bootstrap cannot restore a removed group');plainBoot.threads[0].membership_version=7;receive('bootstrap',plainBoot);assert.equal(q('[data-thread=group]'),null,'legacy omission requires a fresh authoritative membership confirmation');receive('status',{group_memberships:[{thread:'group',membership_version:7}]});receive('bootstrap',plainBoot);assert.ok(q('[data-thread=group]'),'later explicit membership can restore access');click('[data-thread=group]');click('[data-action=group-details]');click('[data-action=group-leave]');assert.doesNotMatch(q('.modal').textContent,/randomly chosen/);click('[data-action=group-leave-confirm]');req=last('group_leave');receive('operation',{request:req._request,phase:'done',event:'group_result',data:{thread:'group',membership_version:8,removed:'me'}});assert.equal(S.thread,null);assert.equal(q('.modal'),null);assert.equal(q('[data-thread=group]'),null);
// Actual removal v3 must defeat an in-flight v2 snapshot even when local state was v1.
receive('signed_out');receive('bootstrap',boot(features));click('[data-thread=group]');
receive('messages',{thread:'group',messages:[{id:10,thread:'group',sender:'member',kind:'image',attachment:photo,created:1}]});receive('blob',{id:'photo',src:'data:image/png;base64,FIRST'});
receive('group_removed',{thread:'group',membership_version:3});const stale=boot(features);stale.threads[0].membership_version=2;receive('bootstrap',stale);assert.equal(q('[data-thread=group]'),null);stale.threads[0].membership_version=3;receive('bootstrap',stale);assert.equal(q('[data-thread=group]'),null);
receive('blob',{id:'photo',src:'data:image/png;base64,ABSENT'});assert.equal(S.images.photo,undefined);
const rejoin=boot(features);rejoin.threads[0].membership_version=4;rejoin.threads[0].avatar={id:'group-avatar',mime:'image/png'};receive('bootstrap',rejoin);click('[data-thread=group]');receive('messages',{thread:'group',messages:[{id:10,thread:'group',sender:'member',kind:'image',attachment:photo,created:1}]});assert.equal(last('blob')._thread,'group');receive('blob',{id:'photo',src:'data:image/png;base64,REJOIN'});assert.equal(q('.message-photo').getAttribute('src'),'data:image/png;base64,REJOIN');receive('blob',{id:'group-avatar',src:'data:image/png;base64,AVATAR'});assert.equal(S.images['group-avatar'],'data:image/png;base64,AVATAR');
click('[data-react-message="10"]');receive('signed_out');assert.equal(q('.reaction-picker'),null,'signout closes chooser');receive('bootstrap',rejoin);click('[data-thread=group]');
// An inbox preview is owned by its group, including while the download is pending.
const previewBoot=structuredClone(rejoin);previewBoot.invites=[{id:'group-invite',thread:'group',recipient:'me',sender:'member',sender_name:'Member',state:'pending',created:1,attachment:{id:'bundle'},summary:{title:'Shared deck',cards:1,notes:1,decks:1}}];receive('bootstrap',previewBoot);click('[data-tab=inbox]');click('[data-action=preview]');req=last('preview_invite');assert.equal(req.thread,'group');assert.equal(q('.modal').dataset.groupThread,'group');receive('group_removed',{thread:'group',membership_version:5});assert.equal(q('.modal'),null);assert.equal(q('[data-action=preview]'),null);receive('operation',{request:req._request,phase:'done',event:'invite_preview',data:{invitation:previewBoot.invites[0],manifest:{summary:{title:'Forbidden'}}}});assert.equal(q('.modal'),null);assert.equal(S.preview,undefined);
receive('signed_out');assert.equal(Object.keys(S.reactions).length,0);assert.equal(Object.keys(S.removedGroups).length,0);receive('signed_out');receive('bootstrap',boot(features));click('[data-tab=chats]');click('[data-thread=group]');receive('messages',{thread:'group',messages:[{id:90,thread:'group',sender:'me',kind:'text',text:'Viewer access',created:1,reactions:[{emoji:'👍',count:1,users:['member']}]}]});click('[data-reaction-people="👍"]');assert.ok(q('.reaction-people'));receive('group_removed',{thread:'group',membership_version:99});assert.equal(q('.reaction-people'),null,'losing access closes reactor list');
dom.window.close();
console.log('Reactions/group DOM passed: seven choices, toggle/change/remove, HTTP/live refresh, stable images/drafts, safe usernames, feature gates, role controls, friend selection, confirmation, request failures/navigation, revocation and rejoin.');
