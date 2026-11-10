"""AnkiLink private relay. Python 3.11+, standard library only.

Run behind HTTPS for internet use. This service never opens an Anki collection.
"""
from __future__ import annotations
import argparse
import base64
import struct
import hashlib
import hmac
import json
import mimetypes
import os
from pathlib import Path
import re
import secrets
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

VERSION='1.5.2'
SYSTEM_NONCE_PREFIX='system:'
REACTIONS=('👍','❤️','😂','😮','😢','😡','🎉')
SCHEMA='''
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,username TEXT NOT NULL UNIQUE,name TEXT NOT NULL,code TEXT NOT NULL UNIQUE,salt TEXT NOT NULL,password TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,uid TEXT NOT NULL REFERENCES users(id),expires REAL NOT NULL);
CREATE TABLE IF NOT EXISTS friends(a TEXT NOT NULL REFERENCES users(id),b TEXT NOT NULL REFERENCES users(id),requester TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',PRIMARY KEY(a,b));
CREATE TABLE IF NOT EXISTS threads(id TEXT PRIMARY KEY,title TEXT NOT NULL,kind TEXT NOT NULL,direct_key TEXT UNIQUE,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS members(thread TEXT NOT NULL REFERENCES threads(id),uid TEXT NOT NULL REFERENCES users(id),seen INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(thread,uid));
CREATE TABLE IF NOT EXISTS files(id TEXT PRIMARY KEY,owner TEXT NOT NULL REFERENCES users(id),name TEXT NOT NULL,mime TEXT NOT NULL,size INTEGER NOT NULL,sha256 TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS invites(id TEXT PRIMARY KEY,sender TEXT NOT NULL REFERENCES users(id),recipient TEXT NOT NULL REFERENCES users(id),thread TEXT NOT NULL REFERENCES threads(id),file TEXT NOT NULL REFERENCES files(id),summary TEXT NOT NULL,state TEXT NOT NULL DEFAULT 'pending',result TEXT NOT NULL DEFAULT '{}',nonce TEXT NOT NULL,created REAL NOT NULL,UNIQUE(sender,recipient,nonce));
CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT,thread TEXT NOT NULL REFERENCES threads(id),sender TEXT NOT NULL REFERENCES users(id),kind TEXT NOT NULL,text TEXT NOT NULL DEFAULT '',file TEXT REFERENCES files(id),invite TEXT REFERENCES invites(id),nonce TEXT NOT NULL,created REAL NOT NULL,UNIQUE(thread,sender,nonce));
CREATE INDEX IF NOT EXISTS message_thread ON messages(thread,id);
'''

class Problem(Exception):
    def __init__(self,message,status=400):super().__init__(message);self.status=status

def text(value,maximum=8000):
    if not isinstance(value,str) or len(value)>maximum:raise Problem('Invalid text length.')
    return value.strip()

def identifier():return secrets.token_hex(16)
def password_hash(password,salt):return hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),220000).hex()
def public(row):return {key:row[key] for key in ('id','username','name','code')}

class Relay:
    def __init__(self,directory,join_code='',max_users=100,max_file_mb=250):
        self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=True)
        self.blobs=self.directory/'files';self.blobs.mkdir(exist_ok=True)
        self.db_path=self.directory/'relay.sqlite3';self.lock=threading.RLock()
        self.join_code=join_code;self.max_users=max_users;self.max_file=max_file_mb*1024*1024;self.hits={};self.peers=set()
        with self.connect() as db:
            db.executescript(SCHEMA)
            # Bounded, additive startup migration for existing standalone installs.
            for table,column,decl in [('users','avatar','TEXT'),('members','delivered','INTEGER NOT NULL DEFAULT 0'),('members','typing_until','REAL NOT NULL DEFAULT 0'),('members','admin','INTEGER NOT NULL DEFAULT 0'),('threads','avatar','TEXT REFERENCES files(id)'),('threads','avatar_version','INTEGER NOT NULL DEFAULT 0'),('threads','owner','TEXT REFERENCES users(id)'),('threads','membership_version','INTEGER NOT NULL DEFAULT 0')]:
                if column not in {r[1] for r in db.execute('PRAGMA table_info('+table+')')}:db.execute('ALTER TABLE '+table+' ADD COLUMN '+column+' '+decl)
            db.execute("CREATE TABLE IF NOT EXISTS presence(session TEXT PRIMARY KEY,uid TEXT NOT NULL REFERENCES users(id),status TEXT NOT NULL DEFAULT 'online',deck TEXT NOT NULL DEFAULT '',updated REAL NOT NULL)")
            db.execute('CREATE INDEX IF NOT EXISTS presence_user ON presence(uid,updated)')
            db.execute('CREATE TABLE IF NOT EXISTS reactions(message INTEGER NOT NULL REFERENCES messages(id),uid TEXT NOT NULL REFERENCES users(id),emoji TEXT NOT NULL,PRIMARY KEY(message,uid))')
            db.execute('CREATE TABLE IF NOT EXISTS reaction_updates(message INTEGER PRIMARY KEY REFERENCES messages(id),updated REAL NOT NULL)')
    def connect(self):
        db=sqlite3.connect(self.db_path,timeout=20);db.row_factory=sqlite3.Row;db.execute('PRAGMA foreign_keys=ON');return db
    def limited(self,key,count,period=60):
        now=time.time()
        with self.lock:
            values=[value for value in self.hits.get(key,[]) if value>now-period]
            if len(values)>=count:raise Problem('Please wait before trying again.',429)
            self.hits[key]=values+[now]
            if len(self.hits)>2000:self.hits={k:v for k,v in self.hits.items() if v and v[-1]>now-600}
    def user(self,token):
        with self.connect() as db:
            row=db.execute('SELECT uid FROM sessions WHERE token=? AND expires>?',(hashlib.sha256(token.encode()).hexdigest(),time.time())).fetchone()
            if not row:raise Problem('Please sign in again.',401)
            return row['uid']
    def authenticate(self,data,register=False,ip='local'):
        self.limited(('auth',ip),20,600)
        username=text(data.get('username',''),32).lower();password=data.get('password','')
        if not re.fullmatch(r'[a-z0-9_]{3,32}',username):raise Problem('Use 3–32 letters, numbers or underscores for your username.')
        if not isinstance(password,str) or not 10<=len(password)<=200:raise Problem('Use a password with at least 10 characters.')
        with self.lock,self.connect() as db:
            if register:
                if self.join_code and not hmac.compare_digest(str(data.get('join_code','')),self.join_code):raise Problem('The server invitation code is incorrect.',403)
                if db.execute('SELECT count(*) FROM users').fetchone()[0]>=self.max_users:raise Problem('This server has reached its account limit.',403)
                name=text(data.get('name',username),60) or username;salt=secrets.token_hex(16)
                try:db.execute('INSERT INTO users(id,username,name,code,salt,password,created) VALUES(?,?,?,?,?,?,?)',(identifier(),username,name,secrets.token_hex(5).upper(),salt,password_hash(password,salt),time.time()))
                except sqlite3.IntegrityError:raise Problem('That username is already in use.',409)
            row=db.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone()
            # Hash a dummy password too, so missing users do not have a fast path.
            check=password_hash(password,row['salt'] if row else '00'*16)
            if not row or not hmac.compare_digest(row['password'],check):raise Problem('Username or password is incorrect.',401)
            token=secrets.token_urlsafe(40);expires=time.time()+14*86400
            db.execute('DELETE FROM sessions WHERE expires<?',(time.time(),))
            db.execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),row['id'],expires))
            return {'user':self.person(db,row),'token':token,'expires':expires,'server_version':VERSION}
    def member(self,db,thread,uid):
        if not db.execute('SELECT 1 FROM members WHERE thread=? AND uid=?',(thread,uid)).fetchone():raise Problem('Conversation not found.',404)
    def group_state(self,db,thread):
        row=db.execute("SELECT owner,membership_version FROM threads WHERE id=? AND kind='group'",(thread,)).fetchone()
        if not row:raise Problem('Group not found.',404)
        members=[]
        for p in db.execute('SELECT u.*,m.admin FROM members m JOIN users u ON u.id=m.uid WHERE m.thread=? ORDER BY u.id',(thread,)):
            item=self.person(db,p);item['admin']=bool(p['admin'] or p['id']==row['owner']);members.append(item)
        return {'thread':thread,'owner':row['owner'],'membership_version':row['membership_version'],'members':members}
    def group_notice(self,db,thread,actor,body):
        # Server-only nonce space; callers insert before removing the actor and
        # within the same membership transaction, so history never lies.
        db.execute('INSERT INTO messages(thread,sender,kind,text,nonce,created) VALUES(?,?,?,?,?,?)',(thread,actor,'system',body,SYSTEM_NONCE_PREFIX+identifier(),time.time()))
    def reaction_summary(self,db,thread,message):
        groups={};version=0
        for row in db.execute('SELECT COALESCE(u.updated,0) AS reaction_version,r.emoji,r.uid FROM messages m LEFT JOIN reaction_updates u ON u.message=m.id LEFT JOIN reactions r ON r.message=m.id WHERE m.id=? ORDER BY r.uid',(message,)):
            version=row['reaction_version']
            if row['emoji'] is not None:groups.setdefault(row['emoji'],[]).append(row['uid'])
        return {'thread':thread,'message':message,'reaction_version':version,'reactions':[{'emoji':emoji,'count':len(groups[emoji]),'users':groups[emoji]} for emoji in REACTIONS if emoji in groups]}
    def decorate_reactions(self,db,messages):
        for message in messages:
            summary=self.reaction_summary(db,message['thread'],message['id']);message['reactions']=summary['reactions'];message['reaction_version']=summary['reaction_version']
        return messages
    def friends(self,db,a,b):
        x,y=sorted((a,b))
        return bool(a!=b and db.execute("SELECT 1 FROM friends WHERE a=? AND b=? AND status='accepted'",(x,y)).fetchone())
    def direct(self,db,a,b):
        key=':'.join(sorted((a,b)));row=db.execute('SELECT id FROM threads WHERE direct_key=?',(key,)).fetchone()
        if row:return row['id']
        tid=identifier();db.execute('INSERT INTO threads(id,title,kind,direct_key,created) VALUES(?,?,?,?,?)',(tid,'','direct',key,time.time()))
        db.executemany('INSERT INTO members(thread,uid) VALUES(?,?)',[(tid,a),(tid,b)]);return tid
    def file_meta(self,db,fid):
        row=db.execute('SELECT id,name,mime,size,sha256 FROM files WHERE id=?',(fid,)).fetchone()
        if not row:raise Problem('Attachment not found.',404)
        return dict(row)
    def person(self,db,row):
        result=public(row);fid=row['avatar'] if 'avatar' in row.keys() else None
        result['avatar']=self.file_meta(db,fid) if fid else None;return result
    def social_call(self,uid,action,data):
        with self.lock,self.connect() as db:
            if action=='profile':
                fid=data.get('avatar') or None
                if fid:
                    file=db.execute('SELECT mime,size FROM files WHERE id=? AND owner=?',(fid,uid)).fetchone()
                    if not file or not file['mime'].startswith('image/') or file['size']>2*1024*1024:raise Problem('Choose one of your own profile images up to 2 MB.')
                db.execute('UPDATE users SET avatar=? WHERE id=?',(fid,uid));return {'user':self.person(db,db.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone())}
            if action=='presence':
                session=text(data.get('_session',''),64)
                if not session:raise Problem('Sign in again.',401)
                state='idle' if data.get('status')=='idle' else 'online';deck=text(data.get('deck',''),700).split('::')[-1][:160] if data.get('share') is True and state!='idle' else ''
                db.execute('INSERT INTO presence VALUES(?,?,?,?,?) ON CONFLICT(session) DO UPDATE SET status=excluded.status,deck=excluded.deck,updated=excluded.updated',(session,uid,state,deck,time.time()));return {'ok':True}
            tid=text(data.get('thread',''),40);self.member(db,tid,uid)
            if action=='typing':
                until=time.time()+5 if data.get('typing') is True else 0;db.execute('UPDATE members SET typing_until=? WHERE thread=? AND uid=?',(until,tid,uid));return {'thread':tid,'uid':uid,'until':until}
            maximum=db.execute('SELECT COALESCE(max(id),0) FROM messages WHERE thread=?',(tid,)).fetchone()[0];last=min(maximum,max(0,int(data.get('last',0))))
            if action=='read':db.execute('UPDATE members SET seen=max(seen,?),delivered=max(delivered,?) WHERE thread=? AND uid=?',(last,last,tid,uid))
            else:db.execute('UPDATE members SET delivered=max(delivered,?) WHERE thread=? AND uid=?',(last,tid,uid))
            return {'ok':True,'receipt':dict(db.execute('SELECT thread,uid,seen,delivered FROM members WHERE thread=? AND uid=?',(tid,uid)).fetchone())}
    def status(self,uid,reaction_after=0):
        reaction_after=max(0,min(9007199254740991,float(reaction_after or 0)))
        with self.connect() as db:
            receipts=[dict(r) for r in db.execute('SELECT m.thread,m.uid,m.seen,m.delivered FROM members m JOIN members own ON own.thread=m.thread WHERE own.uid=?',(uid,))]
            typing=[dict(r) for r in db.execute('SELECT m.thread,m.uid,m.typing_until AS until FROM members m JOIN members own ON own.thread=m.thread WHERE own.uid=? AND m.typing_until>?',(uid,time.time()))]
            people=[]
            for row in db.execute("SELECT u.* FROM users u WHERE u.id=? OR EXISTS(SELECT 1 FROM friends fr WHERE fr.status='accepted' AND ((fr.a=? AND fr.b=u.id) OR (fr.b=? AND fr.a=u.id))) OR EXISTS(SELECT 1 FROM members a JOIN members b ON a.thread=b.thread WHERE a.uid=? AND b.uid=u.id)",(uid,uid,uid,uid)):
                p=self.person(db,row);activity=db.execute('SELECT p.status,p.deck,p.updated FROM presence p JOIN sessions s ON s.token=p.session WHERE p.uid=? AND p.updated>? AND s.expires>? ORDER BY p.updated DESC LIMIT 1',(row['id'],time.time()-55,time.time())).fetchone();p['activity']=dict(activity) if activity else None;people.append(p)
            touched=db.execute('SELECT m.thread,r.message,r.updated FROM reaction_updates r JOIN messages m ON m.id=r.message JOIN members own ON own.thread=m.thread WHERE own.uid=? AND r.updated>? ORDER BY r.updated,r.message LIMIT 200',(uid,reaction_after)).fetchall()
            reactions=[self.reaction_summary(db,r['thread'],r['message']) for r in touched]
            memberships=[dict(r) for r in db.execute("SELECT t.id AS thread,t.membership_version FROM threads t JOIN members own ON own.thread=t.id WHERE own.uid=? AND t.kind='group' ORDER BY t.id",(uid,))]
            return {'receipts':receipts,'typing':typing,'people':people,'reactions':reactions,'reaction_cursor':touched[-1]['updated'] if touched else reaction_after,'group_memberships':memberships,'server_time':time.time()}
    def publish(self,thread,event,data):
        # Cached subscriptions cannot authorize a send after membership changes.
        with self.lock,self.connect() as db:
            for peer in list(self.peers):
                if thread in peer.threads and db.execute('SELECT 1 FROM members WHERE thread=? AND uid=?',(thread,peer.uid)).fetchone():peer.send_event(event,data)
    def notify(self,action,result):
        if action=='message':self.publish(result['message']['thread'],'messages',{'thread':result['message']['thread'],'messages':[result['message']]})
        elif action in ('read','delivered'):self.publish(result['receipt']['thread'],'receipts',{'receipts':[result['receipt']]})
        elif action=='typing':self.publish(result['thread'],'typing',result)
        elif action=='group_photo':self.publish(result['thread'],'group_updated',result)
        elif action=='reaction':self.publish(result['thread'],'reaction_updated',result)
        elif action in ('group_add','group_remove','group_admin','group_leave'):
            with self.lock:
                if result.get('removed'):
                    for peer in list(self.peers):
                        if peer.uid==result['removed']:
                            peer.threads.discard(result['thread']);peer.send_event('group_removed',{'thread':result['thread'],'membership_version':result['membership_version']})
                self.publish(result['thread'],'membership_updated',{'thread':result['thread'],'membership_version':result['membership_version']})
        elif action=='claim_legacy_groups':
            for tid in result['claimed']:
                with self.connect() as db:version=db.execute('SELECT membership_version FROM threads WHERE id=?',(tid,)).fetchone()[0]
                self.publish(tid,'membership_updated',{'thread':tid,'membership_version':version})
    def can_read_file(self,db,fid,uid):
        return bool(db.execute('SELECT 1 FROM files WHERE id=? AND owner=?',(fid,uid)).fetchone()
                    or db.execute('SELECT 1 FROM messages m JOIN members t ON t.thread=m.thread WHERE m.file=? AND t.uid=?',(fid,uid)).fetchone()
                    or db.execute('SELECT 1 FROM invites i JOIN members own ON own.thread=i.thread WHERE i.file=? AND own.uid=? AND (i.sender=? OR i.recipient=?)',(fid,uid,uid,uid)).fetchone()
                    or db.execute("SELECT 1 FROM users u WHERE u.avatar=? AND (EXISTS(SELECT 1 FROM friends fr WHERE fr.status='accepted' AND ((fr.a=u.id AND fr.b=?) OR (fr.b=u.id AND fr.a=?))) OR EXISTS(SELECT 1 FROM members a JOIN members b ON a.thread=b.thread WHERE a.uid=u.id AND b.uid=?))",(fid,uid,uid,uid)).fetchone()
                    or db.execute("SELECT 1 FROM threads g JOIN members m ON m.thread=g.id WHERE g.kind='group' AND g.avatar=? AND m.uid=?",(fid,uid)).fetchone())
    def upload(self,uid,name,mime,content):
        self.limited(('upload',uid),40)
        if not content or len(content)>self.max_file:raise Problem('Attachment is empty or too large.',413)
        images={'image/png':content.startswith(b'\x89PNG\r\n\x1a\n'),'image/jpeg':content.startswith(b'\xff\xd8\xff'),'image/gif':content[:6] in (b'GIF87a',b'GIF89a'),'image/webp':content[:4]==b'RIFF' and content[8:12]==b'WEBP'}
        if mime in images:
            if not images[mime] or len(content)>12*1024*1024:raise Problem('Use a PNG, JPEG, GIF or WebP image up to 12 MB.')
        elif mime!='application/zip' or not content.startswith(b'PK\x03\x04'):raise Problem('Unsupported attachment type.')
        name=Path(text(name,180)).name or 'attachment';fid=identifier();target=self.blobs/fid
        try:
            target.write_bytes(content)
            with self.connect() as db:
                db.execute('INSERT INTO files VALUES(?,?,?,?,?,?,?)',(fid,uid,name,mime,len(content),hashlib.sha256(content).hexdigest(),time.time()))
                return self.file_meta(db,fid)
        except Exception:target.unlink(missing_ok=True);raise
    def bootstrap(self,uid):
        with self.connect() as db:
            me=self.person(db,db.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone())
            people=[]
            for r in db.execute('SELECT f.*,u.id,u.username,u.name,u.code,u.avatar FROM friends f JOIN users u ON u.id=CASE WHEN f.a=? THEN f.b ELSE f.a END WHERE f.a=? OR f.b=?',(uid,uid,uid)):
                p=self.person(db,r);p.update(status=r['status'],incoming=r['requester']!=uid);people.append(p)
            threads=[]
            for row in db.execute('SELECT t.*,m.seen,(SELECT max(id) FROM messages WHERE thread=t.id) AS last_id,(SELECT count(*) FROM messages WHERE thread=t.id AND id>m.seen AND sender!=?) AS unread FROM threads t JOIN members m ON m.thread=t.id WHERE m.uid=? ORDER BY COALESCE((SELECT max(created) FROM messages WHERE thread=t.id),t.created) DESC',(uid,uid)):
                t=dict(row);members=[self.person(db,p) for p in db.execute('SELECT u.* FROM users u JOIN members m ON m.uid=u.id WHERE m.thread=?',(t['id'],))];t['members']=members
                if t['kind']=='group':t.update(self.group_state(db,t['id']));members=t['members']
                if t['kind']=='direct':t['title']=next(p['name'] for p in members if p['id']!=uid)
                t['avatar']=self.file_meta(db,t['avatar']) if t['avatar'] else None
                last=db.execute('SELECT kind,text,sender FROM messages WHERE thread=? ORDER BY id DESC LIMIT 1',(t['id'],)).fetchone();t['last']=dict(last) if last else None;threads.append(t)
            invites=[]
            for row in db.execute('SELECT i.*,u.name AS sender_name FROM invites i JOIN users u ON u.id=i.sender JOIN members own ON own.thread=i.thread WHERE own.uid=? AND (i.sender=? OR i.recipient=?) ORDER BY created DESC LIMIT 200',(uid,uid,uid)):
                item=dict(row);item['summary']=json.loads(item['summary']);item['result']=json.loads(item['result']);item['attachment']=self.file_meta(db,item['file']);invites.append(item)
            return {'user':me,'friends':people,'threads':threads,'invites':invites,'max_file_bytes':self.max_file,'server_version':VERSION,'realtime':True,'features':{'group_deck_shares':True,'message_reactions':True,'group_administration':True}}
    def call(self,uid,action,data):
        social=action in ('presence','typing','delivered','read');self.limited(('social' if social else 'actions',uid),600 if social else 180)
        if social or action=='profile':return self.social_call(uid,action,data)
        with self.lock,self.connect() as db:
            # Acquire the SQLite write lock before reading roles; a second Relay
            # serving this same file cannot race an owner handover or member cap.
            db.execute('BEGIN IMMEDIATE')
            if action=='reaction':
                tid=text(data.get('thread',''),40);self.member(db,tid,uid);mid=data.get('message');emoji=data.get('emoji')
                if type(mid) is not int or not db.execute("SELECT 1 FROM messages WHERE id=? AND thread=? AND kind!='system'",(mid,tid)).fetchone():raise Problem('Message not found.',404)
                if not isinstance(emoji,str) or emoji not in ('',*REACTIONS):raise Problem('Choose a supported reaction.')
                if emoji:db.execute('INSERT INTO reactions VALUES(?,?,?) ON CONFLICT(message,uid) DO UPDATE SET emoji=excluded.emoji',(mid,uid,emoji))
                else:db.execute('DELETE FROM reactions WHERE message=? AND uid=?',(mid,uid))
                db.execute('INSERT INTO reaction_updates VALUES(?,max(?,COALESCE((SELECT max(updated)+0.000001 FROM reaction_updates),0))) ON CONFLICT(message) DO UPDATE SET updated=excluded.updated',(mid,time.time()))
                return self.reaction_summary(db,tid,mid)
            if action=='claim_legacy_groups':
                expected=os.getenv('ANKI_LINK_LEGACY_OWNER_USERNAME','')
                username=db.execute('SELECT username FROM users WHERE id=?',(uid,)).fetchone()[0]
                if not expected or username!=expected:raise Problem('Legacy ownership claim is not enabled for this account.',403)
                claimed=[r[0] for r in db.execute("SELECT t.id FROM threads t JOIN members m ON m.thread=t.id WHERE t.kind='group' AND t.owner IS NULL AND m.uid=?",(uid,))]
                for tid in claimed:
                    db.execute('UPDATE threads SET owner=?,membership_version=membership_version+1 WHERE id=?',(uid,tid));db.execute('UPDATE members SET admin=1 WHERE thread=? AND uid=?',(tid,uid))
                return {'claimed':claimed}
            if action in ('group_add','group_remove','group_admin','group_leave'):
                tid=text(data.get('thread',''),40);self.member(db,tid,uid);state=self.group_state(db,tid)
                owner=state['owner'];actor=next(m for m in state['members'] if m['id']==uid);removed=None
                if action=='group_leave':
                    removed=uid;self.group_notice(db,tid,uid,actor['name']+' left the group.')
                elif action=='group_add':
                    if not actor['admin']:raise Problem('Only a group owner or admin can add members.',403)
                    users=data.get('users');existing={m['id'] for m in state['members']}
                    if not isinstance(users,list) or not 1<=len(users)<=30 or any(not isinstance(u,str) for u in users):raise Problem('Choose accepted friends for your group.')
                    additions=set(users)-existing
                    if len(existing|set(users))>31 or any(not self.friends(db,uid,u) for u in additions):raise Problem('Choose accepted friends; groups allow up to 31 members.')
                    if not additions:return state
                    for target in sorted(additions):
                        db.execute('INSERT INTO members(thread,uid) VALUES(?,?)',(tid,target))
                        name=db.execute('SELECT name FROM users WHERE id=?',(target,)).fetchone()[0]
                        self.group_notice(db,tid,uid,actor['name']+' added '+name+'.')
                else:
                    target=text(data.get('user',''),40);member=next((m for m in state['members'] if m['id']==target),None)
                    if not member:raise Problem('Member not found.',404)
                    if action=='group_admin':
                        if uid!=owner:raise Problem('Only the group owner can appoint admins.',403)
                        if not isinstance(data.get('admin'),bool) or target==owner:raise Problem('The owner must remain an admin.')
                        if member['admin']==data['admin']:return state
                        db.execute('UPDATE members SET admin=? WHERE thread=? AND uid=?',(int(data['admin']),tid,target))
                        self.group_notice(db,tid,uid,actor['name']+(' made '+member['name']+' an admin.' if data['admin'] else ' removed '+member['name']+' as an admin.'))
                    else:
                        if target==owner or not actor['admin'] or uid!=owner and member['admin']:raise Problem('You cannot remove this member.',403)
                        removed=target;self.group_notice(db,tid,uid,actor['name']+' removed '+member['name']+'.')
                if removed:
                    if removed==owner:
                        remaining=[m['id'] for m in state['members'] if m['id']!=removed];replacement=secrets.choice(remaining) if remaining else None
                        db.execute('UPDATE threads SET owner=? WHERE id=?',(replacement,tid))
                        if replacement:
                            db.execute('UPDATE members SET admin=1 WHERE thread=? AND uid=?',(tid,replacement))
                            name=db.execute('SELECT name FROM users WHERE id=?',(replacement,)).fetchone()[0]
                            self.group_notice(db,tid,uid,name+' became the group owner.')
                    db.execute('DELETE FROM members WHERE thread=? AND uid=?',(tid,removed))
                db.execute('UPDATE threads SET membership_version=membership_version+1 WHERE id=?',(tid,))
                result=self.group_state(db,tid)
                if removed:result['removed']=removed
                return result
            if action=='friend_request':
                code=text(data.get('code',''),30).upper().replace('-','').replace(' ','');other=db.execute('SELECT id FROM users WHERE code=?',(code,)).fetchone()
                if not other or other['id']==uid:raise Problem('Friend code not found.')
                a,b=sorted((uid,other['id']));db.execute("INSERT OR IGNORE INTO friends(a,b,requester) VALUES(?,?,?)",(a,b,uid));return {'ok':True}
            if action=='friend_decide':
                other=text(data.get('user',''),40);a,b=sorted((uid,other));r=db.execute('SELECT * FROM friends WHERE a=? AND b=?',(a,b)).fetchone()
                if not r or r['requester']==uid or r['status']!='pending':raise Problem('Friend request not found.',404)
                if data.get('accept') is True:
                    db.execute("UPDATE friends SET status='accepted' WHERE a=? AND b=?",(a,b));tid=self.direct(db,uid,other);return {'thread':tid}
                db.execute('DELETE FROM friends WHERE a=? AND b=?',(a,b));return {'ok':True}
            if action=='direct':
                other=text(data.get('user',''),40)
                if not self.friends(db,uid,other):raise Problem('Add and accept this friend first.',403)
                return {'thread':self.direct(db,uid,other)}
            if action=='group':
                users=data.get('users',[])
                if not isinstance(users,list) or not 1<=len(users)<=30 or any(not self.friends(db,uid,u) for u in users):raise Problem('Choose accepted friends for your group.')
                title=text(data.get('title',''),70)
                if not title:raise Problem('Give the group a name.')
                tid=identifier();db.execute('INSERT INTO threads(id,title,kind,direct_key,created,owner,membership_version) VALUES(?,?,?,?,?,?,1)',(tid,title,'group',None,time.time(),uid))
                db.executemany('INSERT INTO members(thread,uid,admin) VALUES(?,?,?)',[(tid,u,int(u==uid)) for u in set(users+[uid])]);return {'thread':tid}
            if action=='group_photo':
                tid=text(data.get('thread',''),40);self.member(db,tid,uid)
                if not db.execute("SELECT id FROM threads WHERE id=? AND kind='group'",(tid,)).fetchone():raise Problem('Group not found.',404)
                fid=None if data.get('avatar') is None else text(data['avatar'],40)
                if fid is not None:
                    image=db.execute('SELECT mime,size FROM files WHERE id=? AND owner=?',(fid,uid)).fetchone()
                    if not image or image['mime'] not in ('image/png','image/jpeg','image/gif','image/webp') or image['size']>2*1024*1024:raise Problem('Choose one of your own group images up to 2 MB.')
                previous=db.execute('SELECT avatar FROM threads WHERE id=?',(tid,)).fetchone()[0]
                if previous!=fid:
                    actor=db.execute('SELECT name FROM users WHERE id=?',(uid,)).fetchone()[0]
                    self.group_notice(db,tid,uid,actor+(' removed the group photo.' if fid is None else ' changed the group photo.' if previous else ' added a group photo.'))
                changed=db.execute("UPDATE threads SET avatar=?,avatar_version=avatar_version+1 WHERE id=? AND kind='group' AND EXISTS(SELECT 1 FROM members WHERE thread=threads.id AND uid=?)",(fid,tid,uid))
                if not changed.rowcount:raise Problem('Group not found.',404)
                saved=db.execute('SELECT avatar,avatar_version FROM threads WHERE id=?',(tid,)).fetchone()
                return {'thread':tid,'avatar':self.file_meta(db,saved['avatar']) if saved['avatar'] else None,'avatar_version':saved['avatar_version']}
            if action=='message':
                tid=text(data.get('thread',''),40);self.member(db,tid,uid)
                nonce=text(data.get('nonce',''),80);kind=data.get('kind','text');body=text(data.get('text',''))
                if not nonce:raise Problem('Message identifier missing.')
                if nonce.startswith(SYSTEM_NONCE_PREFIX):raise Problem('Reserved message identifier.')
                fid=data.get('file') or None
                if kind not in ('text','image','sticker'):raise Problem('Invalid message type.')
                if fid:
                    row=db.execute('SELECT * FROM files WHERE id=? AND owner=?',(fid,uid)).fetchone()
                    if not row or not row['mime'].startswith('image/'):raise Problem('Choose one of your uploaded images.')
                if kind=='text' and not body or kind=='image' and not fid or kind=='sticker' and not fid and body not in ('cheer','love','coffee','focus','wow','sleep','thanks','yes'):raise Problem('Message is empty or invalid.')
                db.execute('INSERT OR IGNORE INTO messages(thread,sender,kind,text,file,nonce,created) VALUES(?,?,?,?,?,?,?)',(tid,uid,kind,body,fid,nonce,time.time()))
                message=dict(db.execute('SELECT m.*,u.name FROM messages m JOIN users u ON u.id=m.sender WHERE m.thread=? AND m.sender=? AND m.nonce=?',(tid,uid,nonce)).fetchone())
                self.decorate_reactions(db,[message])
                if message['file']:message['attachment']=self.file_meta(db,message['file'])
                return {'id':message['id'],'message':message}
            if action=='invite':
                recipients=data.get('recipients',[]);fid=text(data.get('file',''),40);summary=data.get('summary');nonce=text(data.get('nonce',''),80)
                if nonce.startswith(SYSTEM_NONCE_PREFIX):raise Problem('Reserved message identifier.')
                if data.get('thread'):
                    tid=text(data['thread'],40);self.member(db,tid,uid)
                    if not db.execute("SELECT 1 FROM threads WHERE id=? AND kind='group'",(tid,)).fetchone():raise Problem('Choose a group conversation.')
                    recipients=sorted(r['uid'] for r in db.execute('SELECT uid FROM members WHERE thread=? AND uid!=?',(tid,uid)))
                    if not nonce or not 1<=len(recipients)<=30:raise Problem('The group must have 1–30 other members.')
                    if not isinstance(summary,dict) or len(json.dumps(summary))>50000:raise Problem('Invalid deck summary.')
                    row=db.execute('SELECT mime FROM files WHERE id=? AND owner=?',(fid,uid)).fetchone()
                    if not row or row['mime']!='application/zip':raise Problem('Deck attachment not found.')
                    previous=list(db.execute('SELECT * FROM invites WHERE sender=? AND nonce=? ORDER BY recipient',(uid,nonce)))
                    if previous:
                        if any(r['thread']!=tid or json.loads(r['summary'])!=summary for r in previous):raise Problem('This share was already sent to another destination. Start a new share.',409)
                        return {'thread':tid,'invitations':[r['id'] for r in previous]}
                    result=[]
                    for recipient in recipients:
                        iid=identifier();result.append(iid)
                        db.execute('INSERT INTO invites(id,sender,recipient,thread,file,summary,nonce,created) VALUES(?,?,?,?,?,?,?,?)',(iid,uid,recipient,tid,fid,json.dumps(summary,ensure_ascii=False),nonce,time.time()))
                    db.execute('INSERT INTO messages(thread,sender,kind,text,invite,nonce,created) VALUES(?,?,?,?,?,?,?)',(tid,uid,'deck',text(summary.get('title','Shared decks'),150),result[0],nonce,time.time()))
                    return {'thread':tid,'invitations':result}
                if not nonce or not isinstance(recipients,list) or not 1<=len(recipients)<=30 or any(not self.friends(db,uid,u) for u in recipients):raise Problem('Select accepted friends.')
                if not isinstance(summary,dict) or len(json.dumps(summary))>50000:raise Problem('Invalid deck summary.')
                row=db.execute('SELECT mime FROM files WHERE id=? AND owner=?',(fid,uid)).fetchone()
                if not row or row['mime']!='application/zip':raise Problem('Deck attachment not found.')
                result=[]
                for recipient in set(recipients):
                    old=db.execute('SELECT id FROM invites WHERE sender=? AND recipient=? AND nonce=?',(uid,recipient,nonce)).fetchone()
                    if old:result.append(old['id']);continue
                    tid=self.direct(db,uid,recipient);iid=identifier()
                    db.execute('INSERT INTO invites(id,sender,recipient,thread,file,summary,nonce,created) VALUES(?,?,?,?,?,?,?,?)',(iid,uid,recipient,tid,fid,json.dumps(summary,ensure_ascii=False),nonce,time.time()))
                    db.execute('INSERT INTO messages(thread,sender,kind,text,invite,nonce,created) VALUES(?,?,?,?,?,?,?)',(tid,uid,'deck',text(summary.get('title','Shared decks'),150),iid,nonce,time.time()));result.append(iid)
                return {'invitations':result}
            if action=='invite_state':
                iid=text(data.get('id',''),40);state=data.get('state');row=db.execute('SELECT * FROM invites WHERE id=? AND recipient=?',(iid,uid)).fetchone()
                if not row:raise Problem('Invitation not found.',404)
                self.member(db,row['thread'],uid)
                if state not in ('accepted','rejected'):raise Problem('Invalid invitation state.')
                if row['state']!='pending':
                    if row['state']==state:return {'ok':True}
                    raise Problem('That invitation was already handled.',409)
                result=data.get('result',{})
                if not isinstance(result,dict) or len(json.dumps(result))>10000:raise Problem('Invalid import result.')
                db.execute('UPDATE invites SET state=?,result=? WHERE id=?',(state,json.dumps(result),iid));return {'ok':True}
            raise Problem('Unknown action.',404)
    def decorate_decks(self,db,uid,messages):
        """Each user receives only their own invitation, or their sent invites."""
        ids=[m['id'] for m in messages if m['kind']=='deck'];invites=[];by_message={};files={}
        for offset in range(0,len(ids),80):
            part=ids[offset:offset+80];marks=','.join('?' for _ in part)
            sql=f'SELECT i.*,u.name AS sender_name,m.id AS message_id FROM invites i JOIN users u ON u.id=i.sender JOIN messages m ON m.thread=i.thread AND m.sender=i.sender AND m.nonce=i.nonce WHERE m.id IN ({marks}) AND (i.recipient=? OR i.sender=?) ORDER BY i.recipient'
            for row in db.execute(sql,(*part,uid,uid)):
                item=dict(row);mid=item.pop('message_id');item['summary']=json.loads(item['summary']);item['result']=json.loads(item['result'])
                if item['file'] not in files:files[item['file']]=self.file_meta(db,item['file'])
                item['attachment']=files[item['file']];invites.append(item);by_message.setdefault(mid,[]).append(item)
        for message in messages:
            choices=by_message.get(message['id'],[])
            if choices:message['invite']=next((i['id'] for i in choices if i['recipient']==uid),choices[0]['id'])
        return {'messages':messages,'invites':invites}
    def messages(self,uid,thread,after=0,before=0):
        with self.lock,self.connect() as db:
            self.member(db,thread,uid)
            if after:rows=db.execute('SELECT m.*,u.name FROM messages m JOIN users u ON u.id=m.sender WHERE m.thread=? AND m.id>? ORDER BY m.id LIMIT 200',(thread,after)).fetchall()
            else:rows=list(reversed(db.execute('SELECT m.*,u.name FROM messages m JOIN users u ON u.id=m.sender WHERE m.thread=? AND (?=0 OR m.id<?) ORDER BY m.id DESC LIMIT 100',(thread,before,before)).fetchall()))
            result=[]
            for r in rows:
                m=dict(r)
                if m['file']:m['attachment']=self.file_meta(db,m['file'])
                result.append(m)
            status=self.status(uid);status.pop('reaction_cursor',None)
            return {**self.decorate_decks(db,uid,self.decorate_reactions(db,result)),**status}

class Handler(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    server_version='AnkiLink/'+VERSION
    def setup(self):
        super().setup();self.connection.settimeout(45)
    def log_message(self,fmt,*args):pass  # Never log tokens, passwords or chat text.
    def respond(self,status,value,content_type='application/json; charset=utf-8'):
        content=json.dumps(value,ensure_ascii=False).encode() if not isinstance(value,bytes) else value
        self.send_response(status);self.send_header('Content-Type',content_type);self.send_header('Content-Length',str(len(content)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Security-Policy',"default-src 'none'; frame-ancestors 'none'");self.end_headers();self.wfile.write(content)
    def do_GET(self):self.route()
    def do_POST(self):self.route()
    def send_event(self,event,data):
        raw=json.dumps({'event':event,'data':data},ensure_ascii=False).encode()
        try:
            with self.write_lock:
                header=bytes([0x81,len(raw)]) if len(raw)<126 else bytes([0x81,126])+struct.pack('!H',len(raw)) if len(raw)<65536 else bytes([0x81,127])+struct.pack('!Q',len(raw))
                self.wfile.write(header+raw)
        except OSError:self.live_closed=True
    def live(self,uid,token):
        key=self.headers.get('Sec-WebSocket-Key','')
        try:valid=len(base64.b64decode(key,validate=True))==16
        except ValueError:valid=False
        if self.headers.get('Upgrade','').lower()!='websocket' or self.headers.get('Sec-WebSocket-Version')!='13' or not valid:raise Problem('Use a WebSocket connection.',426)
        self.send_response(101);self.send_header('Upgrade','websocket');self.send_header('Connection','Upgrade');self.send_header('Sec-WebSocket-Accept',base64.b64encode(hashlib.sha1((key+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode());self.end_headers()
        self.close_connection=True;self.live_closed=False;self.write_lock=threading.Lock();self.threads=set();self.uid=uid;app=self.server.app;session=hashlib.sha256(token.encode()).hexdigest();last_auth=time.monotonic();signature=''
        with app.connect() as db:
            self.threads={r[0] for r in db.execute('SELECT thread FROM members WHERE uid=?',(uid,))}
            cursor=db.execute('SELECT COALESCE(max(m.id),0) FROM messages m JOIN members own ON own.thread=m.thread WHERE own.uid=?',(uid,)).fetchone()[0]
        with app.lock:app.peers.add(self)
        self.send_event('live_ready',{'server_version':VERSION})
        try:
            while not self.live_closed:
                head=self.rfile.read(2)
                if len(head)!=2:break
                opcode=head[0]&15;length=head[1]&127
                if not head[0]&128 or not head[1]&128:break  # bounded, masked client frames only
                if length==126:length=struct.unpack('!H',self.rfile.read(2))[0]
                elif length==127:length=struct.unpack('!Q',self.rfile.read(8))[0]
                if length>64000:break
                mask=self.rfile.read(4);raw=self.rfile.read(length)
                if len(mask)!=4 or len(raw)!=length:break
                raw=bytes(v^mask[i%4] for i,v in enumerate(raw))
                if opcode==8:break
                if opcode==9:
                    if length>125:break
                    with self.write_lock:self.wfile.write(bytes([0x8a,length])+raw)
                    continue
                if opcode!=1:break
                frame=json.loads(raw.decode('utf-8'));action=frame.get('action');data=frame.get('data') or {};data['_session']=session
                if time.monotonic()-last_auth>25:app.user(token);last_auth=time.monotonic()
                try:
                    if action=='pull':
                        with app.lock,app.connect() as db:
                            groups=db.execute('SELECT t.id AS thread,t.membership_version,m.uid AS member FROM threads t LEFT JOIN members m ON m.thread=t.id AND m.uid=? WHERE m.uid IS NOT NULL OR t.id IN (SELECT value FROM json_each(?))',(uid,json.dumps(list(self.threads)))).fetchall()
                            for group in groups:
                                if not group['member'] and group['thread'] in self.threads:self.send_event('group_removed',{'thread':group['thread'],'membership_version':group['membership_version']})
                            self.threads={g['thread'] for g in groups if g['member']}
                            rows=db.execute('SELECT m.*,u.name FROM messages m JOIN users u ON u.id=m.sender JOIN members own ON own.thread=m.thread WHERE own.uid=? AND m.id>? ORDER BY m.id LIMIT 200',(uid,cursor)).fetchall()
                            messages=[]
                            for row in rows:
                                m=dict(row)
                                if m['file']:m['attachment']=app.file_meta(db,m['file'])
                                messages.append(m)
                            decorated=app.decorate_decks(db,uid,app.decorate_reactions(db,messages))
                            for m in decorated['messages']:
                                cursor=max(cursor,m['id']);self.threads.add(m['thread'])
                                related=[i for i in decorated['invites'] if i['thread']==m['thread'] and i['sender']==m['sender'] and i['nonce']==m['nonce']]
                                self.send_event('messages',{'thread':m['thread'],'messages':[m],'invites':related})
                            status=app.status(uid,data.get('reaction_after',0));current=json.dumps({k:v for k,v in status.items() if k!='server_time'},sort_keys=True)
                            self.threads={r[0] for r in db.execute('SELECT thread FROM members WHERE uid=?',(uid,))}
                            if current!=signature:signature=current;self.send_event('status',status)
                    elif action=='watch':
                        with app.lock:
                            tid=text(data.get('thread',''),40);result=app.messages(uid,tid,max(0,int(data.get('after',0))));self.threads.add(tid);self.send_event('messages',{**result,'thread':tid,'history':True})
                    elif action in ('message','read','delivered','typing','presence','reaction','group_add','group_remove','group_admin','group_leave'):
                        result=app.call(uid,action,data);app.notify(action,result)
                        if action=='message':self.send_event('sent',{**result,'thread':data['thread'],'nonce':data['nonce']})
                    else:raise Problem('Unknown live action.')
                except Problem as error:self.send_event('live_error',{'action':action,'nonce':data.get('nonce'),'thread':data.get('thread'),'message':str(error)})
        except (OSError,ValueError,KeyError,TypeError,struct.error,Problem):pass
        finally:
            with app.lock:app.peers.discard(self)
            try:
                with self.write_lock:self.wfile.write(b'\x88\x00')
            except OSError:pass
    def route(self):
        try:
            app=self.server.app;url=urlsplit(self.path);path=url.path
            if self.command=='GET' and path=='/':return self.respond(200,b'AnkiLink server is online. Enter this server address in the AnkiLink desktop add-on.','text/plain; charset=utf-8')
            if self.command=='GET' and path=='/health':return self.respond(200,{'service':'AnkiLink','version':VERSION})
            size=int(self.headers.get('Content-Length','0'))
            if size<0 or size>(app.max_file if path=='/v1/upload' else 200000):raise Problem('Request too large.',413)
            raw=self.rfile.read(size) if self.command=='POST' else b''
            if path in ('/v1/register','/v1/login') and self.command=='POST':
                return self.respond(200,app.authenticate(json.loads(raw),path.endswith('register'),self.client_address[0]))
            bearer=self.headers.get('Authorization','')
            if not bearer.startswith('Bearer '):raise Problem('Please sign in.',401)
            token=bearer[7:];uid=app.user(token)
            if path=='/v1/logout' and self.command=='POST':
                with app.lock,app.connect() as db:
                    key=hashlib.sha256(token.encode()).hexdigest();db.execute('DELETE FROM presence WHERE session=?',(key,));db.execute('DELETE FROM sessions WHERE token=?',(key,))
                return self.respond(200,{'ok':True})
            if path=='/v1/live' and self.command=='GET':return self.live(uid,token)
            if path=='/v1/status' and self.command=='GET':return self.respond(200,app.status(uid,parse_qs(url.query).get('reaction_after',['0'])[0]))
            if path=='/v1/bootstrap' and self.command=='GET':return self.respond(200,app.bootstrap(uid))
            if path=='/v1/messages' and self.command=='GET':
                q=parse_qs(url.query);return self.respond(200,app.messages(uid,q.get('thread',[''])[0],max(0,int(q.get('after',['0'])[0])),max(0,int(q.get('before',['0'])[0]))))
            if path=='/v1/upload' and self.command=='POST':return self.respond(200,app.upload(uid,self.headers.get('X-File-Name','attachment'),self.headers.get('Content-Type','').split(';')[0],raw))
            if path.startswith('/v1/files/') and self.command=='GET':
                fid=path.rsplit('/',1)[1]
                with app.connect() as db:
                    if not app.can_read_file(db,fid,uid):raise Problem('Attachment not found.',404)
                    meta=app.file_meta(db,fid)
                return self.respond(200,(app.blobs/fid).read_bytes(),meta['mime'])
            if path.startswith('/v1/actions/') and self.command=='POST':
                action=path.rsplit('/',1)[1];data=json.loads(raw);data['_session']=hashlib.sha256(token.encode()).hexdigest();result=app.call(uid,action,data);app.notify(action,result);return self.respond(200,result)
            raise Problem('Not found.',404)
        except Problem as error:self.respond(error.status,{'error':str(error)})
        except (ValueError,TypeError,KeyError,json.JSONDecodeError):self.respond(400,{'error':'Invalid request.'})
        except (BrokenPipeError,ConnectionResetError):pass
        except Exception:self.respond(500,{'error':'The server could not complete this request.'})

def make_server(host='127.0.0.1',port=8766,directory='data',**kwargs):
    server=ThreadingHTTPServer((host,port),Handler);server.daemon_threads=True;server.app=Relay(directory,**kwargs);return server

def main():
    parser=argparse.ArgumentParser(description='AnkiLink private chat and deck relay')
    parser.add_argument('--host',default=os.getenv('HOST','127.0.0.1'));parser.add_argument('--port',type=int,default=int(os.getenv('PORT','8766')));parser.add_argument('--data',default=os.getenv('ANKI_LINK_DATA','data'));args=parser.parse_args()
    server=make_server(args.host,args.port,args.data,join_code=os.getenv('ANKI_LINK_JOIN_CODE',''),max_users=int(os.getenv('ANKI_LINK_MAX_USERS','100')),max_file_mb=int(os.getenv('ANKI_LINK_MAX_FILE_MB','250')))
    print(f'AnkiLink {VERSION} listening on {args.host}:{args.port}. Use HTTPS for internet access.',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
