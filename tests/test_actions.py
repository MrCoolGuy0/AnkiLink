"""Delayed replies for group/friend/transfer feedback and refresh races."""
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
import test_message_controller as base
D=base.D

class ActionFlow(unittest.TestCase):
    def setUp(self):
        base.MessageController.setUp(self);self.c.busy=False
    finish=base.MessageController.finish
    def bridge(self,action,request='one',**data):
        return self.c.message((False,None),'anki_link:'+json.dumps(dict(action=action,_request=request,**data)),self.c.window)
    def operation(self,request='one'):
        return [data for event,data in self.events if event=='operation' and data['request']==request]
    def test_group_ack_is_scoped_and_never_sends_ui_request_id_to_server(self):
        self.c.client().action=lambda name,data:(self.requests.append((name,data)) or {'thread':'created'})
        self.bridge('group',title='Group',users=['friend'])
        self.assertEqual(self.requests,[],'the bridge must not wait for HTTP')
        self.finish(0)
        self.assertEqual(self.requests,[('group',{'title':'Group','users':['friend']})])
        self.assertEqual(self.operation()[0]['phase'],'done')
        self.assertEqual(self.operation()[0]['data'],{'thread':'created'})
        self.assertNotIn('one',self.c.pending_actions)
    def test_duplicate_pending_click_and_failure_can_retry_without_global_lock(self):
        self.bridge('group',title='Group',users=['friend']);self.bridge('group',title='Group',users=['friend'])
        self.assertEqual(len(self.jobs),1)
        self.c.client().action=lambda *args:(_ for _ in ()).throw(OSError('Offline'))
        self.finish(0);self.assertEqual(self.operation()[-1]['phase'],'failed')
        self.assertFalse(self.c.pending_actions)
        self.bridge('group',request='retry',title='Group',users=['friend']);self.assertEqual(len(self.jobs),2)
    def test_done_callback_failure_finishes_request_instead_of_leaving_it_pending(self):
        self.c.pending_actions={'one':'group'}
        def callback(value):raise ValueError('Invalid reply')
        self.c.action('group',{},callback,request='one');self.finish(0)
        self.assertEqual(self.operation()[-1]['message'],'Invalid reply');self.assertFalse(self.c.pending_actions)
    def test_forced_refresh_during_old_snapshot_runs_again_immediately_and_coalesces(self):
        self.c.active_thread=None
        self.c.poll();self.c.poll(force=True);self.c.poll(force=True)
        self.assertEqual(len(self.jobs),1)
        self.finish(0)
        self.assertEqual(len(self.jobs),2,'do not wait for the next 15-second heartbeat')
        self.assertTrue(self.c.polling)
        self.finish(1);self.assertFalse(self.c.polling)
        self.assertEqual(len(self.jobs),2);self.assertEqual(self.events[-1],('refresh_state',{'loading':False}))
    def test_mutation_completed_during_old_snapshot_still_gets_a_fresh_snapshot(self):
        self.c.active_thread=None;self.c.poll()
        self.bridge('friend_request',code='FRIEND');self.finish(1)
        self.assertTrue(self.c.refresh_queued);self.assertEqual(self.operation()[-1]['phase'],'done')
        self.finish(0);self.assertEqual(len(self.jobs),3)
        self.finish(2);self.assertFalse(self.c.polling)
    def test_queued_refresh_survives_a_failure_of_the_old_snapshot(self):
        self.c.active_thread=None
        self.c.client().request=lambda _:(_ for _ in ()).throw(OSError('Old request failed'))
        self.c.poll();self.c.poll(force=True);self.finish(0)
        self.assertEqual(len(self.jobs),2)
        self.c.client().request=lambda _:{'user':{'id':'me'},'invites':[],'friends':[],'threads':[]}
        self.finish(1);self.assertFalse(self.c.polling)
    def test_request_validation_failure_is_visible_and_releases_only_that_request(self):
        self.bridge('share',recipients=[])
        self.assertEqual(self.operation()[-1]['phase'],'failed')
        self.assertEqual(self.operation()[-1]['message'],'Choose at least one friend.')
        self.assertEqual(self.jobs,[])
    def test_profile_change_suppresses_old_request_completion(self):
        self.bridge('group',title='Group',users=['friend']);self.c.epoch+=1;self.c.reset_session_work();self.finish(0)
        self.assertEqual(self.operation(),[]);self.assertFalse(self.c.pending_actions)
    def test_catalog_collection_callback_cannot_reopen_after_sign_out(self):
        captured=[]
        class Query:
            def __init__(self,**kw):captured.append(kw)
            def failure(self,fn):return self
            def run_in_background(self):pass
        with patch.object(D,'QueryOp',Query):self.bridge('catalog')
        self.c.epoch+=1;self.c.reset_session_work();captured[0]['success']([])
        self.assertEqual(self.events,[])

class MediaQueue(unittest.TestCase):
    setUp=base.MessageController.setUp
    finish=base.MessageController.finish
    def test_many_avatars_have_at_most_two_workers_and_actions_can_start(self):
        with tempfile.TemporaryDirectory() as td:
            c=self.c;c.preparing=set();c.blobs=set();c.store.folder=Path(td);c.store.data['url']='https://test.invalid';c.social={'user':{'id':'me'}}
            c.client().download=lambda meta:b'image bytes'
            rows=[{'id':str(i),'mime':'image/png','sha256':'a'*64} for i in range(20)]
            for row in rows:c.blob(row)
            c.blob(rows[0]);self.assertEqual(len(self.jobs),2);self.assertEqual(c.blob_active,2)
            self.assertEqual(len(c.blob_queue),18)
            c.action('group',{});self.assertEqual(len(self.jobs),3)
            self.finish(0);self.assertEqual(c.blob_active,2);self.assertEqual(len(c.blob_queue),17);self.assertEqual(len(self.jobs),4)
            c.client().download=lambda meta:(_ for _ in ()).throw(OSError('Offline'))
            self.finish(1);self.assertEqual(c.blob_active,2);self.assertEqual(len(c.blob_queue),16)
            self.assertNotIn('1',c.preparing);self.assertEqual(self.events[-1][0],'attachment_error')

if __name__=='__main__':unittest.main()
