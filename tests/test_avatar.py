"""Withheld upload/save replies verify visible stages and retry/account safety."""
from pathlib import Path
import hashlib
import tempfile
import types
import unittest
from unittest.mock import patch
import test_message_controller as base
D=base.D

class AvatarFlow(unittest.TestCase):
    setUpBase=base.MessageController.setUp
    finish=base.MessageController.finish
    def setUp(self):
        self.setUpBase();self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.source=self.root/'photo.png';self.source.write_bytes(b'prepared photo');c=self.c;c.temp=types.SimpleNamespace(name=self.temp.name);c.blobs=set();c.store.folder=self.root;c.store.save=lambda:None
        c.store.data.update(url='https://server.test',user={'id':'me','name':'Me','avatar':None});c.social={'user':dict(c.store.data['user'])};c.poll=lambda **kwargs:None;c.choose_avatar_crop=lambda path:path
        self.meta={'id':'photo-id','mime':'image/png','name':'photo.png','size':len(self.source.read_bytes()),'sha256':hashlib.sha256(self.source.read_bytes()).hexdigest()};self.calls=[];self.upload_error=False;self.save_error=False
        def request(path,**kwargs):
            self.calls.append((path,kwargs))
            if path=='/v1/upload':
                if self.upload_error:raise OSError('Upload interrupted')
                return self.meta
            if self.save_error:raise OSError('Save was not confirmed')
            return {'user':{'id':'me','name':'Me','avatar':None if kwargs['data']['avatar'] is None else self.meta}}
        c.client().request=request
        self.patches=[patch.object(D,'QFileDialog',types.SimpleNamespace(getOpenFileName=lambda *args:(str(self.source),''))),patch.object(D.media,'prepare_avatar',return_value=self.source)]
        for p in self.patches:p.start();self.addCleanup(p.stop)
    def stages(self):return [d['phase'] for e,d in self.events if e=='profile_progress']
    def test_preview_and_each_stage_appear_before_waiting_for_network(self):
        self.c.set_avatar({'request':'one'});self.assertEqual(self.stages(),['choosing','preparing']);self.assertEqual(self.calls,[])
        self.finish(0);self.assertEqual(self.stages()[-1],'uploading');self.assertTrue(self.events[-1][1]['preview'].startswith('data:image/png;base64,'));self.assertEqual(self.calls,[])
        self.finish(1);self.assertEqual(self.stages()[-1],'saving');self.assertEqual(len(self.calls),1)
        self.finish(2);self.assertEqual(self.events[-2][0],'blob');self.assertEqual(self.events[-1][0],'profile_updated');self.assertIsNone(self.c.avatar_job)
        self.assertEqual(self.c.store.data['user']['avatar'],self.meta);self.assertTrue(all(kwargs['background'] for _,kwargs in self.calls));self.assertEqual(len(self.jobs),3,'no self-download is needed')
    def test_upload_failure_is_retryable_without_reselecting_file(self):
        self.c.set_avatar({'request':'one'});self.finish(0);self.upload_error=True;self.finish(1)
        self.assertEqual(self.stages()[-1],'failed');self.assertTrue(self.events[-1][1]['retryable']);self.assertIsNone(self.c.store.data['user']['avatar'])
        self.upload_error=False;self.c.retry_avatar('one');self.finish(2);self.finish(3)
        self.assertEqual(self.events[-1][0],'profile_updated');self.assertEqual(len([p for p,_ in self.calls if p=='/v1/upload']),2)
    def test_retry_after_save_failure_reuses_uploaded_file(self):
        self.c.set_avatar({'request':'one'});self.finish(0);self.finish(1);self.save_error=True;self.finish(2);self.assertEqual(self.stages()[-1],'failed')
        self.save_error=False;self.c.retry_avatar('one');self.finish(3)
        self.assertEqual(len([p for p,_ in self.calls if p=='/v1/upload']),1);self.assertEqual(self.events[-1][0],'profile_updated')
    def test_cancel_crop_does_not_start_upload(self):
        self.c.choose_avatar_crop=lambda path:None;self.c.set_avatar({'request':'crop'});self.finish(0)
        self.assertEqual(self.stages()[-2:],['cropping','cancelled']);self.assertEqual(self.calls,[]);self.assertIsNone(self.c.avatar_job)
    def test_cancel_restores_idle_and_never_sends(self):
        with patch.object(D,'QFileDialog',types.SimpleNamespace(getOpenFileName=lambda *args:('',''))):self.c.set_avatar({'request':'one'})
        self.assertEqual(self.stages()[-1],'cancelled');self.assertEqual(self.jobs,[]);self.assertIsNone(self.c.avatar_job)
    def test_account_change_discards_old_callback_and_cannot_retry_it(self):
        self.c.set_avatar({'request':'one'});self.finish(0);self.c.epoch+=1;before=len(self.events);self.finish(1);self.c.retry_avatar('one')
        self.assertEqual(len(self.events),before);self.assertIsNone(self.c.store.data['user']['avatar']);self.assertEqual(len(self.jobs),2)
    def test_duplicate_click_does_not_start_second_job(self):
        self.c.set_avatar({'request':'one'});self.c.set_avatar({'request':'two'});self.assertEqual(len(self.jobs),1);self.assertEqual(self.c.avatar_job['id'],'one')
    def test_remove_shows_saving_and_restores_on_failure(self):
        self.c.store.data['user']['avatar']=self.meta;self.save_error=True;self.c.set_avatar({'request':'remove','remove':True})
        self.assertEqual(self.stages(),['saving']);self.finish(0);self.assertEqual(self.stages()[-1],'failed');self.assertEqual(self.c.store.data['user']['avatar'],self.meta)
        self.save_error=False;self.c.retry_avatar('remove');self.finish(1);self.assertIsNone(self.c.store.data['user']['avatar']);self.assertTrue(self.events[-1][1]['remove'])

if __name__=='__main__':unittest.main()
