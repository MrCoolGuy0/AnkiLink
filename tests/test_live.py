"""Real Qt WebSockets against a disposable standalone relay; no user profiles."""
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PyQt6.QtCore import QObject,QCoreApplication
from PyQt6.QtWidgets import QApplication
import test_relay
from test_message_controller import D
import server as R
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('anki_link_live_test',ROOT/'anki_link/live.py');L=importlib.util.module_from_spec(spec);spec.loader.exec_module(L)

class LiveNative(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.server=R.make_server('127.0.0.1',0,self.temp.name,join_code='test-code');self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.relay=self.server.app
        self.a=self.relay.authenticate({'username':'jay','password':'strong test password','join_code':'test-code'},True)
        self.b=self.relay.authenticate({'username':'mia','password':'strong test password','join_code':'test-code'},True)
        self.relay.call(self.a['user']['id'],'friend_request',{'code':self.b['user']['code']})
        self.tid=self.relay.call(self.b['user']['id'],'friend_decide',{'user':self.a['user']['id'],'accept':True})['thread']
        self.owners=[]
    def owner(self,session):
        events=[];fallback=[];mw=QObject()
        owner=types.SimpleNamespace(mw=mw,window=None,store=types.SimpleNamespace(token=session['token'],data={'url':'http://127.0.0.1:'+str(self.server.server_port)}),events=events,fallback=fallback)
        owner.closed=False
        owner.share_activity=False
        owner.deck='Parent::Lesson 1'
        owner.publish_presence=types.MethodType(D.Controller.publish_presence,owner)
        def ready():
            events.append(('ready',None))
            owner.publish_presence(force=True)
        owner.live_ready=ready
        owner.live_event=lambda event,data:events.append((event,data))
        owner.activity_payload=lambda idle=False:{
            'share':owner.share_activity,'deck':owner.deck if owner.share_activity and not idle else '',
            'status':'idle' if idle else 'online',
        }
        owner.send_message_http=lambda data:fallback.append(data)
        owner.live=L.Live(owner);self.owners.append(owner);return owner
    def until(self,predicate,timeout=3):
        end=time.monotonic()+timeout
        while not predicate() and time.monotonic()<end:QCoreApplication.processEvents();time.sleep(.002)
        self.assertTrue(predicate(),'Qt signal did not arrive in time')
    def tearDown(self):
        for owner in self.owners:owner.live.close()
        QCoreApplication.processEvents();self.server.shutdown();self.server.server_close();self.thread.join(2);self.temp.cleanup()
    def test_real_qt_live_send_push_typing_receipts_and_no_http_retry(self):
        a,b=self.owner(self.a),self.owner(self.b);self.until(lambda:a.live.online and b.live.online)
        data={'thread':self.tid,'kind':'text','text':'Native Qt hello 💜','nonce':'qt-live'}
        self.assertTrue(a.live.send('message',data))
        self.until(lambda:any(e=='sent' for e,_ in a.events) and any(e=='messages' for e,_ in b.events))
        ack=next(d for e,d in a.events if e=='sent');self.assertEqual(ack['message']['text'],data['text']);self.assertNotIn(data['nonce'],a.live.pending)
        self.assertTrue(b.live.send('delivered',{'thread':self.tid,'last':ack['id']}));self.until(lambda:any(e=='receipts' and d['receipts'][0]['uid']==self.b['user']['id'] for e,d in a.events))
        self.assertEqual(next(d for e,d in a.events if e=='receipts')['receipts'][0]['seen'],0)
        b.live.send('read',{'thread':self.tid,'last':ack['id']});self.until(lambda:any(e=='receipts' and d['receipts'][0]['seen']==ack['id'] for e,d in a.events))
        a.live.send('typing',{'thread':self.tid,'typing':True});self.until(lambda:any(e=='typing' for e,_ in b.events))
        a.live.send('message',data);self.until(lambda:len([1 for e,_ in a.events if e=='sent'])==2)
        self.assertEqual(len(self.relay.messages(self.b['user']['id'],self.tid)['messages']),1);self.assertEqual(a.fallback,[]);self.assertEqual(b.fallback,[])
    def test_lost_ack_retries_same_nonce_once_without_blocking_input(self):
        a=self.owner(self.a);self.until(lambda:a.live.online)
        payload={'thread':self.tid,'nonce':'lost','kind':'text','text':'Keep this'}
        a.live.pending['lost']=(payload,time.monotonic()-9);a.live.tick();a.live.tick()
        self.assertEqual(a.fallback,[payload]);self.assertEqual(a.live.pending,{})
    def test_pull_continues_reaction_cursor_for_offline_catchup(self):
        a=self.owner(self.a);self.until(lambda:a.live.online);a.reaction_cursor=123.5
        a.live.last_pull=0;a.last_presence_sent=time.monotonic();sent=[]
        with patch.object(a.live,'send',side_effect=lambda action,data:sent.append((action,data)) or True):a.live.tick()
        self.assertEqual(next(data for action,data in sent if action=='pull'),{'reaction_after':123.5})
    def test_minimized_live_connection_uses_background_pull_rate_then_resumes(self):
        a=self.owner(self.a);self.until(lambda:a.live.online);sent=[]
        a.window=types.SimpleNamespace(isVisible=lambda:True,isMinimized=lambda:True)
        a.live.last_pull=400;a.last_presence_sent=400
        with patch.object(a.live,'send',side_effect=lambda action,data:sent.append(action) or True):
            with patch.object(L.time,'monotonic',return_value=400.3):a.live.tick()
            self.assertEqual(sent,[])
            self.assertEqual(a.live.timer.interval(),1000)
            with patch.object(L.time,'monotonic',return_value=402.1):a.live.tick()
            self.assertEqual(sent,['pull'])
            a.window.isMinimized=lambda:False
            with patch.object(L.time,'monotonic',return_value=402.4):a.live.tick()
            self.assertEqual(sent,['pull','pull'])
            self.assertEqual(a.live.timer.interval(),250)
        self.assertTrue(a.live.online,'minimizing must not disconnect the account')
    def test_reconnect_restores_live_connection_and_can_send_again(self):
        a=self.owner(self.a);self.until(lambda:a.live.online);a.live.socket.abort();self.until(lambda:not a.live.online);self.until(lambda:a.live.online)
        a.live.send('message',{'thread':self.tid,'nonce':'after-reconnect','kind':'text','text':'Recovered'})
        self.until(lambda:any(e=='sent' and d['nonce']=='after-reconnect' for e,d in a.events));self.assertEqual(a.fallback,[])
    def test_activity_is_leaf_only_opt_in_and_idle_clears_deck(self):
        key=hashlib.sha256(self.a['token'].encode()).hexdigest();uid=self.a['user']['id']
        for share,state,expected in [(False,'online',''),(True,'online','Cardiology'),(True,'idle','')]:
            self.relay.call(uid,'presence',{'_session':key,'share':share,'status':state,'deck':'Parent::Science::Cardiology'})
            person=next(p for p in self.relay.status(self.b['user']['id'])['people'] if p['id']==uid);self.assertEqual(person['activity']['deck'],expected)
    def test_friend_sees_online_studying_and_idle_with_chat_never_opened(self):
        a,b=self.owner(self.a),self.owner(self.b)
        b.window=types.SimpleNamespace(isVisible=lambda:True,isMinimized=lambda:False)
        uid=self.a['user']['id']
        def sees(state,deck):
            status=next((data for event,data in reversed(b.events) if event=='status'),{})
            return any(p['id']==uid and (p.get('activity') or {}).get('status')==state
                       and p['activity']['deck']==deck for p in status.get('people',[]))
        self.until(lambda:sees('online',''))
        a.share_activity=True
        a.publish_presence(activity_change=True)
        self.until(lambda:sees('online','Lesson 1'))
        a.live.last_input=time.monotonic()-301
        a.last_presence_sent=time.monotonic()-20
        a.live.tick()
        self.until(lambda:sees('idle',''))
        self.assertIsNone(a.window)
    def test_existing_database_startup_migration_is_idempotent(self):
        before=self.relay.bootstrap(self.a['user']['id']);again=R.Relay(self.temp.name)
        self.assertEqual(again.bootstrap(self.a['user']['id'])['user'],before['user']);self.assertEqual(len(again.bootstrap(self.a['user']['id'])['threads']),1)

if __name__=='__main__':unittest.main()
