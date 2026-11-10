"""Group photo/member persistence, authorization, and delayed native photo jobs."""
import hashlib
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
import test_relay
import server as R
import test_message_controller as base
D=base.D

class GroupRelay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.relay=R.Relay(cls.temp.name)
        cls.users=[cls.relay.authenticate({'username':name,'name':name.title(),'password':'a strong test password'},True)['user'] for name in ('alex','bea','cai','dana')]
        cls.a,cls.b,cls.c,cls.d=cls.users
        # Bea is friends with Alex/Cai. Alex and Cai are groupmates only.
        for one,two in [(cls.b,cls.a),(cls.b,cls.c),(cls.a,cls.d)]:
            cls.relay.call(one['id'],'friend_request',{'code':two['code']});cls.relay.call(two['id'],'friend_decide',{'user':one['id'],'accept':True})
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def setUp(self):
        self.tid=self.relay.call(self.b['id'],'group',{'title':'Study team','users':[self.a['id'],self.c['id']]})['thread']
        self.image=self.relay.upload(self.a['id'],'photo.png','image/png',test_relay.PNG)
    def change(self,who,avatar):return self.relay.call(who['id'],'group_photo',{'thread':self.tid,'avatar':avatar})
    def test_all_members_can_see_names_and_photo_including_nonfriend_groupmates(self):
        with self.relay.connect() as db:self.assertFalse(self.relay.can_read_file(db,self.image['id'],self.c['id']))
        saved=self.change(self.a,self.image['id']);self.assertEqual(saved['avatar_version'],1)
        group=next(t for t in self.relay.bootstrap(self.c['id'])['threads'] if t['id']==self.tid)
        self.assertEqual({p['name'] for p in group['members']},{'Alex','Bea','Cai'});self.assertEqual(group['avatar'],self.image)
        with self.relay.connect() as db:self.assertTrue(self.relay.can_read_file(db,self.image['id'],self.c['id']))
    def test_friend_outside_group_cannot_read_or_change_group_photo(self):
        self.change(self.a,self.image['id'])
        with self.relay.connect() as db:self.assertFalse(self.relay.can_read_file(db,self.image['id'],self.d['id']))
        own=self.relay.upload(self.d['id'],'own.png','image/png',test_relay.PNG)
        with self.assertRaises(R.Problem) as caught:self.change(self.d,own['id'])
        self.assertEqual(caught.exception.status,404)
        self.assertFalse(any(t['id']==self.tid for t in self.relay.bootstrap(self.d['id'])['threads']))
    def test_photo_can_be_changed_removed_and_survives_server_restart(self):
        self.change(self.a,self.image['id']);second=self.relay.upload(self.c['id'],'second.png','image/png',test_relay.PNG)
        self.assertEqual(self.change(self.c,second['id'])['avatar_version'],2)
        again=R.Relay(self.temp.name);t=next(t for t in again.bootstrap(self.a['id'])['threads'] if t['id']==self.tid)
        self.assertEqual(t['avatar'],second);self.assertEqual(t['avatar_version'],2)
        removed=self.change(self.b,None);self.assertIsNone(removed['avatar']);self.assertEqual(removed['avatar_version'],3)
        with self.relay.connect() as db:self.assertFalse(self.relay.can_read_file(db,self.image['id'],self.c['id']))
    def test_other_users_files_and_nonimages_are_rejected(self):
        with self.assertRaises(R.Problem):self.change(self.c,self.image['id'])
        zipfile=self.relay.upload(self.a['id'],'deck.zip','application/zip',b'PK\x03\x04fixture')
        with self.assertRaises(R.Problem):self.change(self.a,zipfile['id'])
        large=self.relay.upload(self.a['id'],'large.png','image/png',test_relay.PNG+b'x'*(2*1024*1024))
        with self.assertRaises(R.Problem):self.change(self.a,large['id'])
    def test_direct_conversation_photo_cannot_be_changed(self):
        direct=self.relay.call(self.a['id'],'direct',{'user':self.b['id']})['thread']
        with self.assertRaises(R.Problem):self.relay.call(self.a['id'],'group_photo',{'thread':direct,'avatar':self.image['id']})

class GroupPhotoController(unittest.TestCase):
    finish=base.MessageController.finish
    def setUp(self):
        base.MessageController.setUp(self);self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.source=self.root/'photo.png';self.source.write_bytes(b'cropped image fixture')
        c=self.c;c.temp=types.SimpleNamespace(name=self.temp.name);c.blobs=set();c.store.folder=self.root;c.store.data.update(url='https://test.invalid',user={'id':'me','avatar':{'id':'personal'}});c.store.save=lambda:None
        c.social={'user':c.store.data['user'],'threads':[{'id':'group','kind':'group','title':'Team','members':[{'id':'me'}],'avatar':None,'avatar_version':0}]};c.poll=lambda **kw:None
        c.choose_group_crop=lambda path:path;c.avatar_job={'id':'independent-personal-job'}
        raw=self.source.read_bytes();self.meta={'id':'group-photo','mime':'image/png','name':'photo.png','size':len(raw),'sha256':hashlib.sha256(raw).hexdigest()};self.calls=[];self.upload_error=False;self.save_error=False
        def request(path,**kw):
            self.calls.append((path,kw))
            if self.upload_error:raise OSError('Upload interrupted')
            return self.meta
        def action(name,data):
            self.calls.append((name,data))
            if self.save_error:raise OSError('Save interrupted')
            return {'thread':data['thread'],'avatar':None if data['avatar'] is None else self.meta,'avatar_version':1}
        c.client().request=request;c.client().action=action
        self.patches=[patch.object(D,'QFileDialog',types.SimpleNamespace(getOpenFileName=lambda *args:(str(self.source),''))),patch.object(D.media,'prepare_avatar',return_value=self.source)]
        for p in self.patches:p.start();self.addCleanup(p.stop)
    def stages(self):return [data['phase'] for event,data in self.events if event=='group_photo_progress']
    def start(self):self.c.set_group_avatar({'thread':'group','request':'request'})
    def test_progress_precedes_network_and_saving_never_changes_personal_profile(self):
        self.start();self.assertEqual(self.stages(),['choosing','preparing']);self.assertEqual(self.calls,[])
        self.finish(0);self.assertEqual(self.stages()[-2:],['cropping','uploading']);self.assertTrue(self.events[-1][1]['preview'].startswith('data:image/png;base64,'))
        self.finish(1);self.assertEqual(self.stages()[-1],'saving');self.finish(2)
        self.assertEqual(self.events[-1][0],'group_photo_saved');self.assertEqual(self.c.social['threads'][0]['avatar'],self.meta)
        self.assertEqual(self.c.store.data['user']['avatar'],{'id':'personal'});self.assertEqual(self.c.avatar_job['id'],'independent-personal-job')
        self.assertTrue(self.calls[0][1]['bulk']);self.assertFalse(self.c.group_avatar_jobs)
    def test_save_retry_reuses_uploaded_file_and_exact_group(self):
        self.start();self.finish(0);self.finish(1);self.save_error=True;self.finish(2)
        self.assertEqual(self.stages()[-1],'failed');self.save_error=False;self.c.retry_group_avatar('group','request');self.finish(3)
        self.assertEqual(len([name for name,_ in self.calls if name=='/v1/upload']),1)
        self.assertEqual(self.events[-1][0],'group_photo_saved')
    def test_cancel_crop_does_not_upload(self):
        self.c.choose_group_crop=lambda path:None;self.start();self.finish(0)
        self.assertEqual(self.stages()[-1],'cancelled');self.assertEqual(self.calls,[]);self.assertFalse(self.c.group_avatar_jobs)
    def test_duplicate_click_and_wrong_retry_id_do_not_start_more_work(self):
        self.start();self.start();self.assertEqual(len(self.jobs),1)
        self.finish(0);self.upload_error=True;self.finish(1);self.c.retry_group_avatar('group','wrong');self.assertEqual(len(self.jobs),2)
        self.upload_error=False;self.c.retry_group_avatar('group','request');self.finish(2);self.finish(3)
        self.assertEqual(self.events[-1][0],'group_photo_saved')
    def test_old_profile_completion_and_retry_cannot_update_a_new_account(self):
        self.start();self.finish(0);self.c.epoch+=1;self.c.reset_session_work();before=len(self.events);self.finish(1);self.c.retry_group_avatar('group','request')
        self.assertEqual(len(self.events),before);self.assertEqual(self.c.group_photos,{})
    def test_remove_uses_no_upload_and_shows_visible_saving(self):
        self.c.set_group_avatar({'thread':'group','request':'remove','remove':True});self.assertEqual(self.stages(),['saving']);self.finish(0)
        self.assertEqual(self.calls,[('group_photo',{'thread':'group','avatar':None})]);self.assertEqual(self.events[-1][0],'group_photo_saved')
    def test_stale_live_update_cannot_undo_a_newer_photo(self):
        self.c.live_event('group_updated',{'thread':'group','avatar':self.meta,'avatar_version':2})
        self.c.live_event('group_updated',{'thread':'group','avatar':None,'avatar_version':1})
        self.assertEqual(self.c.social['threads'][0]['avatar'],self.meta);self.assertEqual(len(self.events),1)

if __name__=='__main__':unittest.main()
