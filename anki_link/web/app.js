(()=>{'use strict';
function initAnkiLink(){
if(window.ankiLink)return;
const $=s=>document.querySelector(s),all=s=>document.querySelectorAll(s),app=$('#link-app'),modals=$('#modal-root');
if(!app||!modals)return;
const S={setup:{},boot:null,tab:'chats',thread:null,messages:{},drafts:{},outbox:{},sending:{},images:{},blobRequests:new Set(),read:{},register:false,picker:null,catalog:[],branches:new Set(),selected:new Set(),recipients:new Set(),stickerLibrary:[],people:{},receipts:{},typing:{},delivered:{},clock:0,operations:{},modalSerial:0,navSerial:0,groupPhotos:{},groupEdits:{},removedGroups:{},reactionPending:{},chatThemes:{},reactions:{},reactionVersions:{},revokedFiles:new Set(),revokedThreadFiles:{},legacyRemovals:{},membershipConfirmations:{}};
const packs={cheer:['🥳','You got this!'],love:['💜','Sending love'],coffee:['☕','Study fuel'],focus:['🧠','Big brain time'],wow:['😮','Wait… what?'],sleep:['😴','Tiny break'],thanks:['🫶','Thank you!'],yes:['✨','Nailed it!']};
const stickerArt=id=>`<span class="study-sticker sticker-${id}" aria-hidden="true"><span class="sticker-spark">+</span><span class="sticker-face"><i class="sticker-eyes"></i><i class="sticker-mouth"></i><i class="sticker-cheeks"></i></span><span class="sticker-spark second">+</span></span>`;
const reactionEmojis=['👍','❤️','😂','😮','😢','😡','🎉'];
const feature=name=>S.boot?.features?.[name]===true;
const emojis='😀 😁 😂 🤣 😊 🥹 😍 🥰 😘 😎 🤓 🫠 🤔 😭 😤 😴 🤯 🥳 😮 🥲 🙃 😌 🫶 💜 ❤️ 💕 💖 💯 ✨ ⭐ 🔥 🎉 🎊 👍 👏 🙌 🤝 💪 👀 🧠 📚 📖 ✍️ ☕ 🍜 🍟 🍰 🐱 🐶 🐸 🌸 🌙 ☀️ 🎮 💻 ✅ ❌ 💡 🚀'.split(' ');
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const nonce=()=>globalThis.crypto?.randomUUID?.()||Date.now().toString(36)+Math.random().toString(36).slice(2);
const send=(action,data={})=>{if(typeof pycmd==='function')pycmd('anki_link:'+JSON.stringify({action,...data}));};
const btn=(action,label,extra='',cls='')=>`<button class="btn ${cls}" data-action="${action}" ${extra}>${label}</button>`;
const retroIcons={
 chats:'<path d="M20 10.5c0 4-3.6 7-8 7H9l-4 3 1-4.2a6.8 6.8 0 0 1-2-5.3c0-4 3.6-7 8-7s8 3 8 7Z"/>',
 friends:'<circle cx="9" cy="7" r="3.4"/><path d="M2.7 20v-2.4a6.3 6.3 0 0 1 12.6 0V20Zm12-14a2.8 2.8 0 0 1 0 5.5m2.3 2.5a4.6 4.6 0 0 1 4.3 4.6V20h-3.8"/>',
 inbox:'<path d="m3 7.5 9-4 9 4-9 4Zm0 0v4l9 4 9-4v-4M3 12v4l9 4 9-4v-4"/>',
 search:'<circle cx="10.5" cy="10.5" r="5.5"/><path d="m15 15 4.5 4.5"/>',
 folder:'<path d="M3 7V5h7l2 2h9v12H3Z" fill="#ffdd9e"/><path d="M3 10h18"/>'
};
function retroIcon(name){
 return `<svg class="retro-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round" aria-hidden="true">${retroIcons[name]}</svg>`;
}
function retroFrame(content){
 return `<div class="retro-frame">${content}</div>`;
}
const composerIcons={image:'<rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="16" cy="8" r="1" fill="currentColor" stroke="none"/><path d="m4 17 6-7 7 9m-3-4 2-2 5 5"/>',emoji:'<circle cx="12" cy="12" r="9"/><circle cx="9" cy="10" r=".85" fill="currentColor" stroke="none"/><circle cx="15" cy="10" r=".85" fill="currentColor" stroke="none"/><path d="M8 14c1 3 7 3 8 0"/>',sticker:'<path d="M14 21H6a3 3 0 0 1-3-3V6a3 3 0 0 1 3-3h12a3 3 0 0 1 3 3v8Z"/><path d="M14 21v-4a3 3 0 0 1 3-3h4"/>'};
const icon=(action,label,symbol,extra='')=>`<button class="icon" data-action="${action}" aria-label="${label}" title="${label}" ${extra}>${['image','emoji','sticker'].includes(action)?`<svg class="compose-icon" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${composerIcons[action]}</svg>`:symbol}</button>`;
const initials=name=>String(name||'?').trim().split(/\s+/).slice(0,2).map(x=>x[0]).join('').toUpperCase();
const avatar=person=>{const p=typeof person==='string'?{name:person}:person||{},{src}=avatarVisual(p);return `<span class="avatar" ${p.groupId?`data-avatar-group="${esc(p.groupId)}"`:p.id?`data-avatar-user="${esc(p.id)}"`:''}>${src?`<img src="${src}" alt="" draggable="false">`:esc(initials(p.name))}</span>`;};
const partner=t=>t?.kind==='direct'?t.members.find(p=>p.id!==S.boot.user.id):{name:t?.title||'',groupId:t?.id,avatar:t?.avatar};
const person=id=>S.people[id]||S.boot?.friends.find(p=>p.id===id)||S.boot?.threads.flatMap(t=>t.members).find(p=>p.id===id)||{id,name:''};
function activityText(p){const a=p?.activity;if(!a||Date.now()/1000+S.clock-a.updated>55)return 'Offline';return a.status==='idle'?'Idle':a.deck?'Studying '+a.deck:'Online';}
function protectProfile(p){const guard=S.avatarSaved;if(guard&&p.id===guard.uid&&Date.now()<guard.until)return {...p,avatar:guard.avatar};return p;}
function avatarVisual(value){
 if(value.groupId){
  const photo=S.groupPhotos[value.groupId]||value,edit=S.groupEdits[value.groupId];
  if(edit&&['uploading','saving'].includes(edit.phase)&&(edit.preview||edit.remove))return {src:edit.remove?null:edit.preview,key:'preview-'+edit.request};
  return {src:photo.avatar?blob(photo.avatar):null,key:photo.avatar?.id||''};
 }
 const p=protectProfile(value),edit=S.avatarEdit;
 if(edit&&edit.uid===p.id&&['uploading','saving'].includes(edit.phase)&&(edit.preview||edit.remove))return {src:edit.remove?null:edit.preview,key:'preview-'+edit.request};
 return {src:p.avatar?blob(p.avatar):null,key:p.avatar?.id||''};
}
function profileProgress(){
 const host=$('#profile-progress');if(!host)return;const edit=S.avatarEdit||{},active=['choosing','preparing','cropping','uploading','saving'].includes(edit.phase);
 all('[data-action="avatar-set"],[data-action="avatar-remove"]').forEach(button=>button.disabled=active);
 const remove=$('[data-action="avatar-remove"]');if(remove)remove.hidden=!S.boot.user.avatar;
 host.setAttribute('aria-busy',String(active));host.classList.toggle('has-error',edit.phase==='failed');
 let label=({choosing:'Choose a picture…',preparing:'Preparing picture…',cropping:'Crop your picture…',uploading:'Uploading picture…',saving:edit.remove?'Removing picture…':'Saving profile…',saved:edit.remove?'Profile picture removed.':'Profile picture saved.',failed:edit.message||'Could not confirm the save. Please try again.'})[edit.phase]||'';
 const signature=JSON.stringify([label,active,edit.phase==='failed'&&edit.retryable]);if(host.dataset.state===signature)return;host.dataset.state=signature;host.replaceChildren();
 if(active){const spinner=document.createElement('span');spinner.className='profile-spinner';spinner.setAttribute('aria-hidden','true');host.appendChild(spinner);}
 const text=document.createElement('span');text.textContent=label;host.appendChild(text);
 if(edit.phase==='failed'&&edit.retryable){const retry=document.createElement('button');retry.className='link-btn';retry.dataset.action='avatar-retry';retry.textContent='Retry';host.appendChild(retry);}
}
function beginAvatar(remove=false){
 if(S.avatarEdit&&['choosing','preparing','cropping','uploading','saving'].includes(S.avatarEdit.phase))return;
 S.avatarEdit={request:nonce(),uid:S.boot.user.id,phase:remove?'saving':'choosing',remove};updatePeople();profileProgress();send('avatar',{request:S.avatarEdit.request,remove});
}
function updatePeople(){
 all('[data-person-status]').forEach(el=>{const p=person(el.dataset.personStatus),value=activityText(p);if(el.textContent!==value)el.textContent=value;el.classList.toggle('is-online',value!=='Offline');});
 all('[data-avatar-user]').forEach(el=>{const p=person(el.dataset.avatarUser);const {src,key}=avatarVisual(p);if(el.dataset.avatarKey===key&&(!src||el.querySelector('img')))return;el.dataset.avatarKey=key;if(src&&el.querySelector('img')?.getAttribute('src')===src)return;if(src){const img=document.createElement('img');img.src=src;img.alt='';img.draggable=false;el.replaceChildren(img);}else el.textContent=initials(p.name);});
 all('[data-avatar-group]').forEach(el=>{const id=el.dataset.avatarGroup,t=S.boot?.threads.find(t=>t.id===id),p={groupId:id,name:t?.title||'Group',avatar:t?.avatar},{src,key}=avatarVisual(p);if(el.dataset.avatarKey===key&&(!src||el.querySelector('img')))return;el.dataset.avatarKey=key;if(src&&el.querySelector('img')?.getAttribute('src')===src)return;if(src){const img=document.createElement('img');img.src=src;img.alt='';img.draggable=false;el.replaceChildren(img);}else el.textContent=initials(p.name);});
}
function keepGroupPhoto(t){
 if(t.kind!=='group')return t;const old=S.groupPhotos[t.id];
 if(old&&(old.avatar_version||0)>(t.avatar_version||0))return {...t,...old};
 S.groupPhotos[t.id]={avatar:t.avatar||null,avatar_version:t.avatar_version||0};return t;
}
function groupChanged(data){
 const old=S.groupPhotos[data.thread];if(old&&(old.avatar_version||0)>(data.avatar_version||0))return;
 const fields={avatar:data.avatar||null,avatar_version:data.avatar_version||0};S.groupPhotos[data.thread]=fields;
 const t=S.boot?.threads.find(t=>t.id===data.thread&&t.kind==='group');if(t)Object.assign(t,fields);
 updatePeople();groupPhotoProgress();
}
function groupPhotoProgress(){
 const host=$('#group-photo-progress');if(!host)return;const id=host.dataset.thread,edit=S.groupEdits[id]||{},active=['choosing','preparing','cropping','uploading','saving'].includes(edit.phase);
 all('[data-action="group-photo-set"],[data-action="group-photo-remove"]').forEach(el=>el.disabled=active);
 const remove=$('[data-action="group-photo-remove"]');if(remove)remove.hidden=!(S.groupPhotos[id]?.avatar||S.boot?.threads.find(t=>t.id===id)?.avatar);
 host.classList.toggle('has-error',edit.phase==='failed');host.setAttribute('aria-busy',String(active));
 const text=({choosing:'Choose a group photo…',preparing:'Preparing photo…',cropping:'Crop your photo…',uploading:'Uploading photo…',saving:edit.remove?'Removing photo…':'Saving group photo…',saved:edit.remove?'Group photo removed.':'Group photo saved.',failed:edit.message||'Could not save the group photo.'})[edit.phase]||'';
 const signature=JSON.stringify([text,active,edit.phase==='failed'&&edit.retryable]);if(host.dataset.state===signature)return;host.dataset.state=signature;host.replaceChildren();
 if(active){const spinner=document.createElement('span');spinner.className='profile-spinner';spinner.setAttribute('aria-hidden','true');host.appendChild(spinner);}
 const label=document.createElement('span');label.textContent=text;host.appendChild(label);
 if(edit.phase==='failed'&&edit.retryable){const button=document.createElement('button');button.className='link-btn';button.dataset.action='group-photo-retry';button.textContent='Retry';host.appendChild(button);}
}
function beginGroupPhoto(remove=false){
 const id=$('#group-photo-progress')?.dataset.thread;if(!id)return;const current=S.groupEdits[id];if(current&&['choosing','preparing','cropping','uploading','saving'].includes(current.phase))return;
 S.groupEdits[id]={request:nonce(),thread:id,phase:remove?'saving':'choosing',remove};updatePeople();groupPhotoProgress();send('group_photo',{thread:id,request:S.groupEdits[id].request,remove});
}
function groupPermissions(t){const uid=S.boot.user.id;return {owner:t.owner===uid,admin:t.owner===uid||t.members.some(p=>p.id===uid&&p.admin)};}
function memberActions(t,p){
 const rights=groupPermissions(t);if(!feature('group_administration'))return '';
 return (rights.owner&&p.id!==t.owner?btn('group-admin',p.admin?'Remove admin':'Make admin',`data-user="${esc(p.id)}" data-admin="${p.admin?'false':'true'}" role="menuitem"`,'ghost'):'')+(p.id!==t.owner&&p.id!==S.boot.user.id&&(rights.owner||rights.admin&&!p.admin)?btn('group-remove','Remove member',`data-user="${esc(p.id)}" role="menuitem"`,'ghost danger'):'');
}
function groupMembersHTML(t){
 const rights=groupPermissions(t),enabled=feature('group_administration');
 return `<div class="section-label">Members · ${t.members.length}</div><div class="group-members">${t.members.map(p=>`<div class="group-member row">${avatar({...p,...person(p.id)})}<div class="thread-copy"><strong>${esc(person(p.id).name||p.name)}</strong>${p.username?`<small class="muted">@${esc(p.username)}</small>`:''}<div class="member-badges">${p.id===S.boot.user.id?'<span class="tiny muted">You</span>':''}${t.owner===p.id?'<span class="member-role">Owner · Admin</span>':p.admin?'<span class="member-role">Admin</span>':''}</div></div>${memberActions(t,p)?`<button class="member-menu-trigger icon" data-member-menu="${esc(p.id)}" aria-label="Actions for ${esc(person(p.id).name||p.name)}" title="Member actions" aria-haspopup="menu" aria-expanded="false">⋯</button>`:''}</div>`).join('')}</div>${enabled?`<div class="row group-management">${rights.admin&&t.members.length<31?btn('group-add','Add friends','','secondary'):''}${btn('group-leave','Leave group','','ghost danger')}</div>`:''}`;
}
function memberMenu(trigger){
 if(S.floating?.trigger===trigger){closeFloating(true);return;}
 const t=thread(),p=t?.members.find(p=>p.id===trigger.dataset.memberMenu);if(!p)return;
 const html=memberActions(t,p);if(!html)return;
 openFloating(trigger,'member-menu',html,'menu','Member actions');operationView();
}
function refreshGroupDetails(){
 const host=$('[data-group-members]');if(!host)return;const t=S.boot?.threads.find(t=>t.id===host.dataset.groupMembers);if(!t)return;
 const html=groupMembersHTML(t);if(host.dataset.signature!==html){closeFloating();host.innerHTML=html;host.dataset.signature=html;}updatePeople();operationView();
 const count=$('.group-summary .tiny');if(count&&S.thread===t.id)count.textContent=t.members.length+' members';
}
function groupDetails(){
 const t=thread();if(t?.kind!=='group')return;
 modal('Group details',`<div class="group-profile row">${avatar(partner(t))}<div class="group-profile-copy"><h3>${esc(t.title)}</h3><div class="row group-photo-actions">${btn('group-photo-set','Change photo','','secondary')}${btn('group-photo-remove','Remove photo','','ghost')}</div></div></div><div id="group-photo-progress" class="profile-progress" data-thread="${esc(t.id)}" role="status" aria-live="polite"></div><div data-group-members="${esc(t.id)}">${groupMembersHTML(t)}</div>`,btn('close-modal','Close','','secondary'));
 updatePeople();groupPhotoProgress();
}
function groupAdd(){
 const t=thread();if(!t||!feature('group_administration')||!groupPermissions(t).admin)return;
 const members=new Set(t.members.map(p=>p.id)),friends=accepted().filter(p=>!members.has(p.id));
 modal('Add friends',`<p class="muted">New members can see the existing conversation. ${Math.max(0,31-t.members.length)} places available.</p><div class="recipient-grid">${friends.map(p=>`<label class="pill"><input type="checkbox" data-group-recipient value="${esc(p.id)}">${esc(p.name)}</label>`).join('')||'<p class="muted">All your accepted friends are already members.</p>'}</div>`,btn('group-details','Back','','secondary')+btn('group-add-confirm','Add selected',friends.length?'':'disabled'));
 $('.modal').dataset.groupThread=t.id;
}
function groupConfirm(action,user){
 const t=thread();if(!t||!feature('group_administration'))return;
 const leave=action==='group_leave',p=t.members.find(p=>p.id===user);
 if(!leave&&!p)return;
 modal(leave?'Leave group?':'Remove member?',`<p>${leave?'You will lose access to this conversation and its files.':`Remove ${esc(p.name)} from ${esc(t.title)}? They will lose access to the conversation and its files.`}</p>${leave&&t.owner===S.boot.user.id?`<p>${t.members.length>1?'A remaining member will be randomly chosen as the new owner and promoted to admin.':'You are the last member. This group will be archived.'}</p>`:''}`,btn('group-details','Cancel','','secondary')+btn(leave?'group-leave-confirm':'group-remove-confirm',leave?'Leave group':'Remove member',`data-thread-id="${esc(t.id)}" data-user="${esc(user||'')}"`,'danger'));
 $('.modal').dataset.groupThread=t.id;
}
function groupMembership(data){
 const t=S.boot?.threads.find(t=>t.id===data.thread);
 if(data.removed===S.boot?.user.id){removeGroup(data.thread,data.membership_version,data._membership_epoch);return;}
 if(!t)return;
 if(data.members&&(data.membership_version||0)>=(t.membership_version||0)){Object.assign(t,{owner:data.owner,members:data.members,membership_version:data.membership_version});for(const p of data.members)S.people[p.id]={...S.people[p.id],...p};refreshGroupDetails();}
}
function removeGroup(id,version,epoch){
 const t=S.boot?.threads.find(t=>t.id===id),hadRemoval=S.removedGroups[id]!==undefined;if(version!==undefined&&version<(t?.membership_version||0))return;
 for(const key of Object.keys(S.reactionPending))if(key.startsWith(id+'|'))delete S.reactionPending[key];
 S.removedGroups[id]=Math.max(S.removedGroups[id]||0,t?.membership_version||0,version||0);
 if(version===undefined){if(!hadRemoval||Object.prototype.hasOwnProperty.call(S.legacyRemovals,id))S.legacyRemovals[id]=epoch??null;}else delete S.legacyRemovals[id];delete S.membershipConfirmations[id];
 const files=new Set([...(S.messages[id]||[]),...Object.values(S.outbox).filter(m=>m.thread===id)].map(m=>m.attachment?.id).filter(Boolean));if(t?.avatar?.id)files.add(t.avatar.id);
 for(const [key,value] of Object.entries(S.deckInvites||{}))if(value.thread===id){if(value.attachment?.id)files.add(value.attachment.id);delete S.deckInvites[key];}
 const revoked=S.revokedThreadFiles[id]||(S.revokedThreadFiles[id]=new Set());for(const fid of files)revoked.add(fid);
 for(const fid of files){delete S.images[fid];S.blobRequests.delete(fid);S.revokedFiles.add(fid);}
 for(const key of ['messages','drafts','sending','read','receipts','typing','delivered','groupPhotos','groupEdits','reactions','reactionVersions'])delete S[key][id];
 for(const [key,m] of Object.entries(S.outbox))if(m.thread===id)delete S.outbox[key];
 for(const [key,op] of Object.entries(S.operations))if(op.thread===id)delete S.operations[key];
 if(S.boot){S.boot.threads=S.boot.threads.filter(t=>t.id!==id);S.boot.invites=S.boot.invites.filter(i=>i.thread!==id);}
 if(S.shareTarget?.id===id)delete S.shareTarget;
 if(S.preview?.invitation?.thread===id)delete S.preview;
 if($('[data-group-members]')?.dataset.groupMembers===id||$('.modal')?.dataset.groupThread===id)closeModal();
 $('.photo-viewer')?.remove();if(S.thread===id){stopTyping();S.thread=null;S.navSerial++;send('thread',{id:null});render();}else if(S.boot){refreshSidebar();if(S.tab==='inbox'&&$('.workspace'))$('.workspace').innerHTML=inbox();operationView();}
}
function chatIdentity(t){
 if(t.kind==='group')return `<button class="row group-summary" data-action="group-details" aria-label="Group details" title="Group details">${avatar(partner(t))}<span class="group-summary-copy"><span class="chat-title">${esc(t.title)}</span><span class="tiny muted">${t.members.length} members</span></span></button>`;
 return `<div class="row chat-identity">${avatar(partner(t))}<div><h2>${esc(t.title)}</h2><div class="tiny muted"><span data-person-status="${esc(partner(t)?.id)}">${esc(activityText(person(partner(t)?.id)))}</span></div></div></div>`;
}
function receiptText(m){
 const peers=Object.values(S.receipts[m.thread]||{}).filter(r=>r.uid!==S.boot.user.id),seen=peers.filter(r=>r.seen>=m.id),delivered=peers.filter(r=>Math.max(r.delivered||0,r.seen||0)>=m.id);
 if(seen.length)return peers.length>1&&seen.length<peers.length?'Seen by '+seen.length:'Seen';
 if(delivered.length)return peers.length>1&&delivered.length<peers.length?'Delivered to '+delivered.length:'Delivered';return 'Sent';
}
function updateReceipts(rows=[]){
 for(const r of rows){const thread=S.receipts[r.thread]||(S.receipts[r.thread]={}),old=thread[r.uid]||{};thread[r.uid]={...r,seen:Math.max(r.seen||0,old.seen||0),delivered:Math.max(r.delivered||0,old.delivered||0)};}
 all('[data-message-id].mine').forEach(el=>{const m=(S.messages[S.thread]||[]).find(m=>m.id===Number(el.dataset.messageId)),label=el.querySelector('.delivery-status');if(m&&label)label.textContent=receiptText(m);});
}
function typingView(){
 const area=$('.typing-indicator');if(!area)return;
 const names=Object.values(S.typing[S.thread]||{}).filter(t=>t.uid!==S.boot.user.id&&t.until>Date.now()/1000+S.clock).map(t=>person(t.uid).name||'Someone');
 const text=names.length?(names.length>2?'Several people':names.join(' and '))+(names.length===1?' is typing':' are typing'):'';
 if(area.dataset.value===text)return;area.dataset.value=text;area.replaceChildren();
 if(text){const dots=document.createElement('span');dots.className='typing-dots';dots.setAttribute('aria-hidden','true');for(let i=0;i<3;i++)dots.appendChild(document.createElement('i'));area.appendChild(dots);const label=document.createElement('span');label.textContent=text+'…';area.appendChild(label);}
}
function stopTyping(){if(S.lastTypingThread){send('typing',{thread:S.lastTypingThread,typing:false});S.lastTypingThread=null;}clearTimeout(S.typingStop);}
function typingInput(){
 if(!S.thread)return;const active=!!$('#message-input')?.value.trim();if(!active){stopTyping();return;}
 if(S.lastTypingThread!==S.thread||Date.now()-(S.typingSent||0)>1800){if(S.lastTypingThread&&S.lastTypingThread!==S.thread)stopTyping();S.lastTypingThread=S.thread;S.typingSent=Date.now();send('typing',{thread:S.thread,typing:true});}
 clearTimeout(S.typingStop);S.typingStop=setTimeout(stopTyping,2500);
}
function receiveStatus(data){
 if(data.server_time)S.clock=data.server_time-Date.now()/1000;
 for(const value of data.people||[]){const p=protectProfile(value);S.people[p.id]=p;if(S.boot?.user.id===p.id)S.boot.user={...S.boot.user,...p};}
 if(data.typing){S.typing={};for(const t of data.typing)(S.typing[t.thread]||(S.typing[t.thread]={}))[t.uid]=t;}
 if(data.group_memberships&&S.boot){const ids=new Set(data.group_memberships.map(g=>g.thread));for(const t of [...S.boot.threads])if(t.kind==='group'&&!ids.has(t.id))removeGroup(t.id,undefined,data._membership_epoch);for(const g of data.group_memberships)if(S.removedGroups[g.thread]!==undefined)S.membershipConfirmations[g.thread]=g.membership_version||0;}
 for(const reaction of data.reactions||[])reactionChanged(reaction);
 updateReceipts(data.receipts);updatePeople();typingView();
}
const time=stamp=>new Date(stamp*1000).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'});
function toast(value){const el=$('#toast');el.textContent=value;el.style.display='block';clearTimeout(S.toast);S.toast=setTimeout(()=>el.style.display='none',6500);}
function modal(title,body,footer='',wide=false){closeFloating();if(!$('.modal'))S.modalTrigger=document.activeElement;S.picker=null;closePicker();modals.innerHTML=`<div class="shade"><section class="modal ${wide?'wide':''}" tabindex="-1" data-modal="${++S.modalSerial}" role="dialog" aria-modal="true" aria-label="${esc(title)}"><div class="modal-head"><h2>${esc(title)}</h2>${icon('close-modal','Close','×')}</div><div class="modal-body">${body}<div class="operation-status" role="status" aria-live="polite" hidden></div><div class="modal-error" role="alert"></div></div>${footer?`<div class="modal-foot">${footer}</div>`:''}</section></div>`;operationView();$('.modal')?.focus({preventScroll:true});}
function closeModal(){closeFloating();const trigger=S.modalTrigger;modals.innerHTML='';S.modalTrigger=null;S.modalSerial++;document.body.classList.remove('busy');if(trigger?.isConnected)trigger.focus({preventScroll:true});}
function busy(value){document.body.classList.toggle('busy',value);all('.auth-form button[type=submit]').forEach(b=>b.disabled=value);}
const operationSpecs={friend_request:['Sending request…','[data-action="friend-send"]','friends'],friend_decide:['Saving friend request…','[data-friend-accept],[data-friend-reject]','friends'],group:['Creating group…','[data-action="create-group"]','chats'],direct:['Opening conversation…','[data-action="direct"]','chats'],catalog:['Loading your decks…','[data-action="share"]','inbox'],share:['Preparing decks…','[data-action="share-send"]','inbox'],preview_invite:['Downloading shared decks…','[data-action="preview"]','inbox'],accept_invite:['Importing cards…','[data-action="accept"],[data-action="reject"]','inbox'],reject_invite:['Declining invitation…','[data-action="reject"],[data-action="accept"]','inbox'],reaction:['Saving reaction…','[data-react-message],[data-reaction-choice],[data-reaction-people]','chats'],group_add:['Adding members…','[data-action="group-add-confirm"]','chats'],group_remove:['Removing member…','[data-action="group-remove-confirm"]','chats'],group_admin:['Updating admin…','[data-action="group-admin"]','chats'],group_leave:['Leaving group…','[data-action="group-leave-confirm"]','chats']};
function operationView(){
 const pending=Object.values(S.operations).filter(op=>op.action!=='reaction'),pane=$('.modal'),id=pane?.dataset.modal;
 all('[data-operation-disabled]').forEach(el=>{el.disabled=false;el.removeAttribute('data-operation-disabled');el.removeAttribute('aria-busy');});
 for(const op of pending)if((!op.thread||op.thread===S.thread)&&!['catalog','preview_invite'].includes(op.action))for(const el of all(op.action==='reaction'?`[data-react-message="${op.messageId}"],[data-reaction-message="${op.messageId}"]`:operationSpecs[op.action][1])){el.disabled=true;el.dataset.operationDisabled='true';el.setAttribute('aria-busy','true');}
 all('[data-tab]').forEach(el=>{const active=pending.some(op=>operationSpecs[op.action][2]===el.dataset.tab);el.setAttribute('aria-busy',String(active));});
 const host=pane?.querySelector('.operation-status'),op=pending.find(op=>(!op.thread||op.thread===S.thread)&&(op.modal===id||pane?.querySelector(operationSpecs[op.action][1])));if(!host)return;
 host.hidden=!op;if(!op){host.replaceChildren();return;}
 if(host.dataset.request!==op.id){host.dataset.request=op.id;const spinner=document.createElement('span');spinner.className='profile-spinner';spinner.setAttribute('aria-hidden','true');const label=document.createElement('span');host.replaceChildren(spinner,label);}
 host.lastChild.textContent=op.message;
}
function request(action,data={}){
 if(['preview_invite','accept_invite','reject_invite'].includes(action)){const item=S.boot?.invites.find(i=>i.id===data.id)||S.deckInvites?.[data.id];if(item?.thread){data={...data,thread:item.thread};if($('.modal'))$('.modal').dataset.groupThread=item.thread;}}
 const key=action+':'+(data.thread||'')+':'+(data.message||data.id||data.user||''),existing=Object.values(S.operations).find(op=>op.key===key);
 if(existing){if(action==='catalog'||action==='preview_invite'){existing.modal=$('.modal')?.dataset.modal;existing.nav=S.navSerial;}operationView();return;}
 const id=nonce(),op={id,key,action,thread:data.thread,messageId:data.message,modal:$('.modal')?.dataset.modal,nav:S.navSerial,message:operationSpecs[action][0]};
 S.operations[id]=op;if($('.modal-error'))$('.modal-error').textContent='';operationView();send(action,{...data,_request:id});return id;
}
function finishOperation(data){
 const op=S.operations[data.request];if(!op)return;
 if(data.phase==='loading'){op.message=data.message||op.message;operationView();return;}
 delete S.operations[op.id];operationView();
 if(op.action==='reaction'){finishReaction(op,data);return;}
 const sameModal=op.modal===($('.modal')?.dataset.modal),current=sameModal&&op.nav===S.navSerial;
 if(data.phase==='failed'){if(sameModal&&$('.modal-error'))$('.modal-error').textContent=data.message;else toast(data.message);return;}
 if(data.event==='reaction_updated'){reactionChanged(data.data);return;}
 if(data.event==='group_result'){
  groupMembership(data.data||{});
  if(current&&$('.modal')){if(op.action==='group_add'||op.action==='group_remove')groupDetails();else if(op.action==='group_leave')closeModal();}
  else if(op.action!=='group_admin')toast('Group updated.');return;
 }
 if(data.event==='social_result'){
  const value=data.data||{},label=op.action==='group'?'Group created.':op.action==='friend_request'?'Friend request sent.':op.action==='friend_decide'?'Friend request updated.':'Conversation ready.';
  if(current){if(op.modal)closeModal();if(value.thread)selectThread(value.thread);else toast(label);}else toast(label);
  return;
 }
 if(current)window.ankiLink.receive(data.event,data.data);
 else if(data.event==='shared')toast('Deck invitations sent.');
 else if(data.event==='imported')toast(`${data.data.cards} shared cards are ready in Anki.`);
 else if(data.event==='notice')toast(data.data);
}
function auth(){app.innerHTML=retroFrame(`<div class="auth"><aside class="welcome"><div><div class="row"><div class="mark">a<span>↗</span></div><span class="wordmark">AnkiLink</span></div><h1>A little closer.<br>A little smarter.</h1><p>Your study people, messages and shared decks. Together in Anki.</p></div><div class="preview-cards"><div class="preview-card"><small>SCIENCE · STUDY TOGETHER</small><strong>A good question<br>is better shared.</strong></div><div class="preview-card"><small>FROM YOUR STUDY PARTNER</small><strong>“You’ve got this 💜”</strong><small>20 new cards are waiting.</small></div></div><div class="tiny muted">Private conversations. Your own study progress.</div></aside><section class="auth-content"><form class="auth-form stack" id="auth-form"><div><h2>${S.register?'Find your study people.':'Welcome back.'}</h2><p class="muted">${S.register?'Create your sharing account.':'Sign in to AnkiLink.'}</p></div><label class="field">Server address<input id="server-url" type="url" required placeholder="https://your-sharing-server.com" value="${esc(S.setup.url||'')}"></label>${S.register?'<label class="field">Display name<input id="auth-name" maxlength="60" required autocomplete="nickname"></label>':''}<label class="field">Username<input id="auth-user" required minlength="3" maxlength="32" autocomplete="username"></label><label class="field">Password<input id="auth-password" type="password" required minlength="10" maxlength="200" autocomplete="${S.register?'new-password':'current-password'}"></label>${S.register?'<label class="field">Invitation code<input id="join-code" autocomplete="off"></label>':''}${S.setup.remember_available?'<label class="checks"><input type="checkbox" id="remember" checked>Keep me signed in on this Windows account</label>':''}<div class="auth-error" role="alert"></div><button class="btn" type="submit">${S.register?'Create account':'Sign in'}</button><div class="auth-switch">${S.register?'Already have an account?':'First time here?'} <button type="button" class="link-btn" data-action="auth-switch">${S.register?'Sign in':'Create account'}</button></div></form></section></div>`);}
function accepted(){return (S.boot?.friends||[]).filter(f=>f.status==='accepted');}
function thread(){return S.boot?.threads.find(t=>t.id===S.thread);}
function lastText(t){if(!t.last)return 'Say hello';return ['text','system'].includes(t.last.kind)?t.last.text:t.last.kind==='deck'?'Shared a deck':t.last.kind==='sticker'?'Sent a sticker':'Sent an image';}
function sidebar(){
 const requests=S.boot.friends.filter(p=>p.incoming&&p.status==='pending').length;
 const inbox=S.boot.invites.filter(i=>i.recipient===S.boot.user.id&&i.state==='pending').length;
 const search=S.tab==='chats'?'<label class="message-search">'+retroIcon('search')+'<input id="conversation-search" type="search" aria-label="Search conversations" placeholder="Search" autocomplete="off"></label>':'';
 let content='';
 if(S.tab==='chats')content=`<div class="row spread nav-head"><strong>Messages</strong>${icon('new-group','New group','+')}</div>`+(S.boot.threads.map(t=>`<button class="thread ${S.thread===t.id?'active':''}" data-thread="${t.id}">${avatar(partner(t))}<span class="thread-copy"><strong>${esc(t.title)}</strong><small>${esc(lastText(t))}</small></span>${Number.isFinite(t.last?.created)?`<time class="conversation-time">${esc(time(t.last.created))}</time>`:''}${t.unread?`<span class="badge">${t.unread}</span>`:''}</button>`).join('')||'<div class="scroll-empty">Add a friend to start a conversation.</div>')+'<div class="scroll-empty search-empty" hidden>No matching conversations.</div>';
 if(S.tab==='friends')content=`<div class="row spread nav-head"><strong>Your people</strong>${icon('add-friend','Add friend','+')}</div>`+S.boot.friends.map(p=>`<div class="friend">${avatar(S.people[p.id]||p)}<span class="thread-copy"><strong>${esc(p.name)}</strong><small>${p.status==='accepted'?`<span data-person-status="${p.id}">${esc(activityText(person(p.id)))}</span>`:p.incoming?'Wants to connect':'Request sent'}</small>${p.status==='pending'&&p.incoming?`<div class="row" style="margin-top:6px"><button class="link-btn" data-friend-accept="${p.id}">Accept</button><button class="link-btn muted" data-friend-reject="${p.id}">Decline</button></div>`:''}</span>${p.status==='accepted'?icon('direct','Message','↗',`data-user="${p.id}"`):''}</div>`).join('');
 if(S.tab==='inbox')content='<div class="nav-head"><strong>Deck invitations</strong><div class="tiny muted">Your incoming and sent decks.</div></div>';
 return `<aside class="sidebar"><div class="row brand"><div class="mark">a<span>↗</span></div><span class="wordmark">AnkiLink</span></div><nav class="tabs">${[['chats','Chats'],['friends','Friends'+(requests?' · '+requests:'')],['inbox','Decks'+(inbox?' · '+inbox:'')]].map(([id,label])=>`<button data-tab="${id}" class="${S.tab===id?'active':''}">${retroIcon(id)}<span class="nav-tab-label">${label}</span></button>`).join('')}</nav>${search}<div class="list">${content}</div><div class="self row spread"><div class="row">${avatar(S.boot.user)}<div><strong class="tiny self-name">${esc(S.boot.user.name)}</strong><div class="tiny muted">${esc(S.boot.user.code)}</div></div></div>${icon('account','Account','⋯')}</div></aside>`;
}
function filterConversations(){
 const input=$('#conversation-search');
 if(!input)return;
 const search=S.chatSearch||'';
 if(input.value!==search)input.value=search;
 const query=S.setup.appearance==='ankimessage'?search.trim().toLowerCase():'';
 let matches=0;
 for(const row of all('.sidebar .thread')){
  row.hidden=!!query&&!row.querySelector('.thread-copy').textContent.toLowerCase().includes(query);
  if(!row.hidden)matches++;
 }
 const empty=$('.search-empty');
 if(empty)empty.hidden=!query||matches>0;
}
function refreshSidebar(){
 const side=$('.sidebar'),markup=sidebar();
 if(!side||markup===S.sidebarMarkup)return;
 const previous=$('#conversation-search');
 const selection=previous&&document.activeElement===previous?[previous.selectionStart,previous.selectionEnd]:null;
 side.outerHTML=markup;
 S.sidebarMarkup=markup;
 filterConversations();
 const input=$('#conversation-search');
 if(selection&&input){
  input.focus({preventScroll:true});
  input.setSelectionRange(...selection);
 }
}
function render(){
 closeFloating();
 if(!S.boot){auth();return;}
 const old=$('.composer textarea');if(old&&S.thread)S.drafts[S.thread]=old.value;
 const active=thread();const body=S.tab==='inbox'?inbox():active?`<header class="chat-head"><button class="icon chat-back" data-action="back-chats" aria-label="Back to chats" title="Back to chats">‹</button>${chatIdentity(active)}<div class="row chat-actions">${btn('share',retroIcon('folder')+'<span class="chat-share-label">Share decks</span>','aria-label="Share decks" title="Share decks"','secondary')}${icon('conversation-options','Conversation options','⋯')}</div></header><div class="connection" hidden></div><div class="messages" aria-live="polite"></div><div class="composer-wrap"><div class="typing-indicator" aria-live="polite"></div><div class="composer">${icon('image','Send image','＋')}${icon('emoji','Emojis','☺')}${icon('sticker','Stickers','▧')}<textarea rows="1" id="message-input" aria-label="Message" placeholder="Write a message…" maxlength="8000">${esc(S.drafts[S.thread]||'')}</textarea><button class="icon send-btn" data-action="send" aria-label="Send message" title="Send message"><span class="send-arrow" aria-hidden="true">↑</span><span class="send-label" aria-hidden="true">Send</span></button></div><div class="upload-state" hidden></div></div>`:`<div class="empty"><div class="mark">a<span>↗</span></div><h2>Good company.<br>Better study days.</h2><p>Choose a conversation, or add someone with their friend code.</p><div class="row" style="margin-top:12px">${btn('add-friend','Add a friend')}${btn('share','Share decks','','secondary')}</div></div>`;
 const workspaceClass=active&&S.tab!=='inbox'?'workspace chat-workspace'+(active.kind==='group'?'':' direct-chat'):'workspace';
 S.sidebarMarkup=sidebar();app.innerHTML=retroFrame('<div class="layout '+(S.tab==='inbox'?'inbox-open':S.tab==='chats'&&S.thread?'conversation-open':'')+'">'+S.sidebarMarkup+'<main class="'+workspaceClass+'">'+body+'</main></div>');
 if(S.thread&&!active&&S.tab==='chats')$('.workspace').innerHTML='<div class="loading"><span class="profile-spinner" aria-hidden="true"></span><p role="status">Opening conversation…</p></div>';
 filterConversations();applyChatTheme();if(active&&S.tab!=='inbox')renderMessages(true);updatePeople();typingView();operationView();
}
function blob(meta){if(!S.images[meta.id]&&!S.blobRequests.has(meta.id)){S.blobRequests.add(meta.id);const id=S.boot?.threads.find(t=>t.avatar?.id===meta.id||(S.messages[t.id]||[]).some(m=>m.attachment?.id===meta.id))?.id;send('blob',{...meta,...(id?{_thread:id}:{})});}return S.images[meta.id];}
function photo(meta,sticker=false){const src=blob(meta);return src?`<img class="message-photo" data-photo="${meta.id}" src="${src}" alt="${esc(sticker?'Sticker':meta.name)}">`:`<div class="image-loading" data-image-pending="${meta.id}">${sticker?'Loading sticker…':'Loading image…'}</div>`;}
function rememberInvites(rows=[]){
 const uid=S.boot?.user.id;if(!uid)return;S.deckInvites||={};
 for(const row of rows)if(row&&typeof row.id==='string'&&(row.sender===uid||row.recipient===uid)){
  const old=S.deckInvites[row.id];S.deckInvites[row.id]=old&&old.state!=='pending'&&row.state==='pending'?old:row;
 }
 const ids=Object.keys(S.deckInvites);if(ids.length>1000)ids.sort((a,b)=>(S.deckInvites[a].created||0)-(S.deckInvites[b].created||0)).slice(0,ids.length-1000).forEach(id=>delete S.deckInvites[id]);
}
function deckInvites(){return Object.values({...Object.fromEntries((S.boot?.invites||[]).map(i=>[i.id,i])),...S.deckInvites});}
function messageBody(m){
 if(m.kind==='text')return esc(m.text);
 if(m.kind==='image'||m.kind==='sticker'&&m.attachment)return photo(m.attachment,m.kind==='sticker');
 if(m.kind==='sticker'){const p=packs[m.text]||['✨',''];return stickerArt(m.text)+`<span class="sticker-caption">${p[1]}</span>`;}
 const allInvites=deckInvites(),related=m.thread&&m.nonce?allInvites.filter(x=>x.thread===m.thread&&x.sender===m.sender&&x.nonce===m.nonce):[],uid=S.boot.user.id;
 const i=related.find(x=>x.recipient===uid)||allInvites.find(x=>x.id===m.invite),s=i?.summary;
 const group=S.boot.threads.find(t=>t.id===m.thread)?.kind==='group';
 let state=i?.state||'Sent';
 if(group&&m.sender===uid&&related.length){const accepted=related.filter(x=>x.state==='accepted').length,declined=related.filter(x=>x.state==='rejected').length;state=`${accepted} accepted · ${related.length-accepted-declined} pending${declined?` · ${declined} declined`:''}`;}
 return `<div class="deck-symbol" aria-hidden="true"></div><div class="deck-card-copy"><strong>${esc(m.text).replace(/::/g, "::<wbr>")}</strong><p>${s?`${s.cards} cards · ${s.filtered_decks?'Includes filtered practice decks':'Decks and subdecks'}`:'Deck invitation'}</p>${i?.recipient===uid&&i.state==='pending'?btn('preview','View invitation',`data-id="${i.id}"`,'secondary'):`<span class="status">${esc(state)}</span>`}</div>`;
}
function reactionHTML(m){
 if(!feature('message_reactions')||m.outgoing||m.kind==='system')return '';
 const chips=displayedReactions(m).filter(r=>reactionEmojis.includes(r.emoji)&&r.count>0).map(r=>{const mine=(r.users||[]).includes(S.boot.user.id),names=(r.users||[]).map(id=>{const p=id===S.boot.user.id?S.boot.user:person(id);return p.username?'@'+p.username:p.name||'Member';}).join(', ');return `<button class="reaction-chip ${mine?'is-mine':''}" data-reaction-people="${esc(r.emoji)}" data-reaction-message="${m.id}" aria-haspopup="dialog" title="${esc(names)}" aria-label="${esc(r.emoji+' · '+r.count+' · '+names)}">${r.emoji} <span>${r.count}</span></button>`;}).join('');
 return `${chips?`<div class="message-reactions">${chips}</div>`:''}<button class="reaction-add" data-react-message="${m.id}" title="React to message" aria-label="React to message" aria-expanded="false" aria-haspopup="true"><svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" aria-hidden="true"><path d="M20.5 13a8.5 8.5 0 1 1-9.5-9.5M7.5 14a4.5 4.5 0 0 0 8 0"/><path d="M18 2v6m-3-3h6"/><circle cx="8.5" cy="10" r=".7"/><circle cx="14" cy="10" r=".7"/></svg></button>`;
}
function refreshReactions(){
 all('[data-message-id]').forEach(el=>{const m=(S.messages[S.thread]||[]).find(m=>m.id===Number(el.dataset.messageId));if(!m)return;const host=el.querySelector('.reaction-host'),html=reactionHTML(m);if(host&&host.dataset.signature!==html){host.innerHTML=html;host.dataset.signature=html;}});if(S.floating&&!S.floating.trigger.isConnected)closeFloating();refreshReactionPeople();operationView();
}
function reactionPeople(message,emoji){
 const m=(S.messages[S.thread]||[]).find(m=>m.id===Number(message));if(!m||!displayedReactions(m).some(r=>r.emoji===emoji))return;
 modal('Reactions',`<div class="reaction-people" data-thread="${esc(S.thread)}" data-message="${m.id}" data-emoji="${esc(emoji)}"></div>`,btn('close-modal','Close','','secondary'));
 $('.modal').classList.add('reaction-dialog');$('.modal').dataset.groupThread=S.thread;refreshReactionPeople();
}
function refreshReactionPeople(){
 const host=$('.reaction-people');if(!host)return;
 const m=(S.messages[host.dataset.thread]||[]).find(m=>m.id===Number(host.dataset.message)),users=m?displayedReactions(m).find(r=>r.emoji===host.dataset.emoji)?.users||[]:[];
 const unique=[...new Set(users)],rows=unique.map(id=>{const p=id===S.boot?.user.id?S.boot.user:person(id);return `<div class="reaction-person">${avatar(p)}<div class="reaction-person-copy"><strong>${esc(p.name||p.username||'Member')}</strong>${p.username?`<small>@${esc(p.username)}</small>`:''}</div>${id===S.boot?.user.id?'<span class="reaction-self">You</span>':''}</div>`;}).join('')||'<p class="muted">No one has this reaction now.</p>';
 const html=`<div class="reaction-list-summary"><span class="reaction-summary-emoji" aria-hidden="true">${esc(host.dataset.emoji)}</span><span class="reaction-summary-count" aria-live="polite">${unique.length} ${unique.length===1?'person':'people'}</span></div><div class="reaction-person-list">${rows}</div>`;
 if(host.innerHTML!==html)host.innerHTML=html;
}
function reactionChanged(data){
 if(!S.boot||S.removedGroups[data.thread]!==undefined||!S.boot.threads.some(t=>t.id===data.thread))return;
 const versions=S.reactionVersions[data.thread]||={},version=Number(data.reaction_version)||0;if(version<(versions[data.message]||0))return;versions[data.message]=version;
 (S.reactions[data.thread]||={})[data.message]=data.reactions||[];
 const m=(S.messages[data.thread]||[]).find(m=>m.id===Number(data.message));if(m){m.reactions=data.reactions||[];m.reaction_version=version;}
 if(S.thread===data.thread)refreshReactions();
}
function displayedReactions(m){
 const pending=S.reactionPending[m.thread+'|'+m.id];if(!pending)return m.reactions||[];
 const me=S.boot.user.id,groups=(m.reactions||[]).map(r=>({...r,users:(r.users||[]).filter(id=>id!==me)}));
 if(pending.desired){let row=groups.find(r=>r.emoji===pending.desired);if(!row){row={emoji:pending.desired,users:[]};groups.push(row);}row.users.push(me);}
 return groups.map(r=>({...r,count:r.users.length})).filter(r=>r.count);
}
function flushReaction(tid,mid){
 const pending=S.reactionPending[tid+'|'+mid];if(!pending||pending.inflight)return;
 pending.inflight=true;pending.sent=pending.desired;
 pending.request=request('reaction',{thread:tid,message:mid,emoji:pending.sent});
}
function finishReaction(op,data){
 const key=op.thread+'|'+op.messageId,pending=S.reactionPending[key];
 if(data.phase!=='failed'&&data.data)reactionChanged(data.data);
 if(!pending)return;
 pending.inflight=false;
 if(pending.desired!==pending.sent){flushReaction(op.thread,op.messageId);refreshReactions();return;}
 delete S.reactionPending[key];refreshReactions();
 if(data.phase==='failed')toast(data.message||'Could not confirm reaction. Please try again.');
}
function chooseReaction(message,emoji){
 const m=(S.messages[S.thread]||[]).find(m=>m.id===Number(message));if(!m||m.kind==='system'||m.outgoing||!feature('message_reactions'))return;
 const mine=displayedReactions(m).find(r=>(r.users||[]).includes(S.boot.user.id)),key=S.thread+'|'+m.id;
 const pending=S.reactionPending[key]||={inflight:false};pending.desired=mine?.emoji===emoji?'':emoji;
 closeFloating(true);refreshReactions();flushReaction(S.thread,m.id);
}
function closeFloating(restore=false){
 const floating=S.floating;if(!floating)return;S.floating=null;floating.host.remove();floating.trigger.setAttribute('aria-expanded','false');
 if(restore&&floating.trigger.isConnected)floating.trigger.focus({preventScroll:true});
}
function openFloating(trigger,cls,html,role,label){
 closeFloating();const host=document.createElement('div');host.className=cls;host.setAttribute('role',role);host.setAttribute('aria-label',label);host.innerHTML=html;host.style.position='fixed';document.body.appendChild(host);
 S.floating={host,trigger};trigger.setAttribute('aria-expanded','true');
 const rect=trigger.getBoundingClientRect(),box=host.getBoundingClientRect(),pad=8,vw=document.documentElement.clientWidth||window.innerWidth,vh=document.documentElement.clientHeight||window.innerHeight;
 const width=box.width||Math.min(cls==='reaction-picker'?278:180,vw-pad*2),height=box.height||52;
 const left=Math.max(pad,Math.min(rect.right-width,vw-width-pad));
 const below=rect.bottom+6,top=below+height<=vh-pad?below:Math.max(pad,Math.min(rect.top-height-6,vh-height-pad));
 host.style.left=left+'px';host.style.top=top+'px';host.querySelector('button:not(:disabled)')?.focus({preventScroll:true});
}
function reactionPicker(message){
 const article=[...all('[data-message-id]')].find(el=>el.dataset.messageId===message),trigger=article?.querySelector('[data-react-message]');if(!trigger)return;
 if(S.floating?.trigger===trigger){closeFloating(true);return;}
 openFloating(trigger,'reaction-picker',reactionEmojis.map(emoji=>`<button data-reaction-choice="${esc(emoji)}" data-reaction-message="${message}" aria-label="React ${esc(emoji)}">${emoji}</button>`).join(''),'group','Choose a reaction');operationView();
}
function messageHTML(m,showSenderNames=false){
 if(m.kind==='system')return `<article class="message-system" data-message-id="${m.id}"><span>${esc(m.text)}</span></article>`;
 const status=m.outgoing?`<span>${m.failed?'Not sent':'Sending…'}</span>${m.failed?`<button type="button" class="link-btn tiny" data-retry-message="${esc(m.nonce)}">Retry</button>`:''}`:m.sender===S.boot.user.id?`<span class="delivery-status">${receiptText(m)}</span>`:'';
 return `<article class="message ${m.sender===S.boot.user.id?'mine':''}" ${m.outgoing?`data-outgoing-nonce="${esc(m.nonce)}" data-send-state="${m.failed?'failed':'sending'}"`:`data-message-id="${m.id}"`}>${m.sender!==S.boot.user.id?avatar({...person(m.sender),name:m.name}):''}<div class="bubble-wrap"><div class="bubble ${m.kind==='sticker'?'sticker-bubble':''} ${m.kind==='deck'?'deck-bubble':m.kind==='text'?'text-bubble':''}">${messageBody(m)}</div><div class="reaction-host">${reactionHTML(m)}</div><div class="message-meta">${showSenderNames&&m.sender!==S.boot.user.id?'<span>'+esc(m.name)+'</span>':''}<time>${time(m.created)}</time>${status}</div></div></article>`;
}
function mergeMessages(id,messages){
 const merged=new Map((S.messages[id]||[]).map(m=>[m.id,m]));
 for(const m of messages){
 const versions=S.reactionVersions[id]||={},version=Number(m.reaction_version)||0,known=versions[m.id]||0;
 const preserve=S.reactions[id]?.[m.id]&&(version<known||!Object.hasOwn(m,'reactions'));
 if(!preserve&&Object.hasOwn(m,'reactions')){versions[m.id]=version;(S.reactions[id]||={})[m.id]=m.reactions;}
 merged.set(m.id,{...merged.get(m.id),...m,...(preserve?{reactions:S.reactions[id][m.id],reaction_version:known}:{})});const pending=S.outbox[m.nonce];if(m.sender===S.boot.user.id&&pending?.thread===id){delete S.outbox[m.nonce];if(S.sending[id]===m.nonce)delete S.sending[id];}}
 S.messages[id]=[...merged.values()].sort((a,b)=>a.id-b.id);
 drainMessages(id);
}
function renderOutbox(area){
 const entries=Object.values(S.outbox).filter(m=>m.thread===S.thread);
 let host=area.querySelector('.outgoing-messages');
 if(!entries.length){host?.remove();return;}
 if(!host){host=document.createElement('div');host.className='outgoing-messages';area.appendChild(host);}
 for(const m of entries){const old=host.querySelector(`[data-outgoing-nonce="${m.nonce}"]`);if(!old)host.insertAdjacentHTML('beforeend',messageHTML(m));else if(old.dataset.sendState!==(m.failed?'failed':'sending'))old.outerHTML=messageHTML(m);}
 host.querySelectorAll('[data-outgoing-nonce]').forEach(el=>{if(!S.outbox[el.dataset.outgoingNonce])el.remove();});
}
function markRead(){const area=$('.messages');if(S.tab!=='chats'||!area||document.hidden||!document.hasFocus()||area.scrollHeight-area.scrollTop-area.clientHeight>80)return;const last=(S.messages[S.thread]||[]).at(-1)?.id||0;if(last&&(S.read[S.thread]||0)<last){S.read[S.thread]=last;send('read',{thread:S.thread,last});}}
function markDelivered(id,messages){const last=Math.max(0,...messages.map(m=>m.id));if(last>(S.delivered[id]||0)){S.delivered[id]=last;send('delivered',{thread:id,last});}}

function renderMessages(first=false,earlier=false){
 const area=$('.messages');if(!area)return;
 const near=area.scrollHeight-area.scrollTop-area.clientHeight<75,oldHeight=area.scrollHeight,oldTop=area.scrollTop;
 const messages=S.messages[S.thread]||[],showSenderNames=thread()?.kind==='group';
 const renderMessage=message=>messageHTML(message,showSenderNames);
 const existing=[...area.querySelectorAll('[data-message-id]')].map(n=>Number(n.dataset.messageId));
 if(!first&&!earlier&&area.dataset.thread===S.thread&&messages.slice(0,existing.length).every((m,i)=>m.id===existing[i])){
  const outgoing=area.querySelector('.outgoing-messages');(outgoing||area).insertAdjacentHTML(outgoing?'beforebegin':'beforeend',messages.slice(existing.length).map(renderMessage).join(''));
 }else{
  area.innerHTML=(messages.length>=100?'<div class="older"><button class="link-btn" data-action="older">Earlier messages</button></div>':'')+messages.map(renderMessage).join('');area.dataset.thread=S.thread;
 }
 renderOutbox(area);refreshReactions();
 if(first||near&&!earlier)area.scrollTop=area.scrollHeight;else if(earlier)area.scrollTop=oldTop+(area.scrollHeight-oldHeight);else area.scrollTop=oldTop;
 updateReceipts();updatePeople();markRead();
}
function inbox(){return `<div class="inbox-page"><div class="row spread"><h2>Shared decks</h2>${btn('share','Share decks','','secondary')}</div>`+(S.boot.invites.map(i=>`<article class="inbox-row"><div class="row spread"><strong>${esc(i.summary.title)}</strong><span class="status">${esc(i.state)}</span></div><p>${i.sender===S.boot.user.id?'Sent to a study friend':'From '+esc(i.sender_name)} · ${i.summary.cards} cards</p>${i.recipient===S.boot.user.id&&i.state==='pending'?btn('preview','View invitation',`data-id="${i.id}"`,'secondary'):''}</article>`).join('')||'<p class="muted">No deck invitations yet.</p>')+'</div>';}
function selectThread(id){if($('.reaction-people'))closeModal();closeFloating();stopTyping();const old=$('#message-input');if(old&&S.thread)S.drafts[S.thread]=old.value;S.navSerial++;S.thread=id;S.tab='chats';S.picker=null;render();send('thread',{id});}
const chatPalettes={
 default:[['Violet','#6854dc'],['Periwinkle','#6178bc'],['Orchid','#9260a0'],['Dusty Rose','#ae657d'],['Sage','#6c8759']],
 ankiretro:[['Cornflower','#547ab6'],['Wisteria','#866eae'],['Rose','#b66c91'],['Powder Teal','#548884'],['Apricot','#c18562']],
 'ankiretro-baby-blue':[['Sky','#628fbc'],['Denim','#4d7399'],['Slate Blue','#647d9a'],['Periwinkle','#757fac'],['Blue Gray','#8291a6']],
 'ankiretro-maroon':[['Wine','#8f4662'],['Rosewood','#9b586c'],['Mauve','#87677d'],['Dusty Rose','#b47f8c'],['Plum','#77586f']],
 ankirise:[['Slate Teal','#4b7884'],['Ocean','#537fa0'],['Eucalyptus','#5c867a'],['Slate Blue','#6b7391'],['Clay','#b07b65']],
 ankimessage:[['Messages Blue','#0969d8'],['Kelly Green','#278652'],['Slate','#687b93'],['Indigo','#6c71b4'],['Muted Coral','#b46566']]
};
function chatPalette(){return chatPalettes[S.setup.appearance]||chatPalettes.default;}
const canMixChatTint=window.CSS?.supports('color','color-mix(in srgb, red, blue)');
function chatColorSwatches(selected){
 return [['Theme default','default'],...chatPalette()].map(([label,color])=>{
  const reset=color==='default',fill=reset?'var(--message-outgoing,var(--mine))':color;
  return `<button type="button" data-chat-color="${color}" aria-label="${label}" title="${label}" aria-pressed="${selected===color}" style="--swatch:${fill}">${reset?'↺':''}</button>`;
 }).join('');
}
function applyChatTheme(){
 const workspace=$('.workspace');if(!workspace)return;
 const color=S.chatThemes[S.thread],hasColor=/^#[0-9a-f]{6}$/i.test(color||'');
 workspace.classList.toggle('has-chat-color',hasColor);
 for(const key of ['--mine','--accent','--soft'])workspace.style.removeProperty(key);
 if(!hasColor)return;
 const rgb=[1,3,5].map(i=>parseInt(color.slice(i,i+2),16)),dark=!!S.setup.dark;
 const mix=(base,factor)=>'rgb('+rgb.map((x,i)=>Math.round(x*factor+base[i]*(1-factor))).join(',')+')';
 const tint=percent=>canMixChatTint
  ? `color-mix(in srgb, ${color} ${percent}%, var(--panel))`
  : mix(dark?[24,26,36]:[255,255,255],percent/100);
 workspace.style.setProperty('--mine',tint(dark?32:14));
 workspace.style.setProperty('--soft',tint(dark?25:10));
 // Blend toward the opposite text color to keep controls legible on both modes.
 workspace.style.setProperty('--accent',mix(dark?[255,255,255]:[0,0,0],dark?.4:.45));
}
function setChatTheme(color){
 if(!S.thread||color!=='default'&&!/^#[0-9a-f]{6}$/i.test(color))return;
 if(color==='default')delete S.chatThemes[S.thread];else S.chatThemes[S.thread]=color.toLowerCase();
 const custom=$('#custom-chat-color');if(custom)custom.value=S.chatThemes[S.thread]||chatPalette()[0][1];
 applyChatTheme();all('[data-chat-color]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.chatColor===(S.chatThemes[S.thread]||'default'))));
 send('chat_theme',{thread:S.thread,color});
}
function conversationOptions(){const t=thread();if(!t)return;
 modal(t.title,`<label class="option"><input id="chat-notifications" data-thread-id="${esc(t.id)}" type="checkbox" ${(S.setup.muted||[]).includes(t.id)?'':'checked'}><span>Message notifications<small>Mute this conversation without stopping messages or shared decks.</small></span></label><details class="chat-color-options"><summary>Chat color</summary><p class="tiny muted">Only changes this chat on your account.</p><div class="chat-color-swatches" data-appearance="${S.setup.appearance}">${chatColorSwatches(S.chatThemes[t.id]||'default')}<label class="chat-custom-color">Custom<input id="custom-chat-color" type="color" value="${esc(S.chatThemes[t.id]||chatPalette()[0][1])}" aria-label="Custom chat color"></label></div></details>`,btn('close-modal','Done','','secondary'));}
function closePicker(){$('.picker')?.remove();}
function picker(kind){if(S.picker===kind){S.picker=null;closePicker();return;}S.picker=kind;closePicker();const host=document.createElement('div');host.className='picker';host.innerHTML=kind==='emoji'?'<div class="emoji-grid">'+emojis.map(e=>`<button data-emoji="${e}" aria-label="${e}">${e}</button>`).join('')+'</div>':`<div class="picker-label">Little study buddies</div><div class="sticker-grid">${Object.entries(packs).map(([id,p])=>`<button data-sticker="${id}" title="${p[1]}" aria-label="${p[1]}">${stickerArt(id)}</button>`).join('')}</div><div id="saved-stickers"></div>${btn('upload-sticker','Add an image sticker','','secondary')}`;$('.composer-wrap').appendChild(host);if(kind==='sticker')send('stickers');}
function drainMessages(id){
 if(S.sending[id])return;
 const next=Object.values(S.outbox).find(m=>m.thread===id&&!m.failed&&!m.uploading);
 if(next){S.sending[id]=next.nonce;send('message',next.payload);}
}
function queueMessage(data){
 const payload={thread:S.thread,...data,nonce:nonce()};
 S.outbox[payload.nonce]={...payload,payload,sender:S.boot.user.id,name:S.boot.user.name,created:Date.now()/1000,outgoing:true,failed:false,attachment:payload.file?S.stickerLibrary.find(m=>m.id===payload.file):undefined};
 renderMessages();const area=$('.messages');if(area)area.scrollTop=area.scrollHeight;drainMessages(payload.thread);
}
function sendText(){const input=$('#message-input');if(!input?.value.trim())return;const text=input.value.trim();input.value='';stopTyping();input.style.height='auto';S.drafts[S.thread]='';queueMessage({kind:'text',text});}
const appearanceOptions=[
 ['default','Default'],
 ['ankiretro','AnkiRetro'],
 ['ankiretro-baby-blue','AnkiRetro · Baby Blue'],
 ['ankiretro-maroon','AnkiRetro · Maroon'],
 ['ankirise','AnkiRise'],
 ['ankimessage','AnkiMessage']
];
function applyAppearance(theme){
 const selected=appearanceOptions.some(([value])=>value===theme)?theme:'default';
 S.setup.appearance=selected;
 document.body.classList.toggle('ankiretro',selected.startsWith('ankiretro'));
 document.body.classList.toggle('ankiretro-baby-blue',selected==='ankiretro-baby-blue');
 document.body.classList.toggle('ankiretro-maroon',selected==='ankiretro-maroon');
 document.body.classList.toggle('ankirise',selected==='ankirise');
 document.body.classList.toggle('ankimessage',selected==='ankimessage');
 const swatches=$('.chat-color-swatches');
 if(swatches&&swatches.dataset.appearance!==selected){
  swatches.dataset.appearance=selected;
  const color=S.chatThemes[S.thread];
  swatches.querySelectorAll('[data-chat-color]').forEach(button=>button.remove());
  swatches.insertAdjacentHTML('afterbegin',chatColorSwatches(color||'default'));
  $('#custom-chat-color').value=color||chatPalette()[0][1];
 }
 filterConversations();
 const select=$('#appearance-theme');
 if(select)select.value=S.setup.appearance;
}
function accountModal(){
 const appearance=`<label class="field appearance-field">Appearance<select id="appearance-theme">
 ${appearanceOptions.map(([value,label])=>`<option value="${value}" ${S.setup.appearance===value?'selected':''}>${label}</option>`).join('')}
 </select></label>`;
 modal('Your AnkiLink','<div class="row">'+avatar(S.boot.user)+'<div><h3>'+esc(S.boot.user.name)+'</h3><span class="muted tiny">@'+esc(S.boot.user.username)+'</span></div></div><div class="row profile-actions">'+btn('avatar-set','Set profile picture','','secondary')+btn('avatar-remove','Remove',S.boot.user.avatar?'':'hidden','ghost')+'</div><div id="profile-progress" class="profile-progress" role="status" aria-live="polite"></div>'+appearance+'<label class="option"><input id="share-activity" type="checkbox" '+(S.setup.share_activity?'checked':'')+'><span>Share study activity<small>Shows only your current deck name. Otherwise friends see Online or Idle.</small></span></label><div class="section-label">Friend code</div><input class="friend-code-display" readonly value="'+esc(S.boot.user.code)+'"><div class="section-label">Server</div><p class="tiny muted">'+esc(S.setup.url)+'</p>',btn('logout','Sign out','','secondary'));updatePeople();profileProgress();}
function addFriend(){modal('Add a study friend','<p class="muted">Ask for their friend code.</p><label class="field">Friend code<input id="friend-code" autocomplete="off" placeholder="A1B2C3D4E5" maxlength="30"></label>',btn('close-modal','Cancel','','secondary')+btn('friend-send','Send request'));$('#friend-code').focus();}
function peopleCheckboxes(selected){return accepted().map(p=>`<label class="pill"><input type="checkbox" value="${p.id}" ${selected.has(p.id)?'checked':''} data-recipient>${esc(p.name)}</label>`).join('')||'<span class="muted tiny">Add a friend and accept their request first.</span>';}
function newGroup(){modal('A little study group','<label class="field">Group name<input id="group-name" maxlength="70" placeholder="The study corner"></label><div class="section-label">Invite your people</div><div class="recipient-grid">'+peopleCheckboxes(new Set())+'</div>',btn('close-modal','Cancel','','secondary')+btn('create-group','Create group'));}
function tree(){return S.catalog.map(d=>{
 const parts=d.name.split('::'),ancestors=parts.slice(0,-1).map((_,i)=>parts.slice(0,i+1).join('::'));
 if(ancestors.some(p=>!S.branches.has(p)))return '';
 const children=S.catalog.some(other=>other.name.startsWith(d.name+'::'));
 return `<div class="tree-row" style="padding-left:${(parts.length-1)*19}px"><button class="chevron ${children?'':'placeholder'} ${S.branches.has(d.name)?'open':''}" data-branch="${esc(d.name)}" ${children?'':'disabled'} aria-label="Expand ${esc(d.name)}" aria-expanded="${S.branches.has(d.name)}"></button><label><input type="checkbox" data-deck="${d.id}" ${S.selected.has(d.id)?'checked':''}>${esc(parts.at(-1))}</label><span class="kind">${d.filtered?'Filtered':''}</span></div>`;
 }).join('');}
function share(){const active=thread();S.shareTarget=active?{id:active.id,kind:active.kind,title:active.title,members:active.members}:null;modal('Share decks','<p class="muted">Your decks will appear here.</p>',btn('close-modal','Close','','secondary'));request('catalog');}
function shareModal(rows){
 S.catalog=rows;S.selected=new Set();S.branches=new Set();S.shareNonce=nonce();const active=S.shareTarget===undefined?thread():S.shareTarget;S.shareTarget=active;S.recipients=new Set(active?.members.filter(u=>u.id!==S.boot.user.id).map(u=>u.id)||[]);
 const target=active?.kind==='group'?`<div class="share-destination" data-share-group="${esc(active.id)}"><div><strong>${esc(active.title)}</strong><small>Group chat · Each member can accept or decline.</small></div></div>`:`<div class="recipient-grid">${peopleCheckboxes(S.recipients)}</div>`;
 modal('Send a little knowledge',`<div class="section-label">To</div>${target}<div class="section-label">Decks & subdecks</div><div class="tree" id="deck-tree">${tree()}</div><label class="field" style="margin-top:12px">Anki search <span class="muted">Optional</span><input id="share-search" placeholder="Limit the selected cards"></label><div class="section-label">Include</div><label class="option"><input id="share-settings" type="checkbox" checked><span>My deck setup<small>Presets, per-deck limits, desired retention and filtered-deck options.</small></span></label><label class="option"><input id="share-progress" type="checkbox"><span>My learning progress<small>Leave off to send fresh cards.</small></span></label>`,btn('close-modal','Cancel','','secondary')+btn('share-send','Send decks'),true);
}
function importDestination(data,invitation){
 const merge=data.merge!==false;
 return `<label class="option"><input id="merge-decks" type="checkbox" ${merge?'checked':''}><span>Merge into existing decks<small>Reuses matching full deck paths and adds new cards and lessons.</small></span></label><label class="field" id="destination-field" ${merge?'hidden':''}>Separate destination folder<input id="destination" value="${esc(data.destination||'From '+invitation.sender_name)}" maxlength="700"></label>`;
}
function previewInvite(data){
 const m=data.manifest,i=data.invitation;if(i.thread&&S.removedGroups[i.thread]!==undefined)return;S.preview=data;
 const conflicts=data.conflicts||[];
 modal(m.summary.title,`<div class="muted tiny">From ${esc(i.sender_name)}</div><div class="summary-grid"><div><strong>${data.new_cards}</strong><span>new cards</span></div><div><strong>${data.updated_notes}</strong><span>updated notes</span></div><div><strong>${data.existing_cards}</strong><span>existing cards</span></div></div>${importDestination(data,i)}<div class="section-label">Your setup</div>${m.with_settings?`<label class="option"><input id="receive-settings" type="checkbox" ${data.existing_cards?'':'checked'}><span>Apply the sender’s deck setup<small>Uses separate presets for the received decks.</small></span></label>`:''}${m.with_progress?'<label class="option"><input id="receive-progress" type="checkbox"><span>Use the sender’s learning progress</span></label>':''}<label class="option"><input id="receive-reset" type="checkbox"><span>Reset received cards to New<small>Includes matching cards already in your collection. Other cards are untouched.</small></span></label>${data.needs_fsrs?'<label class="option"><input id="enable-fsrs" type="checkbox"><span>Enable FSRS for this Anki profile<small>Required only if applying an FSRS setup. This is an Anki-wide setting.</small></span></label>':''}${m.filters.length?'<label class="option"><input id="build-filters" type="checkbox" checked><span>Build the filtered practice decks<small>Rebuilding starts a new practice round. Shared cards can occupy one filtered deck at a time.</small></span></label>':''}${conflicts.length?`<div class="section-label">${conflicts.length} local edit${conflicts.length===1?'':'s'}</div><p class="tiny muted">Your versions stay unless you choose to replace them.</p>${conflicts.slice(0,10).map(c=>`<div class="conflict"><div class="conflict-columns"><div><strong>Your version</strong><p>${esc(c.local.join('\n'))}</p></div><div><strong>Received</strong><p>${esc(c.received.join('\n'))}</p></div></div></div>`).join('')}<label class="option"><input id="replace-conflicts" type="checkbox"><span>Replace these local edits with the received versions</span></label>`:''}`,btn('reject','Decline',`data-id="${i.id}"`,'ghost')+btn('close-modal','Later','','secondary')+btn('accept','Accept & import',`data-id="${i.id}"`),true);
 if(i.thread&&$('.modal'))$('.modal').dataset.groupThread=i.thread;
}
document.addEventListener('submit',e=>{if(e.target.id!=='auth-form')return;e.preventDefault();busy(true);$('.auth-error').textContent='';send('auth',{url:$('#server-url').value,username:$('#auth-user').value,password:$('#auth-password').value,name:$('#auth-name')?.value,join_code:$('#join-code')?.value,register:S.register,remember:$('#remember')?.checked});});
// Dismiss before outside navigation, but leave clicks inside the overlay intact.
function dismissFloating(e){const f=S.floating;if(f&&!f.host.contains(e.target)&&!f.trigger.contains(e.target))closeFloating(true);}
document.addEventListener('pointerdown',dismissFloating,true);
document.addEventListener('click',dismissFloating,true);
document.addEventListener('scroll',()=>closeFloating(),true);
window.addEventListener('resize',()=>closeFloating());
document.addEventListener('click',e=>{
 const t=e.target.closest('button');if(!t)return;
 if(t.disabled)return;
 if(t.dataset.tab){closeFloating();stopTyping();S.navSerial++;S.tab=t.dataset.tab;render();send('refresh');return;}
 if(t.dataset.thread){selectThread(t.dataset.thread);return;}
 if(t.dataset.friendAccept||t.dataset.friendReject){request('friend_decide',{user:t.dataset.friendAccept||t.dataset.friendReject,accept:!!t.dataset.friendAccept});return;}
 if(t.dataset.branch){S.branches.has(t.dataset.branch)?S.branches.delete(t.dataset.branch):S.branches.add(t.dataset.branch);$('#deck-tree').innerHTML=tree();return;}
 if(t.dataset.emoji){const input=$('#message-input'),a=input.selectionStart,b=input.selectionEnd;input.value=input.value.slice(0,a)+t.dataset.emoji+input.value.slice(b);input.focus();input.setSelectionRange(a+t.dataset.emoji.length,a+t.dataset.emoji.length);S.drafts[S.thread]=input.value;return;}
 if(t.dataset.memberMenu){memberMenu(t);return;}
 if(t.dataset.chatColor){setChatTheme(t.dataset.chatColor);return;}
 if(t.dataset.reactMessage){reactionPicker(t.dataset.reactMessage);return;}
 if(t.dataset.reactionPeople){reactionPeople(t.dataset.reactionMessage,t.dataset.reactionPeople);return;}
 if(t.dataset.reactionChoice){chooseReaction(t.dataset.reactionMessage,t.dataset.reactionChoice);return;}
 if(t.dataset.retryMessage){const m=S.outbox[t.dataset.retryMessage];if(m?.failed){m.failed=false;renderMessages();if(m.uploading)send('retry_attachment',{nonce:m.nonce});else drainMessages(m.thread);}return;}
 if(t.dataset.sticker){queueMessage({kind:'sticker',text:t.dataset.sticker});closePicker();S.picker=null;return;}
 if(t.dataset.savedSticker){queueMessage({kind:'sticker',file:t.dataset.savedSticker,text:''});closePicker();S.picker=null;return;}
 const action=t.dataset.action;
 switch(action){
 case 'startup-retry':readyTries=0;S.connected=false;connect();break;
 case 'auth-switch':S.register=!S.register;S.setup.url=$('#server-url').value;auth();break;
 case 'back-chats':selectThread(null);break;
 case 'conversation-options':conversationOptions();break;
 case 'close-modal':closeModal();break;
 case 'add-friend':addFriend();break;
 case 'friend-send':request('friend_request',{code:$('#friend-code').value});break;
 case 'direct':request('direct',{user:t.dataset.user});break;
 case 'new-group':newGroup();break;
 case 'create-group':request('group',{title:$('#group-name').value,users:[...all('[data-recipient]:checked')].map(x=>x.value)});break;
 case 'account':accountModal();break;
 case 'group-details':groupDetails();break;
 case 'group-add':groupAdd();break;
 case 'group-add-confirm':{const users=[...all('[data-group-recipient]:checked')].map(x=>x.value),id=$('.modal')?.dataset.groupThread,t=S.boot.threads.find(t=>t.id===id);if(!users.length||!t||users.length+t.members.length>31){$('.modal-error').textContent='Choose friends within the 31 member limit.';break;}request('group_add',{thread:id,users});break;}
 case 'group-admin':closeFloating(true);request('group_admin',{thread:S.thread,user:t.dataset.user,admin:t.dataset.admin==='true'});break;
 case 'group-remove':closeFloating(true);groupConfirm('group_remove',t.dataset.user);break;
 case 'group-leave':groupConfirm('group_leave');break;
 case 'group-remove-confirm':request('group_remove',{thread:t.dataset.threadId,user:t.dataset.user});break;
 case 'group-leave-confirm':request('group_leave',{thread:t.dataset.threadId});break;
 case 'group-photo-set':beginGroupPhoto();break;
 case 'group-photo-remove':beginGroupPhoto(true);break;
 case 'group-photo-retry':{const host=$('#group-photo-progress'),id=host?.dataset.thread,edit=S.groupEdits[id];if(edit?.phase==='failed'){edit.phase=edit.remove?'saving':'preparing';groupPhotoProgress();send('retry_group_photo',{thread:id,request:edit.request});}break;}
 case 'avatar-set':beginAvatar();break;
 case 'avatar-remove':beginAvatar(true);break;
 case 'avatar-retry':if(S.avatarEdit?.phase==='failed'){S.avatarEdit.phase=S.avatarEdit.remove?'saving':'preparing';profileProgress();send('retry_avatar',{request:S.avatarEdit.request});}break;
 case 'logout':closeModal();send('logout');break;
 case 'send':sendText();break;
 case 'emoji':picker('emoji');break;
 case 'sticker':picker('sticker');break;
 case 'image':send('attach',{thread:S.thread,nonce:nonce()});toast('Choose an image to send.');break;
 case 'upload-sticker':send('attach',{thread:S.thread,sticker:true,nonce:nonce()});closePicker();S.picker=null;break;
 case 'share':share();break;
 case 'share-send':request('share',{decks:[...S.selected],...(S.shareTarget?.kind==='group'?{thread:S.shareTarget.id}:{recipients:[...all('[data-recipient]:checked')].map(x=>x.value)}),settings:$('#share-settings').checked,progress:$('#share-progress').checked,search:$('#share-search').value,nonce:S.shareNonce});break;
 case 'preview':modal('Shared decks','',btn('close-modal','Close','','secondary'));request('preview_invite',{id:t.dataset.id});break;
 case 'reject':request('reject_invite',{id:t.dataset.id});break;
 case 'accept':request('accept_invite',{id:t.dataset.id,options:{merge:$('#merge-decks')?.checked===true,destination:$('#destination').value,settings:$('#receive-settings')?.checked||false,progress:$('#receive-progress')?.checked||false,reset:$('#receive-reset').checked,enable_fsrs:$('#enable-fsrs')?.checked||false,replace_conflicts:$('#replace-conflicts')?.checked||false,build_filters:$('#build-filters')?.checked??true}});break;
 case 'older':send('thread',{id:S.thread,before:(S.messages[S.thread]||[])[0]?.id||0});break;
 }
});
document.addEventListener('click',e=>{const image=e.target.closest('[data-photo]');if(image&&!image.closest('[data-saved-sticker]')){const shade=document.createElement('div');shade.className='shade photo-viewer';const img=document.createElement('img');img.src=S.images[image.dataset.photo];shade.appendChild(img);const close=document.createElement('button');close.className='icon photo-close';close.textContent='×';close.setAttribute('aria-label','Close image');shade.appendChild(close);close.onclick=()=>shade.remove();shade.onclick=event=>{if(event.target===shade)shade.remove();};modals.appendChild(shade);}});
document.addEventListener('change',e=>{if(e.target.id==='appearance-theme')send('appearance',{theme:e.target.value});if(e.target.id==='custom-chat-color')setChatTheme(e.target.value);if(e.target.id==='chat-notifications')send('mute_thread',{id:e.target.dataset.threadId,muted:!e.target.checked});if(e.target.id==='share-activity'){S.setup.share_activity=e.target.checked;send('activity',{enabled:e.target.checked});}if(e.target.id==='merge-decks')$('#destination-field').hidden=e.target.checked;if(e.target.dataset.deck){e.target.checked?S.selected.add(e.target.dataset.deck):S.selected.delete(e.target.dataset.deck);}if(e.target.id==='receive-reset'&&e.target.checked&&$('#receive-progress'))$('#receive-progress').checked=false;if(e.target.id==='receive-progress'&&e.target.checked)$('#receive-reset').checked=false;});
document.addEventListener('input',e=>{if(e.target.id==='conversation-search'){S.chatSearch=e.target.value;filterConversations();}if(e.target.id==='message-input'){typingInput();S.drafts[S.thread]=e.target.value;e.target.style.height='auto';e.target.style.height=Math.min(150,e.target.scrollHeight)+'px';}});
document.addEventListener('focusin',e=>{const pane=$('.modal');if(pane&&!pane.contains(e.target)&&!S.floating?.host.contains(e.target))pane.focus({preventScroll:true});});
document.addEventListener('keydown',e=>{
 const floating=S.floating;
 if(floating&&floating.host.contains(document.activeElement)){
  const controls=[...floating.host.querySelectorAll('button:not(:disabled)')],index=controls.indexOf(document.activeElement);
  if(['ArrowDown','ArrowRight','ArrowUp','ArrowLeft','Home','End'].includes(e.key)){
   e.preventDefault();const next=e.key==='Home'?0:e.key==='End'?controls.length-1:(index+(['ArrowUp','ArrowLeft'].includes(e.key)?-1:1)+controls.length)%controls.length;controls[next]?.focus();return;
  }
  if(e.key==='Tab'){e.preventDefault();closeFloating(true);return;}
 }
 const pane=$('.modal');if(!pane||e.key!=='Tab')return;
 const controls=[...pane.querySelectorAll('button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled),a[href]')].filter(el=>!el.hidden&&!el.closest('[hidden]'));
 if(!controls.length){e.preventDefault();pane.focus();return;}
 const first=controls[0],last=controls.at(-1);
 if(e.shiftKey&&(document.activeElement===first||document.activeElement===pane)){e.preventDefault();last.focus();}
 else if(!e.shiftKey&&(document.activeElement===last||document.activeElement===pane)){e.preventDefault();first.focus();}
});
document.addEventListener('keydown',e=>{if(e.key==='Escape'){if(S.floating){e.preventDefault();closeFloating(true);}else if($('.photo-viewer'))$('.photo-viewer').remove();else if($('.picker')){closePicker();S.picker=null;}else closeModal();}if(e.target.id==='message-input'&&e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();if(!e.repeat)sendText();}});
document.addEventListener('paste',e=>{if(e.target.id==='message-input'&&[...(e.clipboardData?.items||[])].some(i=>i.type.startsWith('image/'))){e.preventDefault();send('paste_image',{thread:S.thread,nonce:nonce()});}});
window.ankiLink={state:S,receive(event,data){
 if(!S.boot&&['messages','sent','status','receipts','typing'].includes(event)){(S.waiting||(S.waiting=[])).push([event,data]);return;}
 switch(event){
 case 'operation':finishOperation(data);break;
 case 'open_thread':if(S.removedGroups[data.id]===undefined){closeModal();selectThread(data.id);}break;
 case 'notification_settings':S.setup.muted=data.muted||[];if($('#chat-notifications'))$('#chat-notifications').checked=!S.setup.muted.includes($('#chat-notifications').dataset.threadId);break;
 case 'refresh_state':break; // Routine synchronization stays silent; tracked actions have their own progress.
 case 'setup':{S.connected=true;const changed=!!S.setup.dark!==!!data.dark;S.setup=data;document.body.classList.toggle('dark',!!data.dark);applyAppearance(data.appearance);if(!S.boot)auth();else if(changed)render();break;}
 case 'authenticated':S.setup.url=$('#server-url')?.value||S.setup.url;busy(false);closeModal();app.innerHTML=retroFrame('<div class="loading"><div class="mark">a<span>↗</span></div><p>Finding your people…</p></div>');break;
 case 'signed_out':S.chatSearch='';S.boot=null;S.thread=null;S.messages={};S.drafts={};S.outbox={};S.sending={};S.read={};S.images={};S.blobRequests.clear();S.people={};S.receipts={};S.typing={};S.delivered={};S.waiting=[];S.avatarEdit=null;S.avatarSaved=null;S.operations={};S.groupPhotos={};S.groupEdits={};S.removedGroups={};S.reactions={};S.reactionPending={};S.chatThemes={};S.reactionVersions={};S.revokedFiles.clear();S.revokedThreadFiles={};S.legacyRemovals={};S.membershipConfirmations={};S.deckInvites={};delete S.shareTarget;closeModal();stopTyping();auth();break;
 case 'chat_themes':S.chatThemes=data||{};applyChatTheme();break;
 case 'bootstrap':{
  S.chatThemes=data.chat_themes||S.chatThemes;applyChatTheme();
  const old=S.boot;
  for(const t of data.threads)if(S.removedGroups[t.id]!==undefined){
   const legacy=Object.prototype.hasOwnProperty.call(S.legacyRemovals,t.id),epoch=S.legacyRemovals[t.id],confirmed=S.membershipConfirmations[t.id];
   const fresh=legacy?((epoch!==null&&data._membership_epoch!==undefined&&data._membership_epoch>=epoch)||(confirmed!==undefined&&(t.membership_version||0)>=confirmed)):(t.membership_version||0)>S.removedGroups[t.id];
   if(fresh){delete S.removedGroups[t.id];delete S.legacyRemovals[t.id];delete S.membershipConfirmations[t.id];for(const fid of S.revokedThreadFiles[t.id]||[])S.revokedFiles.delete(fid);delete S.revokedThreadFiles[t.id];}
  }
  const visible=data.threads.filter(t=>S.removedGroups[t.id]===undefined);
  if(old)for(const t of [...old.threads])if(t.kind==='group'&&!visible.some(n=>n.id===t.id))removeGroup(t.id);
  S.boot={...data,user:protectProfile(data.user),threads:visible.map(t=>{const previous=old?.threads.find(p=>p.id===t.id);return keepGroupPhoto(previous&&(previous.membership_version||0)>(t.membership_version||0)?{...t,owner:previous.owner,members:previous.members,membership_version:previous.membership_version}:t);})};rememberInvites(data.invites);for(const value of [S.boot.user,...data.friends,...data.threads.flatMap(t=>t.members)]){const p=protectProfile(value);S.people[p.id]={...S.people[p.id],...p};}
  if(!old||!$('.layout')){render();const queued=S.waiting||[];S.waiting=[];for(const [event,value] of queued)window.ankiLink.receive(event,value);break;}
  refreshSidebar();
  if(S.tab==='chats'&&thread()&&!$('#message-input'))render();
  if(S.tab==='inbox')$('.workspace').innerHTML=inbox();
  else all('[data-message-id] .deck-bubble').forEach(el=>{const id=Number(el.closest('[data-message-id]').dataset.messageId),m=(S.messages[S.thread]||[]).find(x=>x.id===id);if(m){const html=messageBody(m);if(el.innerHTML!==html)el.innerHTML=html;}});
  updatePeople();updateReceipts();typingView();refreshGroupDetails();refreshReactions();operationView();if($('.connection'))$('.connection').hidden=true;
  break;
 }
 case 'messages':{
  if(S.removedGroups[data.thread]!==undefined)break;
  rememberInvites(data.invites);
  const old=S.messages[data.thread]||[];mergeMessages(data.thread,data.messages);markDelivered(data.thread,data.messages);receiveStatus(data);
  if(data.thread===S.thread&&S.tab!=='inbox')renderMessages(!old.length,!!data.earlier);break;
 }
 case 'status':receiveStatus(data);break;
 case 'reaction_updated':reactionChanged(data);break;
 case 'group_result':groupMembership(data);break;
 case 'group_removed':if(S.boot)removeGroup(data.thread,data.membership_version,data._membership_epoch);break;
 case 'receipts':updateReceipts(data.receipts);break;
 case 'typing':(S.typing[data.thread]||(S.typing[data.thread]={}))[data.uid]=data;typingView();break;
 case 'appearance':applyAppearance(data);break;
 case 'activity_setting':S.setup.share_activity=data.enabled;break;
 case 'profile_progress':{
  if(!S.boot||data.uid!==S.boot.user.id||S.avatarEdit&&S.avatarEdit.request!==data.request)return;
  S.avatarEdit={...S.avatarEdit,...data};if(data.phase==='failed'||data.phase==='cancelled')delete S.avatarEdit.preview;
  updatePeople();profileProgress();break;
 }
 case 'profile_updated':{
  if(!S.boot)break;const user=data.user||data;if(data.request&&S.avatarEdit?.request!==data.request)break;
  S.boot.user=user;S.people[user.id]={...S.people[user.id],...user};S.avatarSaved={uid:user.id,avatar:user.avatar||null,until:Date.now()+15000};
  S.avatarEdit={request:data.request,uid:user.id,phase:'saved',remove:!!data.remove};updatePeople();profileProgress();break;
 }
 case 'group_updated':if(S.boot)groupChanged(data);break;
 case 'group_photo_progress':{
  if(!S.boot)break;const edit=S.groupEdits[data.thread];if(edit&&edit.request!==data.request)break;
  S.groupEdits[data.thread]={...edit,...data};if(['failed','cancelled'].includes(data.phase))delete S.groupEdits[data.thread].preview;
  updatePeople();groupPhotoProgress();break;
 }
 case 'group_photo_saved':{
  const edit=S.groupEdits[data.thread];if(!S.boot||edit?.request!==data.request)break;
  S.groupEdits[data.thread]={...edit,phase:'saved'};delete S.groupEdits[data.thread].preview;groupChanged(data);
  if($('#group-photo-progress')?.dataset.thread!==data.thread)toast(edit.remove?'Group photo removed.':'Group photo saved.');break;
 }
 case 'live_connected':if($('.connection'))$('.connection').hidden=true;break;
 case 'attachment_pending':{S.images[data.attachment.id]=data.src;S.outbox[data.nonce]={...data,sender:S.boot.user.id,name:S.boot.user.name,created:Date.now()/1000,outgoing:true,uploading:true,failed:false};if(data.thread===S.thread)renderMessages();break;}
 case 'thread_created':closeModal();selectThread(data.thread);break;
 case 'sent':{const m=S.outbox[data.nonce];if(m&&Number.isSafeInteger(data.id)&&data.id>0){mergeMessages(m.thread,[data.message||{...m,id:data.id,outgoing:false,failed:false}]);if(m.thread===S.thread)renderMessages();}break;}
 case 'message_failed':{const m=S.outbox[data.nonce];if(m&&m.thread===data.thread){m.failed=true;if(S.sending[m.thread]===m.nonce)delete S.sending[m.thread];if(m.thread===S.thread)renderMessages();toast(data.message);drainMessages(m.thread);}break;}
 case 'blob':if(S.revokedFiles.has(data.id))break;S.images[data.id]=data.src;S.blobRequests.delete(data.id);all(`[data-image-pending="${data.id}"]`).forEach(el=>{const img=document.createElement('img');img.className='message-photo';img.dataset.photo=data.id;img.alt='Shared image';img.src=data.src;el.replaceWith(img);});updatePeople();break;
 case 'attachment_error':S.blobRequests.delete(data.id);all(`[data-image-pending="${data.id}"]`).forEach(el=>el.textContent='Image unavailable');break;
 case 'sticker_library':S.stickerLibrary=data;if($('#saved-stickers'))$('#saved-stickers').innerHTML='<div class="picker-label" style="margin-top:13px">Your stickers</div><div class="sticker-grid">'+data.map(meta=>`<button data-saved-sticker="${meta.id}">${photo(meta,true)}</button>`).join('')+'</div>';break;
 case 'catalog':shareModal(data);break;
 case 'shared':busy(false);closeModal();toast('Deck invitations sent.');break;
 case 'invite_preview':busy(false);previewInvite(data);break;
 case 'imported':busy(false);closeModal();toast(`${data.cards} shared cards are ready in Anki.`);break;
 case 'notice':busy(false);closeModal();toast(data);break;
 case 'receipt_pending':toast('Cards imported. The acceptance receipt will retry when you reconnect.');break;
 case 'cancelled':break;
 case 'connection_error':if($('.connection')){$('.connection').hidden=false;$('.connection').textContent='Reconnecting…';}else if($('.auth-error'))$('.auth-error').textContent=data;break;
 case 'error':busy(false);if($('.modal-error'))$('.modal-error').textContent=data;else if($('.auth-error'))$('.auth-error').textContent=data;else toast(data);break;
 }
}};
let readyTries=0;
function connect(){
 if(S.connected)return;
 if(readyTries++>=60){app.innerHTML='<div class="loading"><div class="mark">a<span>↗</span></div><h2>AnkiLink could not connect to Anki.</h2><p>Try opening the connection again.</p>'+btn('startup-retry','Retry')+'</div>';return;}
 if(typeof pycmd==='function')send('ready');
 setTimeout(connect,250);
}
connect();
window.addEventListener('focus',markRead);window.addEventListener('blur',stopTyping);document.addEventListener('visibilitychange',()=>{if(document.hidden)stopTyping();else markRead();});document.addEventListener('scroll',e=>{if(e.target.matches?.('.messages'))markRead();},true);setInterval(()=>{typingView();updatePeople();},750);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initAnkiLink,{once:true});else initAnkiLink();
})();
