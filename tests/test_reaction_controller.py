"""Delayed membership snapshots, revoked media, and group preview completions."""
import copy
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
import test_message_controller as base
D=base.D

class RevocationController(unittest.TestCase):
    finish=base.MessageController.finish
    def setUp(self):
        base.MessageController.setUp(self)
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        c=self.c;c.active_thread=None;c.previews={};c.blobs=set();c.preparing=set();c.blob_queue=[];c.blob_active=0
        c.temp=types.SimpleNamespace(name=self.temp.name);c.store.folder=Path(self.temp.name);c.store.data.update(url='https://test.invalid',user={'id':'me'})
        c.notification_bootstrap=lambda *args,**kw:None
        self.group={'id':'group','kind':'group','title':'Team','membership_version':1,'members':[{'id':'me'}],'unread':0}
        c.social=self.boot(1)
        self.snapshot=self.boot(2);c.client().request=lambda path:copy.deepcopy(self.snapshot)
    def boot(self,version):
        return {'user':{'id':'me'},'invites':[],'friends':[],'threads':[{**self.group,'membership_version':version}]}
    def test_actual_removal_version_blocks_pre_removal_and_equal_bootstraps(self):
        c=self.c;c.poll(force=True);c.live_event('group_removed',{'thread':'group','membership_version':3});self.finish(0)
        self.assertEqual(c.social['threads'],[]);self.assertEqual(c.removed_groups['group'],3)
        self.snapshot=self.boot(3);c.poll(force=True);self.finish(1);self.assertEqual(c.social['threads'],[])
        self.snapshot=self.boot(4);c.poll(force=True);self.finish(2);self.assertEqual(c.social['threads'][0]['id'],'group')
    def test_legacy_removal_requires_bootstrap_started_after_removal(self):
        c=self.c;c.poll(force=True);c.live_event('group_removed',{'thread':'group'});self.finish(0)
        self.assertEqual(c.social['threads'],[])
        c.poll(force=True);self.finish(1);self.assertEqual(c.social['threads'][0]['id'],'group')
    def test_stale_message_status_omission_is_not_forwarded_to_webview(self):
        c=self.c;c.active_thread='group';c.client().messages=lambda *args,**kw:{'messages':[],'group_memberships':[]}
        c.poll_messages('group');c.membership_epoch=1;self.finish(0)
        payload=next(data for event,data in self.events if event=='messages')
        self.assertNotIn('group_memberships',payload);self.assertEqual(c.social['threads'][0]['id'],'group')
    def test_stale_removal_cannot_remove_later_membership(self):
        self.c.social=self.boot(4);self.c.remove_group('group',3)
        self.assertEqual(self.c.social['threads'][0]['membership_version'],4)
    def test_stale_http_status_omission_cannot_remove_fresh_bootstrap(self):
        c=self.c;old_epoch=getattr(c,'membership_epoch',0);c.poll(force=True);self.finish(0)
        c.live_event('status',{'group_memberships':[]},old_epoch)
        self.assertEqual(c.social['threads'][0]['id'],'group');self.assertFalse(getattr(c,'removed_groups',{}))
    def test_rejoin_restores_photo_and_avatar_but_old_download_stays_invalid(self):
        c=self.c;photo={'id':'photo','mime':'image/png'};avatar={'id':'avatar','mime':'image/png'};c.social['threads'][0]['avatar']=avatar
        c.client().download=lambda meta:b'image fixture'
        with patch.object(D.media,'cache_path',return_value=None):
            c.blob({**photo,'_thread':'group'});c.blob({**avatar,'_thread':'group'})
            c.live_event('group_removed',{'thread':'group','membership_version':3})
            self.finish(0);self.assertNotIn('photo',c.blobs)
            c.blob({**photo,'_thread':'group'});self.assertEqual(len(self.jobs),2,'absent group cannot restart media')
            self.snapshot=self.boot(4);self.snapshot['threads'][0]['avatar']=avatar;c.poll(force=True);self.finish(2)
            c.blob({**photo,'_thread':'group'});c.blob({**avatar,'_thread':'group'})
            self.finish(1);self.assertNotIn('avatar',c.blobs,'pre-removal completion stays invalid after rejoin')
            self.finish(3);self.finish(4)
            self.assertEqual(c.blobs,{'photo','avatar'});self.assertFalse(c.revoked_files)
    def test_reaction_cursor_advances_only_from_valid_status_and_resets(self):
        c=self.c;c.live_event('status',{'reaction_cursor':12});self.assertEqual(c.reaction_cursor,12)
        c.live_event('messages',{'thread':'group','messages':[],'reaction_cursor':999});self.assertEqual(c.reaction_cursor,12)
        for cursor in (8,-1,float('inf'),float('nan'),'100',True):c.live_event('status',{'reaction_cursor':cursor})
        self.assertEqual(c.reaction_cursor,12)
        c.membership_epoch=2;c.live_event('status',{'reaction_cursor':100},1);self.assertEqual(c.reaction_cursor,12)
        c.reset_session_work();self.assertEqual(c.reaction_cursor,0)
    def test_old_preview_query_stays_invalid_after_rejoin(self):
        callbacks=[]
        class Query:
            def __init__(self,**kw):callbacks.append(kw['success'])
            def failure(self,fn):return self
            def run_in_background(self):pass
        with patch.object(D,'QueryOp',Query):
            path=self.preview();self.finish(0);self.c.remove_group('group',3)
            self.snapshot=self.boot(4);self.c.poll(force=True);self.finish(1);callbacks[0]({'manifest':{}})
        self.assertFalse(path.exists());self.assertNotIn('invite',self.c.previews)
    def preview(self):
        c=self.c;item={'id':'invite','thread':'group','recipient':'me','attachment':{'id':'bundle'}}
        c.social['invites']=[item];c.client().download=lambda meta:b'zip fixture';c.preview_invite('invite','request')
        return Path(self.temp.name)/'invite.alink'
    def test_removed_group_preview_download_cannot_create_file_or_query(self):
        path=self.preview();self.c.remove_group('group',3);self.finish(0)
        self.assertFalse(path.exists());self.assertNotIn('invite',self.c.previews)
    def test_removed_group_preview_query_cannot_restore_file_or_ui(self):
        callbacks=[]
        class Query:
            def __init__(self,**kw):callbacks.append(kw['success'])
            def failure(self,fn):return self
            def run_in_background(self):pass
        with patch.object(D,'QueryOp',Query):
            path=self.preview();self.finish(0);self.assertTrue(path.exists());self.c.remove_group('group',3);callbacks[0]({'manifest':{}})
        self.assertFalse(path.exists());self.assertNotIn('invite',self.c.previews)
        self.assertFalse(any(event=='invite_preview' or (event=='operation' and data.get('event')=='invite_preview') for event,data in self.events))

if __name__=='__main__':unittest.main()
