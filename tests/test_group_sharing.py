"""Three-member group delivery, private decisions, retries and authorization."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import threading
import unittest
import uuid
from test_relay import N,make_server


class GroupSharing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.server=make_server(port=0,directory=cls.tmp.name,join_code='test-only')
        cls.worker=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.worker.start();cls.url='http://127.0.0.1:'+str(cls.server.server_port)
        cls.clients=[];cls.users=[]
        for i in range(4):
            client=N.Client(cls.url);session=client.request('/v1/register',data={'username':'groupuser'+str(i),'name':'Person '+str(i),'password':'a strong test password','join_code':'test-only'})
            client.token=session['token'];cls.clients.append(client);cls.users.append(session['user'])
        cls.a,cls.b,cls.c,cls.outsider=cls.clients
        for i in (1,2):
            cls.a.action('friend_request',{'code':cls.users[i]['code']});cls.clients[i].action('friend_decide',{'user':cls.users[0]['id'],'accept':True})
        cls.group=cls.a.action('group',{'title':'Study group','users':[cls.users[1]['id'],cls.users[2]['id']]})['thread']
        path=Path(cls.tmp.name)/'deck.alink';path.write_bytes(b'PK\x03\x04synthetic deck');cls.file=cls.b.upload(path,'application/zip')
    @classmethod
    def tearDownClass(cls):
        for client in cls.clients:client.close()
        cls.server.shutdown();cls.server.server_close();cls.worker.join(2);cls.tmp.cleanup()
    def payload(self):return {'thread':self.group,'file':self.file['id'],'summary':{'title':'Science','cards':60,'settings':True,'progress':False},'nonce':uuid.uuid4().hex}
    def test_group_message_once_no_private_threads_and_each_member_gets_own_invite(self):
        before=[{t['id'] for t in client.request('/v1/bootstrap')['threads']} for client in (self.a,self.b,self.c)]
        data=self.payload();result=self.b.action('invite',data);self.assertEqual(result['thread'],self.group);self.assertEqual(len(result['invitations']),2)
        for client,uid,threads in zip((self.a,self.b,self.c),(u['id'] for u in self.users),before):
            boot=client.request('/v1/bootstrap');self.assertTrue(boot['features']['group_deck_shares']);self.assertEqual({t['id'] for t in boot['threads']},threads)
            frame=client.messages(self.group);messages=[m for m in frame['messages'] if m['nonce']==data['nonce']];self.assertEqual(len(messages),1)
            invitations=[i for i in frame['invites'] if i['nonce']==data['nonce']]
            if client is not self.b:self.assertEqual([i['recipient'] for i in invitations],[uid]);self.assertEqual(messages[0]['invite'],invitations[0]['id'])
            else:self.assertEqual(len(invitations),2)
        self.assertFalse(any(t['kind']=='direct' and {p['id'] for p in t['members']}=={self.users[1]['id'],self.users[2]['id']} for t in self.b.request('/v1/bootstrap')['threads']))
    def test_independent_accept_decline_file_acl_and_foreign_invite_rejected(self):
        data=self.payload();self.b.action('invite',data)
        ai=next(i for i in self.a.messages(self.group)['invites'] if i['nonce']==data['nonce'])
        ci=next(i for i in self.c.messages(self.group)['invites'] if i['nonce']==data['nonce'])
        self.assertNotEqual(ai['id'],ci['id']);self.assertEqual(self.a.download(ai['attachment']),b'PK\x03\x04synthetic deck')
        self.a.action('invite_state',{'id':ai['id'],'state':'accepted','result':{'cards':60}})
        self.c.action('invite_state',{'id':ci['id'],'state':'rejected'})
        states={i['recipient']:i['state'] for i in self.b.request('/v1/bootstrap')['invites'] if i['nonce']==data['nonce']}
        self.assertEqual(states,{self.users[0]['id']:'accepted',self.users[2]['id']:'rejected'})
        with self.assertRaises(N.NetworkError):self.c.action('invite_state',{'id':ai['id'],'state':'accepted'})
        with self.assertRaises(N.NetworkError):self.outsider.download(ai['attachment'])
        with self.assertRaises(N.NetworkError):self.outsider.messages(self.group)
    def test_concurrent_retries_are_one_share_and_do_not_reset_decisions(self):
        data=self.payload()
        def send(_):
            client=N.Client(self.url,self.b.token)
            try:return client.action('invite',data)
            finally:client.close()
        with ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(send,range(3)))
        self.assertTrue(all(value==results[0] for value in results));self.assertEqual(len(results[0]['invitations']),2)
        frame=self.a.messages(self.group);row=next(i for i in frame['invites'] if i['nonce']==data['nonce'])
        self.a.action('invite_state',{'id':row['id'],'state':'accepted'});self.b.action('invite',data)
        self.assertEqual(next(i for i in self.a.messages(self.group)['invites'] if i['id']==row['id'])['state'],'accepted')
        self.assertEqual(len([m for m in self.a.messages(self.group)['messages'] if m['nonce']==data['nonce']]),1)
    def test_member_recipient_list_is_server_derived_and_invalid_destinations_fail(self):
        data=self.payload();data['recipients']=[self.users[3]['id']];self.b.action('invite',data)
        self.assertFalse(any(i['nonce']==data['nonce'] for i in self.outsider.request('/v1/bootstrap')['invites']))
        with self.assertRaises(N.NetworkError):self.outsider.action('invite',self.payload())
        direct=next(t['id'] for t in self.a.request('/v1/bootstrap')['threads'] if t['kind']=='direct')
        invalid=self.payload();invalid['thread']=direct
        with self.assertRaises(N.NetworkError):self.a.action('invite',invalid)
        invalid=self.payload();invalid['file']='missing'
        with self.assertRaises(N.NetworkError):self.b.action('invite',invalid)
    def test_new_share_adds_another_update_and_history_retains_personal_metadata(self):
        first=self.payload();self.b.action('invite',first);second=self.payload();second['summary']['cards']=80;self.b.action('invite',second)
        frame=self.c.messages(self.group);self.assertEqual({i['summary']['cards'] for i in frame['invites'] if i['nonce'] in (first['nonce'],second['nonce'])},{60,80})
        ids=[m['id'] for m in frame['messages'] if m['nonce'] in (first['nonce'],second['nonce'])]
        older=self.c.messages(self.group,before=max(ids));self.assertTrue(any(i['nonce']==first['nonce'] for i in older['invites']))


if __name__=='__main__':unittest.main()
