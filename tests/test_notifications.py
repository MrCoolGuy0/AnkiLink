"""Notification policy: synthetic messages, account-local mutes, no collection access."""
import copy
import json
import types
import tempfile
import unittest
from unittest.mock import patch
import test_message_controller as base
D=base.D


class Notifications(unittest.TestCase):
    def setUp(self):
        base.MessageController.setUp(self)
        self.notices=[];self.saved=0
        case=self
        class Notice:
            def __init__(self,owner,thread,message):self.owner=owner;self.closed=False;self.update_message(thread,message);case.notices.append(self)
            def update_message(self,thread,message):self.thread=thread;self.message=message
            def show(self):pass
            def raise_(self):pass
            def close(self):self.closed=True;self.owner.notice=None
        module=types.ModuleType('anki_link.notifications');module.Notice=Notice
        self.patch=patch.dict('sys.modules',{'anki_link.notifications':module});self.patch.start();self.addCleanup(self.patch.stop)
        self.c.store.data={'url':'https://one.test','user':{'id':'me'},'muted':[]}
        self.c.message_after={}
        self.c.store.save=lambda:setattr(self,'saved',self.saved+1)
        self.c.social={'user':{'id':'me'},'threads':[{'id':'chat','title':'Mia','kind':'direct','unread':1,'last_id':10,'last':{'sender':'friend','kind':'text','text':'Old hello'}}]}
        self.c.window.isActiveWindow=lambda:False
    def message(self,identifier=11,**changes):return {'id':identifier,'sender':'friend','kind':'text','text':'Hello',**changes}
    def test_initial_unread_history_is_seeded_without_a_popup(self):
        self.c.notification_bootstrap(self.c.social,initial=True);self.c.notification_bootstrap(self.c.social)
        self.assertEqual(self.notices,[])
    def test_live_then_fallback_bootstrap_then_duplicate_packet_only_notify_once(self):
        self.c.notification_bootstrap(self.c.social,initial=True)
        self.c.notify_messages('chat',[self.message()]);notice=self.notices[0]
        self.c.social['threads'][0].update(last_id=11,last=self.message())
        self.c.notification_bootstrap(self.c.social);self.c.notify_messages('chat',[self.message()])
        self.assertEqual(len(self.notices),1);self.assertIs(self.c.notice,notice)
    def test_burst_updates_one_notice_instead_of_stacking(self):
        for i in range(11,25):self.c.notify_messages('chat',[self.message(i,text=str(i))])
        self.assertEqual(len(self.notices),1);self.assertEqual(self.c.notice.message['text'],'24')
    def test_own_messages_never_notify(self):
        self.c.notify_messages('chat',[self.message(sender='me')]);self.assertEqual(self.notices,[])
    def test_group_activity_is_quiet_but_next_chat_message_notifies(self):
        self.c.notify_messages('chat',[self.message(kind='system',text='Mia added Jay.')])
        self.assertEqual(self.notices,[])
        self.assertEqual(self.c.notification_cursor['chat'],11)
        self.c.notify_messages('chat',[self.message(12,text='Welcome')])
        self.assertEqual(self.notices[0].message['text'],'Welcome')
    def test_open_focused_conversation_is_silent_but_other_conversations_notify(self):
        self.c.window.isActiveWindow=lambda:True
        self.c.notify_messages('chat',[self.message()]);self.assertEqual(self.notices,[])
        self.c.active_thread='other';self.c.notify_messages('chat',[self.message(12)])
        self.assertEqual(len(self.notices),1)
    def test_muted_chat_stays_delivered_without_popup_and_can_be_unmuted(self):
        self.c.set_thread_muted('chat',True);self.c.live_event('messages',{'thread':'chat','messages':[self.message()]})
        self.assertEqual(self.notices,[]);self.assertEqual(self.requests,[])
        self.assertTrue(self.jobs,'delivery still runs independently of notifications')
        self.c.set_thread_muted('chat',False);self.c.notify_messages('chat',[self.message(12)])
        self.assertEqual(len(self.notices),1);self.assertEqual(self.saved,2)
    def test_muting_is_account_and_server_scoped(self):
        self.c.set_thread_muted('chat',True);saved=copy.deepcopy(self.c.store.data)
        self.assertEqual(self.c.muted_threads(),['chat'])
        self.c.store.data['user']={'id':'another'};self.assertEqual(self.c.muted_threads(),[])
        self.c.store.data=copy.deepcopy(saved);self.c.store.data['url']='https://two.test';self.assertEqual(self.c.muted_threads(),[])
        self.c.store.data=saved;self.assertEqual(self.c.muted_threads(),['chat'])
    def test_mute_is_saved_and_survives_reopening_profile_settings(self):
        from anki_link.config import Store
        with tempfile.TemporaryDirectory() as folder:
            self.c.store=Store(folder);self.c.store.data.update(url='https://one.test',user={'id':'me'})
            self.c.set_thread_muted('chat',True)
            restored=Store(folder)
            self.assertEqual(restored.data['muted_by_account']['https://one.test|me'],['chat'])
    def test_mute_immediately_dismisses_visible_notice(self):
        self.c.notify_messages('chat',[self.message()]);notice=self.c.notice
        self.c.set_thread_muted('chat',True);self.assertTrue(notice.closed);self.assertIsNone(self.c.notice)
    def test_history_watch_does_not_notify(self):
        self.c.live_event('messages',{'thread':'chat','history':True,'messages':[self.message()]})
        self.assertEqual(self.notices,[])
    def test_new_thread_from_later_bootstrap_can_notify(self):
        self.c.notification_bootstrap(self.c.social,initial=True)
        self.c.social['threads'].append({'id':'new','title':'New friend','last_id':20,'unread':1,'last':self.message(20)})
        self.c.notification_bootstrap(self.c.social);self.assertEqual(self.notices[0].thread['id'],'new')
    def test_unknown_thread_mute_is_ignored(self):
        self.c.set_thread_muted('unknown',True);self.assertEqual(self.saved,0)
    def test_session_reset_dismisses_old_account_notice_and_cursors(self):
        self.c.notify_messages('chat',[self.message()]);notice=self.c.notice
        self.c.reset_session_work();self.assertTrue(notice.closed);self.assertEqual(self.c.notification_cursor,{})
    def test_receiving_a_deck_does_not_accept_or_import_it(self):
        self.c.notify_messages('chat',[self.message(kind='deck',invite='invitation')])
        self.assertEqual(len(self.notices),1);self.assertEqual(self.jobs,[]);self.assertEqual(self.requests,[])
    def test_notice_routes_to_exact_thread_and_waits_for_web_ready_if_needed(self):
        c=self.c;c.ui_mode='dock';c.web_ready=True;c.pending_open_thread=None;seen=[]
        c.show_sidebar=lambda:seen.append('sidebar');c.open_conversation('chat')
        self.assertEqual(seen,['sidebar']);self.assertIn(('open_thread',{'id':'chat'}),self.events)
        self.events.clear();c.web_ready=False;c.open_conversation('chat')
        self.assertEqual(self.events,[]);self.assertEqual(c.pending_open_thread,'chat')
    def test_back_to_list_stops_foreground_thread_tracking(self):
        self.c.message((False,None),'anki_link:'+json.dumps({'action':'thread','id':None}),self.c.window)
        self.assertIsNone(self.c.active_thread);self.assertEqual(self.jobs,[])


if __name__=='__main__':unittest.main()
