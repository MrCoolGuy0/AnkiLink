"""Deterministic delayed HTTP completions; no sleeps, GUI or user accounts."""
from concurrent.futures import Future
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
pkg=types.ModuleType('anki_link');pkg.__path__=[str(ROOT/'anki_link')];sys.modules.setdefault('anki_link',pkg)
qt=types.ModuleType('aqt.qt')
for name in ('QDialog','QVBoxLayout','QTimer','QFileDialog','QApplication','QImageReader','Qt','QSystemTrayIcon','QEvent'):setattr(qt,name,object)
web=types.ModuleType('aqt.webview');web.AnkiWebView=object
ops=types.ModuleType('aqt.operations');ops.QueryOp=ops.CollectionOp=object
theme=types.ModuleType('aqt.theme');theme.theme_manager=types.SimpleNamespace(night_mode=False)
spec=importlib.util.spec_from_file_location('anki_link._message_controller_test',ROOT/'anki_link/dialog.py')
D=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'aqt':types.ModuleType('aqt'),'aqt.qt':qt,'aqt.webview':web,'aqt.operations':ops,'aqt.theme':theme}):spec.loader.exec_module(D)

class MessageController(unittest.TestCase):
    def setUp(self):
        self.jobs=[];self.events=[];self.requests=[]
        c=self.c=D.Controller.__new__(D.Controller)
        c.history_loaded=set();c.ensure_live=lambda:None;c.live=None;c.uploads={};c.closed=False;c.epoch=0;c.polling=False;c.message_polls=set();c.active_thread='chat';c.social=None;c.menu_action=None;c.tray=None
        c.window=types.SimpleNamespace(isVisible=lambda:True,isActiveWindow=lambda:True,isMinimized=lambda:False)
        c.store=types.SimpleNamespace(token='test-token',data={'imports':{}})
        c.timer=types.SimpleNamespace(start=lambda:None)
        c.emit=lambda event,data=None:self.events.append((event,data))
        c.mw=types.SimpleNamespace(taskman=types.SimpleNamespace(run_in_background=lambda work,done,*,uses_collection=True:self.jobs.append((work,done))))
        boot={'user':{'id':'me'},'invites':[],'friends':[],'threads':[]}
        def action(name,data):
            self.requests.append((name,data))
            if data.get('nonce')=='fail':raise OSError('Offline')
            return {'id':42}
        client=types.SimpleNamespace(request=lambda path:boot,messages=lambda thread,after=0,before=0:{'messages':[{'id':7}],'before':before},action=action)
        c.client=lambda:client
    def finish(self,index):
        work,done=self.jobs[index];future=Future()
        try:future.set_result(work())
        except Exception as e:future.set_exception(e)
        done(future)
    def test_messages_can_arrive_while_bootstrap_is_still_waiting(self):
        self.c.poll();self.assertEqual(len(self.jobs),2);self.events.clear()
        self.finish(0)
        self.assertEqual(self.events[0][0],'messages');self.assertTrue(self.c.polling)
        self.finish(1);self.assertFalse(self.c.polling);self.assertEqual(self.events[-2][0],'bootstrap');self.assertEqual(self.events[-1],('refresh_state',{'loading':False}))
    def test_send_ack_does_not_wait_for_poll_or_start_an_extra_refresh(self):
        self.c.poll();self.events.clear();self.c.send_message({'thread':'chat','nonce':'one','text':'Hello','kind':'text'})
        self.assertEqual(len(self.jobs),3);self.finish(2)
        self.assertEqual(self.events,[('sent',{'id':42,'thread':'chat','nonce':'one'})])
        self.assertEqual(len(self.jobs),3);self.assertTrue(self.c.polling)
    def test_send_failure_identifies_exact_message_without_losing_others(self):
        self.c.send_message({'thread':'chat','nonce':'fail','text':'Keep me','kind':'text'});self.finish(0)
        self.assertEqual(self.events,[('message_failed',{'thread':'chat','nonce':'fail','message':'Offline'})])
    def test_poll_coalesces_inflight_requests_but_new_thread_can_load(self):
        self.c.poll();self.c.poll();self.assertEqual(len(self.jobs),2);self.events.clear()
        self.c.active_thread='other';self.c.poll(thread='other');self.assertEqual(len(self.jobs),3)
        self.finish(0);self.assertEqual(self.events,[],'old thread response cannot paint the new thread')
        self.finish(2);self.assertEqual(self.events[0][1]['thread'],'other')
        self.c.poll_messages('other',before=20);self.assertEqual(len(self.jobs),4)
        self.finish(3);self.assertTrue(self.events[-1][1]['earlier'])
    def test_read_receipt_does_not_trigger_another_poll(self):
        self.c.message((False,None),'anki_link:{"action":"read","thread":"chat","last":7}',self.c.window)
        self.assertEqual(len(self.jobs),1);self.finish(0);self.assertEqual(len(self.jobs),1)
        self.assertEqual(self.requests,[('read',{'thread':'chat','last':7})])
    def test_profile_epoch_ignores_old_send_completion(self):
        self.c.send_message({'thread':'chat','nonce':'one'});self.c.epoch+=1;self.finish(0)
        self.assertEqual(self.events,[])

class LiveController(unittest.TestCase):
    setUp=MessageController.setUp
    finish=MessageController.finish
    def test_live_send_does_not_queue_http_work(self):
        seen=[];self.c.live=types.SimpleNamespace(send=lambda action,data:seen.append((action,data)) or True)
        self.c.send_message({'thread':'chat','nonce':'fast','kind':'text','text':'Hello'})
        self.assertEqual(len(self.jobs),0);self.assertEqual(seen[0][0],'message')
    def test_hidden_window_cannot_mark_seen_but_can_mark_delivered(self):
        self.c.window.isVisible=lambda:False
        self.c.message((False,None),'anki_link:{"action":"read","thread":"chat","last":7}',self.c.window)
        self.assertEqual(self.jobs,[])
        self.c.message((False,None),'anki_link:{"action":"delivered","thread":"chat","last":7}',self.c.window);self.assertEqual(len(self.jobs),1)
    def test_incoming_message_does_not_skip_unopened_thread_history(self):
        self.c.message_after={}
        self.c.live_event('messages',{'thread':'other','messages':[{'id':70}]})
        self.assertNotIn('other',self.c.message_after);self.assertNotIn('other',self.c.history_loaded)
        self.c.live_event('messages',{'thread':'other','history':True,'messages':[{'id':60},{'id':70}]})
        self.assertEqual(self.c.message_after['other'],70);self.assertIn('other',self.c.history_loaded)
    def test_activity_reads_only_current_leaf_and_does_not_touch_scheduling(self):
        self.c.store.data={'url':'https://one.test','user':{'id':'me'},'activity':{'https://one.test|me':True}}
        self.c.mw.state='review';self.c.mw.reviewer=types.SimpleNamespace(card=types.SimpleNamespace(did=9))
        self.c.mw.col=types.SimpleNamespace(decks=types.SimpleNamespace(get=lambda did:{'name':'MIDTERMS::Science::Lesson 1 Cardiology'}))
        self.assertEqual(self.c.activity_payload()['deck'],'Lesson 1 Cardiology')
        self.assertEqual(self.c.activity_payload(True)['deck'],'')
        self.c.mw.state='deckBrowser';self.assertEqual(self.c.activity_payload()['deck'],'')
        self.c.mw.state='review';self.c.store.data['activity'].clear();self.assertEqual(self.c.activity_payload()['share'],False)

class ActivityCost(unittest.TestCase):
    setUp=MessageController.setUp
    finish=MessageController.finish

    def test_hidden_presence_refreshes_while_chat_sync_is_pending(self):
        c=self.c
        c.window=None
        c.social={'realtime':True}
        c.polling=True
        c.poll()
        self.assertEqual(len(self.jobs),1)
        self.finish(0)
        self.assertEqual(self.requests,[('presence',{'share':False,'status':'online','deck':''})])
        c.poll()
        self.assertEqual(len(self.jobs),1,'rapid timer ticks do not duplicate presence writes')

    def test_friend_status_received_before_opening_is_replayed_with_current_time(self):
        c=self.c
        c.window=None
        c.pending_open_thread=None
        c.social={'user':{'id':'me'},'friends':[],'invites':[],'threads':[]}
        people=[{'id':'friend','activity':{'status':'online','deck':'Lesson','updated':1000}}]
        with patch.object(D.time,'monotonic',return_value=50):
            c.live_event('status',{'people':people,'server_time':1000})
        self.events.clear()
        c.window=object()
        with patch.object(D.time,'monotonic',return_value=58):
            c.ready()
        self.assertEqual(self.events[-1],('status',{'people':people,'server_time':1008}))

    def test_http_presence_coalesces_deck_changes_and_privacy_toggle(self):
        c=self.c
        c.window=None
        c.store.data={'url':'https://one.test','user':{'id':'me'},'activity':{'https://one.test|me':True}}
        c.mw.state='review'
        c.mw.reviewer=types.SimpleNamespace(card=types.SimpleNamespace(did=1))
        c.mw.col=types.SimpleNamespace(decks=types.SimpleNamespace(get=lambda did:{'name':f'Course::Lesson {did}'}))
        c.study_changed()
        for did in range(2,6):
            c.mw.reviewer.card.did=did
            c.study_changed()
        self.assertEqual(len(self.jobs),1)
        c.store.data['activity'].clear()
        c.publish_presence(force=True)
        self.finish(0)
        self.assertEqual(len(self.jobs),2)
        self.finish(1)
        self.assertEqual([data['deck'] for _,data in self.requests],['Lesson 1',''])
        self.assertFalse(self.requests[-1][1]['share'])

    def test_native_card_events_reuse_deck_name_and_coalesce_presence(self):
        c=self.c;c.store.data={'url':'https://one.test','user':{'id':'me'},'activity':{'https://one.test|me':True}};reads=[];sent=[]
        c.mw.state='review';c.mw.reviewer=types.SimpleNamespace(card=types.SimpleNamespace(did=9));c.mw.col=types.SimpleNamespace(decks=types.SimpleNamespace(get=lambda did:reads.append(did) or {'name':'MIDTERMS::Lesson 1'}));c.live=types.SimpleNamespace(send=lambda action,data:sent.append((action,data)) or True)
        for _ in range(30):c.study_changed()
        self.assertEqual(reads,[9]);self.assertEqual(len(sent),1);self.assertEqual(sent[0][1]['deck'],'Lesson 1')
        c.mw.reviewer.card.did=10;c.study_changed();self.assertEqual(reads,[9,10])
        c.mw.state='overview';c.study_changed();self.assertEqual(sent[-1][1]['deck'],'')

if __name__=='__main__':unittest.main()
