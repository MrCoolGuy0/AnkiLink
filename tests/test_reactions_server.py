"""Real HTTP/WebSocket coverage for standalone reactions and group membership ACLs."""
import base64
from concurrent.futures import ThreadPoolExecutor
import json
import os
import socket
import struct
import tempfile
import threading
import unittest
from unittest.mock import patch
from test_relay import N, make_server, PNG
import server as R


class ReactionsGroupsHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.server=make_server(port=0,directory=cls.temp.name)
        cls.worker=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.worker.start()
        cls.url='http://127.0.0.1:'+str(cls.server.server_port);cls.clients=[];cls.users=[]
        for name in ('jigstar','member','third','fourth','outside'):
            c=N.Client(cls.url);session=c.request('/v1/register',data={'username':name,'password':'a strong test password'})
            c.token=session['token'];cls.clients.append(c);cls.users.append(session['user'])
        cls.a,cls.b,cls.c,cls.d,cls.outside=cls.clients
        for i,j in ((0,1),(0,2),(0,3),(1,3)):
            cls.clients[i].action('friend_request',{'code':cls.users[j]['code']})
            cls.clients[j].action('friend_decide',{'user':cls.users[i]['id'],'accept':True})
    @classmethod
    def tearDownClass(cls):
        for c in cls.clients:c.close()
        cls.server.shutdown();cls.server.server_close();cls.worker.join(2);cls.temp.cleanup()
    def setUp(self):
        self.tid=self.a.action('group',{'title':'Study group','users':[self.uid(1),self.uid(2)]})['thread']
        self.mid=self.a.action('message',{'thread':self.tid,'nonce':'first','kind':'text','text':'Original content'})['id']
    def uid(self,i):return self.users[i]['id']
    def action(self,client,action,**data):return client.action(action,dict(thread=self.tid,**data))
    def group(self,client=None):return next(t for t in (client or self.a).request('/v1/bootstrap')['threads'] if t['id']==self.tid)
    def forbidden(self,fn):
        with self.assertRaises(N.NetworkError):fn()
    def test_reactions_replace_remove_validate_and_survive_restart(self):
        self.assertEqual(self.a.messages(self.tid)['messages'][0]['reaction_version'],0)
        version=0
        for emoji in ('👍','❤️','😂','😮','😢','😡','🎉'):
            summary=self.action(self.b,'reaction',message=self.mid,emoji=emoji)
            self.assertGreater(summary['reaction_version'],version);version=summary['reaction_version']
            self.assertEqual(summary,{'thread':self.tid,'message':self.mid,'reaction_version':version,'reactions':[{'emoji':emoji,'count':1,'users':[self.uid(1)]}]})
        self.action(self.c,'reaction',message=self.mid,emoji='🎉')
        history=self.a.messages(self.tid)['messages'][0]
        self.assertEqual(history['text'],'Original content');self.assertEqual(history['reactions'][0]['count'],2)
        self.assertEqual(R.Relay(self.temp.name).messages(self.uid(0),self.tid)['messages'][0]['reactions'],history['reactions'])
        for bad in ('💜','❤️x',[],None):self.forbidden(lambda:self.action(self.b,'reaction',message=self.mid,emoji=bad))
        self.forbidden(lambda:self.action(self.outside,'reaction',message=self.mid,emoji='👍'))
        other=self.a.action('direct',{'user':self.uid(1)})['thread']
        self.forbidden(lambda:self.b.action('reaction',{'thread':other,'message':self.mid,'emoji':'👍'}))
        self.action(self.b,'reaction',message=self.mid,emoji='');self.action(self.c,'reaction',message=self.mid,emoji='')
        self.assertEqual(self.a.messages(self.tid)['messages'][0]['reactions'],[])
        summaries=self.a.request('/v1/status')['reactions']
        self.assertEqual(next(r for r in summaries if r['message']==self.mid)['reactions'],[])
    def test_creator_roles_add_admin_remove_and_history(self):
        group=self.group();self.assertEqual(group['owner'],self.uid(0));self.assertTrue(next(m for m in group['members'] if m['id']==self.uid(0))['admin'])
        self.assertTrue(self.a.request('/v1/bootstrap')['features']['message_reactions'])
        self.assertTrue(self.a.request('/v1/bootstrap')['features']['group_administration'])
        self.forbidden(lambda:self.action(self.b,'group_add',users=[self.uid(3)]))
        self.forbidden(lambda:self.action(self.b,'group_admin',user=self.uid(2),admin=True))
        self.action(self.a,'group_admin',user=self.uid(1),admin=True)
        added=self.action(self.b,'group_add',users=[self.uid(3)])
        self.assertGreater(added['membership_version'],group['membership_version']);self.assertEqual(self.d.messages(self.tid)['messages'][0]['text'],'Original content')
        self.forbidden(lambda:self.action(self.b,'group_remove',user=self.uid(0)))
        self.forbidden(lambda:self.action(self.b,'group_add',users=[self.uid(4)]))
        self.action(self.a,'group_admin',user=self.uid(2),admin=True)
        self.forbidden(lambda:self.action(self.b,'group_remove',user=self.uid(2)))
        self.action(self.b,'group_remove',user=self.uid(3));self.forbidden(lambda:self.d.messages(self.tid))
        self.action(self.a,'group_admin',user=self.uid(2),admin=False);self.action(self.b,'group_remove',user=self.uid(2))
        self.assertEqual({m['id'] for m in self.group()['members']},{self.uid(0),self.uid(1)})
    def test_reaction_cursor_paginates_offline_changes_and_deletions(self):
        app=self.server.app;ids=[]
        def cleanup():
            with app.connect() as db:
                db.executemany('DELETE FROM reactions WHERE message=?',[(mid,) for mid in ids])
                db.executemany('DELETE FROM reaction_updates WHERE message=?',[(mid,) for mid in ids])
                db.executemany('DELETE FROM messages WHERE id=?',[(mid,) for mid in ids])
        self.addCleanup(cleanup)
        with app.connect() as db:
            for i in range(205):
                mid=db.execute("INSERT INTO messages(thread,sender,kind,text,nonce,created) VALUES(?,?,'text','Cached',?,0)",(self.tid,self.uid(0),'offline-'+str(i))).lastrowid;ids.append(mid)
                db.execute('INSERT INTO reactions VALUES(?,?,?)',(mid,self.uid(1),'👍'))
                db.execute('INSERT INTO reaction_updates VALUES(?,?)',(mid,i+1))
        first=self.a.request('/v1/status?reaction_after=0')
        self.assertEqual(len(first['reactions']),200)
        self.assertGreater(first['reaction_cursor'],0)
        second=self.a.request('/v1/status?reaction_after='+str(first['reaction_cursor']))
        received={r['message'] for r in first['reactions']+second['reactions']}
        self.assertTrue(set(ids)<=received,'all offline cached messages eventually refresh')
        cursor=second['reaction_cursor']
        self.assertNotIn('reaction_cursor',self.a.messages(self.tid),'history must not advance the global reaction cursor')
        with patch.object(R.time,'time',return_value=1):
            self.action(self.b,'reaction',message=ids[-1],emoji='')
            self.action(self.b,'reaction',message=ids[0],emoji='❤️')
        changes=self.a.request('/v1/status?reaction_after='+str(cursor))
        self.assertEqual([r['message'] for r in changes['reactions']],[ids[-1],ids[0]])
        self.assertEqual(changes['reactions'][0]['reactions'],[])
        self.assertGreater(changes['reaction_cursor'],cursor)
        self.assertGreater(changes['reactions'][0]['reaction_version'],cursor)
        self.assertEqual(changes['reactions'][1]['reaction_version'],changes['reaction_cursor'])
        tombstone=next(m for m in self.a.messages(self.tid)['messages'] if m['id']==ids[-1])
        self.assertEqual(tombstone['reactions'],[]);self.assertEqual(tombstone['reaction_version'],changes['reactions'][0]['reaction_version'])
        self.assertEqual(self.a.request('/v1/status?reaction_after='+str(changes['reaction_cursor']))['reactions'],[])
        sock=self.websocket(self.a);self.send_frame(sock,'pull',{'reaction_after':cursor})
        event=self.read_frame(sock);self.assertEqual(event['event'],'status')
        self.assertEqual(event['data']['reaction_cursor'],changes['reaction_cursor'])
    def test_group_photo_rechecks_membership_at_write(self):
        app=self.server.app;original=app.member
        def remove_after_check(db,thread,uid):
            original(db,thread,uid)
            db.execute('DELETE FROM members WHERE thread=? AND uid=?',(thread,uid))
        with patch.object(app,'member',side_effect=remove_after_check):
            with self.assertRaises(R.Problem):app.call(self.uid(1),'group_photo',{'thread':self.tid,'avatar':None})
        self.assertEqual(self.group()['avatar_version'],0)
    def test_removed_member_loses_files_invites_status_and_writes(self):
        meta=self.a.request('/v1/upload',raw=b'PK\x03\x04test',mime='application/zip',name='deck.zip')
        share=self.action(self.a,'invite',file=meta['id'],summary={'title':'Study'},nonce='deck')
        invite=next(i for i in self.b.request('/v1/bootstrap')['invites'] if i['id'] in share['invitations'])
        self.assertEqual(self.b.download(meta),b'PK\x03\x04test')
        self.action(self.a,'group_remove',user=self.uid(1))
        self.forbidden(lambda:self.b.download(meta));self.forbidden(lambda:self.b.messages(self.tid))
        for action,data in [('message',{'nonce':'denied','text':'Denied'}),('reaction',{'message':self.mid,'emoji':'👍'}),('typing',{'typing':True}),('read',{'last':self.mid}),('invite',{'file':meta['id'],'summary':{},'nonce':'no'})]:
            self.forbidden(lambda:self.action(self.b,action,**data))
        self.forbidden(lambda:self.b.action('invite_state',{'id':invite['id'],'state':'accepted'}))
        boot=self.b.request('/v1/bootstrap');self.assertFalse(any(i['thread']==self.tid for i in boot['invites']))
        status=self.b.request('/v1/status');self.assertFalse(any(g['thread']==self.tid for g in status['group_memberships']));self.assertFalse(any(r['thread']==self.tid for r in status['reactions']))
    def test_owner_leave_randomly_promotes_and_last_leave_archives(self):
        with patch.object(R.secrets,'choice',side_effect=lambda users:users[-1]) as choose:
            result=self.action(self.a,'group_leave');self.assertEqual(choose.call_count,1)
        self.assertIn(result['owner'],(self.uid(1),self.uid(2)));owner=result['owner']
        group=self.group(self.b);self.assertTrue(next(m for m in group['members'] if m['id']==owner)['admin'])
        self.forbidden(lambda:self.a.messages(self.tid))
        self.action(self.b,'group_leave');self.action(self.c,'group_leave')
        with self.server.app.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM members WHERE thread=?',(self.tid,)).fetchone()[0],0)
            self.assertEqual(db.execute("SELECT count(*) FROM messages WHERE thread=? AND kind='text'",(self.tid,)).fetchone()[0],1)
            self.assertEqual(db.execute("SELECT count(*) FROM messages WHERE thread=? AND kind='system' AND text LIKE '% left the group.'",(self.tid,)).fetchone()[0],3)
            self.assertIn(db.execute("SELECT count(*) FROM messages WHERE thread=? AND kind='system' AND text LIKE '% became the group owner.'",(self.tid,)).fetchone()[0],(1,2))
        self.forbidden(lambda:self.action(self.a,'group_add',users=[self.uid(1)]))
    def test_legacy_owner_claim_is_opt_in_and_preserves_other_groups(self):
        unrelated=self.b.action('group',{'title':'Unrelated','users':[self.uid(3)]})['thread']
        with self.server.app.connect() as db:db.execute('UPDATE threads SET owner=NULL WHERE id IN (?,?)',(self.tid,unrelated))
        with patch.dict(os.environ,{},clear=True):self.forbidden(lambda:self.a.action('claim_legacy_groups',{}))
        with patch.dict(os.environ,{'ANKI_LINK_LEGACY_OWNER_USERNAME':'jigstar'}):
            self.forbidden(lambda:self.b.action('claim_legacy_groups',{}))
            result=self.a.action('claim_legacy_groups',{});self.assertIn(self.tid,result['claimed']);self.assertNotIn(unrelated,result['claimed'])
        self.assertEqual(self.group()['owner'],self.uid(0))
    def websocket(self,client):
        sock=socket.create_connection(('127.0.0.1',self.server.server_port),timeout=2)
        key=base64.b64encode(os.urandom(16)).decode();sock.sendall(('GET /v1/live HTTP/1.1\r\nHost: localhost\r\nAuthorization: Bearer '+client.token+'\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Version: 13\r\nSec-WebSocket-Key: '+key+'\r\n\r\n').encode())
        headers=b''
        while not headers.endswith(b'\r\n\r\n'):headers+=sock.recv(1)
        self.assertIn(b'101',headers);self.read_frame(sock);self.addCleanup(sock.close);return sock
    def read_frame(self,sock):
        def read(n):
            out=b''
            while len(out)<n:
                part=sock.recv(n-len(out))
                if not part:raise EOFError()
                out+=part
            return out
        head=read(2);size=head[1]&127
        if size==126:size=struct.unpack('!H',read(2))[0]
        elif size==127:size=struct.unpack('!Q',read(8))[0]
        return json.loads(read(size))
    def send_frame(self,sock,action,data):
        raw=json.dumps({'action':action,'data':data}).encode();mask=b'abcd'
        head=bytes([129,128|len(raw)]) if len(raw)<126 else bytes([129,254])+struct.pack('!H',len(raw))
        sock.sendall(head+mask+bytes(b^mask[i%4] for i,b in enumerate(raw)))
    def test_live_reactions_and_removed_socket_receives_no_future_content(self):
        sock=self.websocket(self.b)
        self.action(self.a,'reaction',message=self.mid,emoji='👍')
        event=self.read_frame(sock);self.assertEqual(event['event'],'reaction_updated');self.assertEqual(event['data']['message'],self.mid)
        removed=self.action(self.a,'group_remove',user=self.uid(1));event=self.read_frame(sock);self.assertEqual(event['event'],'group_removed');self.assertEqual(event['data']['membership_version'],removed['membership_version'])
        self.action(self.a,'message',nonce='secret',text='Private future')
        self.send_frame(sock,'message',{'thread':self.tid,'nonce':'cached','text':'Denied'})
        event=self.read_frame(sock);self.assertEqual(event['event'],'live_error')
        self.send_frame(sock,'pull',{});event=self.read_frame(sock)
        self.assertEqual(event['event'],'status');self.assertFalse(any(g['thread']==self.tid for g in event['data']['group_memberships']))
    def test_live_pull_detects_removal_from_another_process_with_version(self):
        sock=self.websocket(self.b)
        # A second server process cannot publish through this process's peer registry.
        removed=R.Relay(self.temp.name).call(self.uid(0),'group_remove',{'thread':self.tid,'user':self.uid(1)})
        self.send_frame(sock,'pull',{})
        event=self.read_frame(sock);self.assertEqual(event['event'],'group_removed')
        self.assertEqual(event['data'],{'thread':self.tid,'membership_version':removed['membership_version']})
        self.assertEqual(self.read_frame(sock)['event'],'status')


if __name__=='__main__':unittest.main()
