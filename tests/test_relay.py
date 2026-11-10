import base64
import importlib
from pathlib import Path
import sys
import tempfile
import threading
import types
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'server'))
from server import make_server,Problem
pkg=types.ModuleType('anki_link');pkg.__path__=[str(ROOT/'anki_link')];sys.modules.setdefault('anki_link',pkg)
N=importlib.import_module('anki_link.net')

PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aRZkAAAAASUVORK5CYII=')

class RelayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.server=make_server(port=0,directory=cls.temp.name,join_code='private-test')
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start();cls.url='http://127.0.0.1:'+str(cls.server.server_port)
        cls.clients=[];cls.users=[]
        for i in range(3):
            c=N.Client(cls.url);session=c.request('/v1/register',data={'username':'person'+str(i),'name':['Jay','Partner','Other person'][i],'password':'a strong test password','join_code':'private-test'});c.token=session['token'];cls.clients.append(c);cls.users.append(session['user'])
        cls.a,cls.b,cls.other=cls.clients
        cls.a.action('friend_request',{'code':cls.users[1]['code']});cls.b.action('friend_decide',{'user':cls.users[0]['id'],'accept':True});cls.tid=cls.a.action('direct',{'user':cls.users[1]['id']})['thread']
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join(2);cls.temp.cleanup()
    def test_sign_in_separate_accounts_and_wrong_password(self):
        c=N.Client(self.url);result=c.request('/v1/login',data={'username':'person0','password':'a strong test password'});self.assertEqual(result['user']['id'],self.users[0]['id'])
        with self.assertRaises(N.NetworkError):c.request('/v1/login',data={'username':'person0','password':'wrong password'})
    def test_private_server_invitation_required(self):
        with self.assertRaises(N.NetworkError):N.Client(self.url).request('/v1/register',data={'username':'outsider','password':'a strong test password','join_code':'wrong'})
    def test_unicode_emoji_idempotency_and_persistent_offline_delivery(self):
        data={'thread':self.tid,'kind':'text','text':'Good luck 💜\nYou got this, ñ!','nonce':'same-message'}
        one=self.a.action('message',data);two=self.a.action('message',data);self.assertEqual(one,two)
        fresh=N.Client(self.url,self.b.token);messages=fresh.messages(self.tid)['messages'];matches=[m for m in messages if m['nonce']=='same-message'];self.assertEqual(len(matches),1);self.assertEqual(matches[0]['text'],data['text'])
    def test_nonmember_cannot_read_or_write_messages(self):
        with self.assertRaises(N.NetworkError):self.other.messages(self.tid)
        with self.assertRaises(N.NetworkError):self.other.action('message',{'thread':self.tid,'kind':'text','text':'Nope','nonce':'bad'})
    def test_images_stickers_and_private_file_downloads(self):
        meta=self.a.request('/v1/upload',raw=PNG,mime='image/png',name='study.png')
        with self.assertRaises(N.NetworkError):self.b.download(meta)
        self.a.action('message',{'thread':self.tid,'kind':'image','file':meta['id'],'nonce':'image-one'})
        self.assertEqual(self.b.download(meta),PNG)
        with self.assertRaises(N.NetworkError):self.other.download(meta)
        self.a.action('message',{'thread':self.tid,'kind':'sticker','text':'cheer','nonce':'sticker-one'})
        with self.assertRaises(N.NetworkError):self.b.action('message',{'thread':self.tid,'kind':'sticker','file':meta['id'],'nonce':'borrow-other-owner'})
        self.a.action('message',{'thread':self.tid,'kind':'sticker','file':meta['id'],'nonce':'custom-sticker'})
        self.assertTrue(any(m['kind']=='sticker' and m.get('attachment') for m in self.b.messages(self.tid)['messages']))
    def test_svg_and_disguised_uploads_are_rejected(self):
        for mime,raw in [('image/svg+xml',b'<svg/>'),('image/png',b'<script>bad</script>'),('text/html',b'<html/>')]:
            with self.assertRaises(N.NetworkError):self.a.request('/v1/upload',raw=raw,mime=mime,name='bad.png')
    def test_deck_invitations_accept_reject_idempotency_and_no_import_before_accept(self):
        meta=self.a.request('/v1/upload',raw=b'PK\x03\x04test-package',mime='application/zip',name='test.alink')
        payload={'recipients':[self.users[1]['id']],'file':meta['id'],'summary':{'title':'Midterms::Science','cards':80,'new_cards':20,'settings':True,'progress':False,'filtered_decks':1},'nonce':'invite-one'}
        one=self.a.action('invite',payload);two=self.a.action('invite',payload);self.assertEqual(one,two);iid=one['invitations'][0]
        invite=next(x for x in self.b.request('/v1/bootstrap')['invites'] if x['id']==iid);self.assertEqual(invite['state'],'pending');self.assertEqual(invite['attachment']['sha256'],meta['sha256'])
        self.b.action('invite_state',{'id':iid,'state':'accepted','result':{'cards':80}});self.b.action('invite_state',{'id':iid,'state':'accepted'})
        with self.assertRaises(N.NetworkError):self.b.action('invite_state',{'id':iid,'state':'rejected'})
        with self.assertRaises(N.NetworkError):self.other.action('invite_state',{'id':iid,'state':'accepted'})
        payload['nonce']='invite-two';iid=self.a.action('invite',payload)['invitations'][0];self.b.action('invite_state',{'id':iid,'state':'rejected'})
        self.assertEqual(next(x for x in self.a.request('/v1/bootstrap')['invites'] if x['id']==iid)['state'],'rejected')
    def test_read_receipts_and_unread_counts(self):
        m=self.a.action('message',{'thread':self.tid,'kind':'text','text':'A new message','nonce':'read-test'})
        before=self.b.request('/v1/bootstrap');self.assertGreater(next(t for t in before['threads'] if t['id']==self.tid)['unread'],0)
        self.b.action('read',{'thread':self.tid,'last':m['id']});after=self.b.request('/v1/bootstrap');self.assertEqual(next(t for t in after['threads'] if t['id']==self.tid)['unread'],0)
    def test_invite_nonfriend_and_group_nonfriend_rejected(self):
        with self.assertRaises(N.NetworkError):self.a.action('direct',{'user':self.users[2]['id']})
        with self.assertRaises(N.NetworkError):self.a.action('group',{'title':'No','users':[self.users[2]['id']]})
    def test_group_membership_and_message(self):
        group=self.a.action('group',{'title':'Study corner','users':[self.users[1]['id']]})['thread'];self.b.action('message',{'thread':group,'kind':'text','text':'Hello group','nonce':'group-one'})
        self.assertEqual(self.a.messages(group)['messages'][0]['text'],'Hello group')
        with self.assertRaises(N.NetworkError):self.other.messages(group)
    def test_public_plain_http_and_credential_urls_blocked(self):
        for address in ('http://example.com','https://user:pass@example.com','https://example.com/path','https://example.com?token=bad'):
            with self.assertRaises(ValueError):N.server_url(address)

if __name__=='__main__':unittest.main()
