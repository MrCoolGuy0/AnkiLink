"""Minimized chat remains connected without foreground polling or Seen receipts."""
from enum import IntFlag
import json
import types
import unittest
from unittest.mock import patch
import test_message_controller as base
D=base.D

class WindowState(unittest.TestCase):
    setUp=base.MessageController.setUp
    finish=base.MessageController.finish
    def test_minimized_window_uses_background_bootstrap_and_no_thread_poll(self):
        self.c.window.isMinimized=lambda:True
        with patch.object(D.time,'monotonic',return_value=100):
            self.c.poll();self.assertEqual(len(self.jobs),1,'only bootstrap, not a foreground messages request')
            self.finish(0)
        self.assertFalse(self.c.window_visible());self.assertEqual(self.c.next_bootstrap,115)
    def test_minimized_window_cannot_mark_seen_but_delivery_still_works(self):
        self.c.window.isMinimized=lambda:True;sent=[]
        self.c.live=types.SimpleNamespace(send=lambda action,data:sent.append((action,data)) or True)
        for action in ('read','delivered'):
            self.c.message((False,None),'anki_link:'+json.dumps({'action':action,'thread':'chat','last':7}),self.c.window)
        self.assertEqual(sent,[('delivered',{'thread':'chat','last':7})])
    def test_open_restores_same_window_without_losing_maximized_state(self):
        class State(IntFlag):Minimized=1;Maximized=2
        seen=[]
        class Window:
            state=State.Minimized|State.Maximized
            web=types.SimpleNamespace(show=lambda:None)
            def isMinimized(self):return bool(self.state&State.Minimized)
            def windowState(self):return self.state
            def setWindowState(self,value):self.state=value;seen.append('restore')
            def show(self):seen.append('show')
            def raise_(self):seen.append('raise')
            def activateWindow(self):seen.append('activate')
        window=self.c.window=Window();self.c.store.token=''
        self.c.timer.setInterval=lambda value:seen.append(('interval',value))
        with patch.object(D,'Qt',types.SimpleNamespace(WindowState=types.SimpleNamespace(WindowMinimized=State.Minimized))):self.c.open()
        self.assertIs(self.c.window,window);self.assertEqual(window.state,State.Maximized)
        self.assertEqual(seen,['restore',('interval',1000),'show','raise','activate'])
    def test_visible_dock_cannot_mark_seen_while_central_anki_has_focus(self):
        c=self.c;main_focus=object();web=object();c.ui_mode='dock'
        c.dock=types.SimpleNamespace(isVisible=lambda:True)
        c.mw.isMinimized=lambda:False;c.mw.isActiveWindow=lambda:True
        c.window.web=types.SimpleNamespace(isAncestorOf=lambda value:value is web)
        with patch.object(D,'QApplication',types.SimpleNamespace(focusWidget=lambda:main_focus)):
            self.assertTrue(c.window_visible());self.assertFalse(c.window_focused())
            c.message((False,None),'anki_link:{"action":"read","thread":"chat","last":7}',c.window)
        self.assertEqual(self.jobs,[])
        with patch.object(D,'QApplication',types.SimpleNamespace(focusWidget=lambda:web)):
            self.assertTrue(c.window_focused())
            c.message((False,None),'anki_link:{"action":"read","thread":"chat","last":7}',c.window)
        self.assertEqual(len(self.jobs),1)

if __name__=='__main__':unittest.main()
