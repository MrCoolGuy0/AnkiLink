"""Short startup check using Anki's actual AnkiWebView and Qt WebChannel.

Requires matching aqt/anki plus Qt native dependencies. The host supplies a
temporary collection/profile and task runner; WebView, media server, pycmd,
stdHtml, bridge registration and the add-on Window/Controller are unmodified.
No global message hook or test-injected pycmd is used. No remote account needed.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import importlib
import json
import os
import sys
import tempfile
import threading
import types


def main():
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS','--no-sandbox --disable-gpu')
    import anki.lang
    anki.lang.set_lang('en')
    import aqt
    from aqt.qt import QApplication,QMainWindow,QTextEdit,QObject,pyqtSignal,QEventLoop,QTimer,Qt,QShortcut,QKeySequence
    from PyQt6.QtTest import QTest
    from aqt.mediasrv import MediaServer
    from aqt.webview import AnkiWebView
    from anki.collection import Collection
    root=Path(__file__).resolve().parents[1]
    app=QApplication(['native-anki-link-check']);temp=tempfile.TemporaryDirectory();base=Path(temp.name)
    profile=base/'profile';profile.mkdir();pool=ThreadPoolExecutor(max_workers=2)
    class Taskman(QObject):
        done=pyqtSignal(object,object)
        def __init__(self):super().__init__();self.done.connect(lambda cb,f:cb(f))
        def run_in_background(self,work,done,*,uses_collection=True):
            future=pool.submit(work);future.add_done_callback(lambda f:self.done.emit(done,f));return future
    host=QMainWindow();host.web=QTextEdit(host);host.setCentralWidget(host.web);host.resize(1400,850);host.show();host.app=app;host.col=Collection(str(profile/'collection.anki2'));host.state='deckBrowser';host.taskman=Taskman()
    # Only accelerate Anki's five-second deferred page-record cleanup.
    host.progress=types.SimpleNamespace(single_shot=lambda ms,fn:QTimer.singleShot(min(ms,100),fn))
    host.pm=types.SimpleNamespace(profileFolder=lambda:str(profile),reduce_motion=lambda:False,minimalist_mode=lambda:False)
    host.addonManager=types.SimpleNamespace(addonFromModule=lambda _: 'anki_link',getWebExports=lambda _:r'web/.*\.(html|css|js|png)',addonsFolder=lambda:str(root))
    host.mediaServer=MediaServer(host);host.mediaServer.start()
    host.serverURL=lambda:'http://127.0.0.1:'+str(host.mediaServer.getPort())+'/'
    host.baseHTML=lambda:'<base href="'+host.serverURL()+'">'
    aqt.mw=host
    pkg=types.ModuleType('anki_link');pkg.__path__=[str(root/'anki_link')];sys.modules['anki_link']=pkg
    dialog=importlib.import_module('anki_link.dialog')
    sys.path.insert(0,str(root/'server'));from server import make_server
    relay=make_server(port=0,directory=base/'relay');thread=threading.Thread(target=relay.serve_forever,daemon=True);thread.start()
    controller=dialog.Controller(host,'anki_link');controller.open();view=controller.window.web
    assert type(view) is AnkiWebView,'Must exercise native class, not a WebView adapter'
    assert view._bridge_context is controller.window,'stdHtml context alone is insufficient'
    assert view.onBridgeCmd.__self__ is controller.window
    def wait(ms):loop=QEventLoop();QTimer.singleShot(ms,loop.quit);loop.exec()
    def js(code):
        loop=QEventLoop();values=[]
        view.evalWithCallback(code,lambda v:(values.append(v),loop.quit()))
        QTimer.singleShot(1800,loop.quit);loop.exec();assert values,'Native WebView/DOM did not finish loading';return values[0]
    def until(check,label):
        import time
        end=time.monotonic()+7
        while time.monotonic()<end:
            if check():return
            wait(40)
        raise AssertionError(label)
    until(lambda:js('!!document.querySelector("#auth-form")'),'native pycmd -> controller -> setup -> auth')
    before=host.col.db.all('SELECT * FROM cards')
    if '--buttons' in sys.argv or '--buttons-before' in sys.argv:
        from test_button_styles_qt import check_buttons
        check_buttons(js,view,wait,root,before='--buttons-before' in sys.argv)
        assert host.col.db.all('SELECT * FROM cards')==before
        controller.close();wait(180);pool.shutdown(wait=True);host.col.close();host.close()
        relay.shutdown();relay.server_close();thread.join(1);host.mediaServer.shutdown();temp.cleanup();app.quit()
        return
    # Use actual UI bridge again after startup, not a Python-side auth shortcut.
    url='http://127.0.0.1:'+str(relay.server_port)
    js('document.querySelector("[data-action=auth-switch]").click();'+''.join('document.querySelector('+json.dumps(s)+').value='+json.dumps(v)+';' for s,v in [('#server-url',url),('#auth-name','Native check'),('#auth-user','native_check'),('#auth-password','a local synthetic test password')])+'document.querySelector("#auth-form").dispatchEvent(new Event("submit",{bubbles:true,cancelable:true}))')
    until(lambda:controller.social is not None and js('!!document.querySelector(".layout")'),'native account signup round trip')
    controller.window.close();assert not controller.window.isVisible();controller.open()
    until(lambda:js('!!document.querySelector(".layout")'),'same native window reopened')
    page=view.page();controller.show_sidebar();host.resizeDocks([controller.dock],[350],Qt.Orientation.Horizontal);wait(150)
    assert controller.dock.widget() is view and view.page() is page and view._bridge_context is controller.window
    assert js('innerWidth')<=400 and js('getComputedStyle(document.querySelector(".workspace")).display')=='none'
    js('document.querySelector("[data-action=account]").click()')
    assert js('!!document.querySelector(".modal")'),'bridge and controls work after native reparent'
    js('document.querySelector("[data-action=close-modal]").click();document.querySelector("[data-action=add-friend]").click();')
    host.activateWindow();view.setFocus();js('document.querySelector("#friend-code").focus()');wait(80)
    hits=[];shortcuts=[QShortcut(QKeySequence(key),host,activated=lambda k=key:hits.append(k)) for key in ('1','e',' ','Return')]
    for key in (Qt.Key.Key_E,Qt.Key.Key_1,Qt.Key.Key_Space,Qt.Key.Key_Return):QTest.keyClick(view.focusProxy(),key);wait(30)
    assert hits==[],f'chat typing leaked into Anki shortcuts: {hits}'
    assert js('document.querySelector("#friend-code").value')=='e1 '
    for shortcut in shortcuts:shortcut.setEnabled(False);shortcut.deleteLater()
    controller.hide_sidebar();controller.show_sidebar();controller.open();wait(120)
    assert view.page() is page and view.parent() is controller.window and js('!!document.querySelector(".modal")')
    assert host.col.db.all('SELECT * FROM cards')==before
    assert controller.message((False,None),'anki_link:{"action":"ready"}',object())==(False,None)
    controller.close();wait(180);pool.shutdown(wait=True);host.col.close();host.close()
    relay.shutdown();relay.server_close();thread.join(1);host.mediaServer.shutdown();temp.cleanup();app.quit()
    print(json.dumps({'native_AnkiWebView':'passed','actual_media_server_and_QWebChannel':'passed','bridge_context_registration':'passed','auth_round_trip':'passed','hide_reopen':'passed','dock_reparent_same_page_and_bridge':'passed','foreign_context_rejected':'passed','schedule_unchanged':'passed','clean_shutdown':'passed'}),flush=True)


if __name__=='__main__':main()
