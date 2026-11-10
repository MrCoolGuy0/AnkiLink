"""Two actual desktop WebViews + real controller + HTTP relay + native Anki.

Only Anki's host/operation runners are test adapters. Native collection methods,
controller, network client, server, JavaScript, images and keyboard are real.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import importlib
import json
import os
import sys
import tempfile
import threading
import types

ROOT=Path(__file__).resolve().parents[1]

def main():
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen');os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS','--no-sandbox --disable-gpu')
    from PyQt6 import QtCore,QtGui,QtWidgets
    from PyQt6.QtCore import QEventLoop,QTimer,QUrl,pyqtSignal,QObject,Qt
    from PyQt6.QtTest import QTest
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEnginePage
    from anki.collection import Collection
    app=QtWidgets.QApplication(['anki-link-ui-qa']);web=ROOT/'anki_link/web';out=ROOT.parent/'qa/ui';out.mkdir(parents=True,exist_ok=True)
    pool=ThreadPoolExecutor(max_workers=4)
    class Taskman(QObject):
        completed=pyqtSignal(object,object)
        def __init__(self):super().__init__();self.completed.connect(lambda cb,future:cb(future))
        def run_in_background(self,work,done,*,uses_collection=True):
            future=pool.submit(work);future.add_done_callback(lambda f:self.completed.emit(done,f));return future
    class Host(QtWidgets.QMainWindow):
        def __init__(self,profile,col):
            super().__init__();self.pm=types.SimpleNamespace(profileFolder=lambda:profile);self.col=col;self.state='deckBrowser';self.taskman=Taskman();self.reset_count=0
            self.addonManager=types.SimpleNamespace(addonFromModule=lambda _: 'anki_link')
            self.web=QtWidgets.QTextEdit(self);self.web.setPlainText('Synthetic Anki review area');self.setCentralWidget(self.web);self.resize(1500,850)
        def reset(self):self.reset_count+=1
    class Page(QWebEnginePage):
        def __init__(self,parent):super().__init__(parent);self.errors=[];self.context=None
        def javaScriptConsoleMessage(self,level,message,line,source):
            if message.startswith('BRIDGE:'):
                QTimer.singleShot(0,lambda:self.view.onBridgeCmd(message[7:]))
            elif 'Error' in str(level):self.errors.append(message)
    class Web(QWebEngineView):
        def __init__(self,parent,title):
            super().__init__(parent);self.onBridgeCmd=lambda cmd:None;self._bridge_context=None
            self.page_=Page(self);self.page_.view=self;self.setPage(self.page_)
        def set_bridge_command(self,func,context):self.onBridgeCmd=func;self._bridge_context=context
        def stdHtml(self,body,css,js,context,default_css=True):
            # Match Anki: stdHtml's context does NOT register the message bridge.
            head=''.join('<link rel="stylesheet" href="'+Path(p).name+'">' for p in css)+'<script>window.pycmd=m=>console.log("BRIDGE:"+m);</script>'+''.join('<script src="'+Path(p).name+'"></script>' for p in js)
            self.setHtml('<!doctype html><html><head>'+head+'</head><body>'+body+'</body></html>',QUrl.fromLocalFile(str(web)+'/'))
        def eval(self,code):self.page_.runJavaScript(code)
        def cleanup(self):self.close()
    class Operation:
        def __init__(self,parent,op,success=None):self.parent=parent;self.op=op;self.ok=success;self.bad=None
        def success(self,callback):self.ok=callback;return self
        def failure(self,callback):self.bad=callback;return self
        def with_progress(self,**kwargs):return self
        def run_in_background(self,**kwargs):
            def execute():
                try:result=self.op(self.parent.col)
                except Exception as error:
                    if self.bad:self.bad(error)
                    else:raise
                else:
                    if self.ok:self.ok(result)
            QTimer.singleShot(0,execute)
    qt=types.ModuleType('aqt.qt')
    for module in (QtCore,QtGui,QtWidgets):
        for name in dir(module):
            if not name.startswith('_'):setattr(qt,name,getattr(module,name))
    aq=types.ModuleType('aqt');sys.modules['aqt']=aq;sys.modules['aqt.qt']=qt
    ops=types.ModuleType('aqt.operations');ops.QueryOp=ops.CollectionOp=Operation;sys.modules['aqt.operations']=ops
    wmod=types.ModuleType('aqt.webview');wmod.AnkiWebView=Web;sys.modules['aqt.webview']=wmod
    theme=types.ModuleType('aqt.theme');theme.theme_manager=types.SimpleNamespace(night_mode=False);sys.modules['aqt.theme']=theme
    pkg=types.ModuleType('anki_link');pkg.__path__=[str(ROOT/'anki_link')];sys.modules['anki_link']=pkg
    sys.path.insert(0,str(ROOT/'server'));from server import make_server
    D=importlib.import_module('anki_link.dialog')
    temp=tempfile.TemporaryDirectory();base=Path(temp.name);server=make_server(port=0,directory=base/'relay');worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start();url='http://127.0.0.1:'+str(server.server_port)
    controllers=[];hosts=[]
    def js(c,code):
        loop=QEventLoop();box=[];c.window.web.page().runJavaScript(code,lambda result:(box.append(result),loop.quit()));QTimer.singleShot(2500,loop.quit);loop.exec();assert box,'JavaScript timed out';return box[0]
    def wait(ms=80):loop=QEventLoop();QTimer.singleShot(ms,loop.quit);loop.exec()
    def until(check,label,limit=7000):
        import time
        end=time.monotonic()+limit/1000
        while time.monotonic()<end:
            if check():return
            wait(45)
        raise AssertionError(label)
    def click(c,selector):js(c,'document.querySelector('+json.dumps(selector)+').click()');wait(70)
    def fill(c,selector,value):js(c,'document.querySelector('+json.dumps(selector)+').value='+json.dumps(value)+';')
    for index,(username,name) in enumerate((('jay','Jay'),('mia','Mia'))):
        profile=base/username;profile.mkdir();col=Collection(str(profile/'collection.anki2'));host=Host(str(profile),col);host.show();hosts.append(host)
        controller=D.Controller(host,'anki_link',QtGui.QAction('AnkiLink',host));controllers.append(controller)
        controller.sidebar_action=QtGui.QAction('AnkiLink sidebar',host);controller.sidebar_action.setShortcut(QtGui.QKeySequence('Ctrl+Alt+J'));controller.sidebar_action.triggered.connect(controller.toggle_sidebar);host.addAction(controller.sidebar_action);controller.open()
        until(lambda:js(controller,'!!document.querySelector("#auth-form")'),'auth view')
        click(controller,'[data-action=auth-switch]');fill(controller,'#server-url',url);fill(controller,'#auth-name',name);fill(controller,'#auth-user',username);fill(controller,'#auth-password','a strong test password')
        js(controller,'document.querySelector("#auth-form").dispatchEvent(new Event("submit",{bubbles:true,cancelable:true}))')
        until(lambda:controller.social is not None,'account sign in');until(lambda:js(controller,'!!document.querySelector(".layout")'),'signed-in view')
    a,b=controllers;ca,cb=[h.col for h in hosts]
    click(a,'[data-action=add-friend]');fill(a,'#friend-code',b.social['user']['code']);click(a,'[data-action=friend-send]')
    until(lambda:a.social and bool(a.social['friends']),'friend sent');b.poll();until(lambda:b.social and bool(b.social['friends']),'friend inbox')
    click(b,'[data-tab=friends]');click(b,'[data-friend-accept]');until(lambda:len(b.social['threads'])==1,'accepted friend thread');a.poll();until(lambda:len(a.social['threads'])==1,'sender thread')
    tid=a.social['threads'][0]['id']
    # One real WebEngine page moves between the native dock and normal window.
    # CSS is measured in Chromium, not approximated by a DOM-only test.
    click(a,'[data-thread="'+tid+'"]');fill(a,'#message-input','A draft while studying')
    js(a,'document.querySelector("#message-input").dispatchEvent(new Event("input",{bubbles:true}));')
    page=a.window.web.page();webview=a.window.web;a.show_sidebar();hosts[0].activateWindow();wait(150)
    hosts[0].resizeDocks([a.dock],[320],Qt.Orientation.Horizontal);wait(150)
    assert a.dock.widget() is webview and not a.window.isVisible() and a.window_visible()
    assert js(a,'getComputedStyle(document.querySelector(".sidebar")).display')=='none'
    assert js(a,'getComputedStyle(document.querySelector(".workspace")).display')=='flex'
    assert js(a,'document.documentElement.scrollWidth<=innerWidth'),'narrow conversation overflows'
    assert js(a,'document.querySelector("#message-input").value')=='A draft while studying'
    a.dock.grab().save(str(out/'sidebar-narrow.png'))
    click(a,'[data-action=back-chats]');assert a.active_thread is None
    assert js(a,'getComputedStyle(document.querySelector(".sidebar")).display')=='flex'
    assert js(a,'getComputedStyle(document.querySelector(".workspace")).display')=='none'
    click(a,'[data-thread="'+tid+'"]')
    hosts[0].resizeDocks([a.dock],[820],Qt.Orientation.Horizontal);wait(150)
    assert js(a,'innerWidth')>700
    assert js(a,'getComputedStyle(document.querySelector(".sidebar")).display')=='flex'
    assert js(a,'document.documentElement.scrollWidth<=innerWidth'),'wide dock overflows'
    a.dock.grab().save(str(out/'sidebar-wide.png'))
    a.hide_sidebar();hosts[0].activateWindow();hosts[0].web.setFocus();wait(60)
    QTest.keyClick(hosts[0],Qt.Key.Key_J,Qt.KeyboardModifier.ControlModifier|Qt.KeyboardModifier.AltModifier);wait(100)
    assert a.dock.isVisible(),'Ctrl+Alt+J opens dock'
    QTest.keyClick(hosts[0],Qt.Key.Key_J,Qt.KeyboardModifier.ControlModifier|Qt.KeyboardModifier.AltModifier);wait(100)
    assert not a.dock.isVisible(),'same shortcut hides dock'
    a.open();wait(150)
    assert a.window.web is webview and a.window.web.page() is page and a.window.web.parent() is a.window
    assert js(a,'document.querySelector("#message-input").value')=='A draft while studying'
    fill(a,'#message-input','');js(a,'document.querySelector("#message-input").dispatchEvent(new Event("input",{bubbles:true}));')
    # Hold a real HTTP group action after submitting in WebEngine. The modal
    # shows progress, can close, and Friends -> Decks still navigates. Its late
    # ACK must not pull us out of Decks; group avatars must render without IDs.
    release_group=threading.Event();entered_group=threading.Event();original_action=a.client().action
    def delayed_action(name,data):
        if name=='group':
            entered_group.set()
            if not release_group.wait(5):raise TimeoutError('Synthetic group hold expired')
        return original_action(name,data)
    a.client().action=delayed_action
    click(a,'[data-tab=chats]');click(a,'[data-action=new-group]');fill(a,'#group-name','Study corner');click(a,'[data-recipient]');click(a,'[data-action=create-group]')
    try:
        until(entered_group.is_set,'held group request')
        assert js(a,'document.querySelector(".operation-status").textContent.includes("Creating group")')
        assert js(a,'document.querySelector("[data-action=create-group]").disabled')
        wait(180);a.window.web.grab().save(str(out/'group-loading.png'))
        click(a,'[data-action=close-modal]');click(a,'[data-tab=friends]');click(a,'[data-tab=inbox]')
        assert js(a,'ankiLink.state.tab')=='inbox'
    finally:release_group.set()
    until(lambda:a.social and any(t['kind']=='group' for t in a.social['threads']),'created group refreshed')
    until(lambda:js(a,'Object.keys(ankiLink.state.operations).length')==0,'group feedback settled')
    assert js(a,'ankiLink.state.tab')=='inbox'
    click(a,'[data-tab=chats]');assert js(a,'!!document.querySelector("[data-thread]")')
    group_id=next(t['id'] for t in a.social['threads'] if t['kind']=='group');click(a,'[data-thread="'+group_id+'"]')
    assert js(a,'!!document.querySelector("#message-input")')
    a.client().action=original_action
    click(a,'[data-action=group-details]')
    assert js(a,'document.querySelectorAll(".group-member").length')==2
    group_picture=base/'group.png';group_image=QtGui.QImage(256,256,QtGui.QImage.Format.Format_ARGB32);group_image.fill(QtGui.QColor('#7861c4'));assert group_image.save(str(group_picture),'PNG')
    original_dialog=D.QFileDialog.getOpenFileName;D.QFileDialog.getOpenFileName=lambda *args:(str(group_picture),'')
    crop_wait={'tries':0}
    def accept_group_crop():
        dialog=app.activeModalWidget();crop_wait['tries']+=1
        if dialog and dialog.windowTitle()=='Crop group photo':dialog.accept()
        elif crop_wait['tries']<150:QTimer.singleShot(25,accept_group_crop)
    QTimer.singleShot(25,accept_group_crop)
    try:
        click(a,'[data-action=group-photo-set]')
        try:until(lambda:any(t.get('avatar') for t in a.social['threads'] if t['id']==group_id),'group photo saved')
        except AssertionError:
            print('Synthetic group-photo diagnostic:',js(a,'document.querySelector("#group-photo-progress")?.textContent'),{key:job['phase'] for key,job in a.group_avatar_jobs.items()},a.window.web.page_.errors,flush=True)
            raise
        until(lambda:js(a,'document.querySelector("#group-photo-progress").textContent.includes("saved")'),'group save feedback')
        b.poll(force=True);until(lambda:b.social and any(t.get('avatar') for t in b.social['threads'] if t['id']==group_id),'other member gets photo')
        click(b,'[data-tab=chats]');click(b,'[data-thread="'+group_id+'"]');click(b,'[data-action=group-details]')
        until(lambda:js(b,'!!document.querySelector(".group-profile img")'),'other member can download group photo')
        assert js(b,'document.querySelectorAll(".group-member").length')==2
        wait(180);b.window.web.grab().save(str(out/'group-details-light.png'))
        b.emit('setup',{'url':url,'dark':True,'remember_available':False,'signed_in':True});wait(180);b.window.web.grab().save(str(out/'group-details-dark.png'))
        b.emit('setup',{'url':url,'dark':False,'remember_available':False,'signed_in':True})
        click(a,'[data-action=group-photo-remove]');until(lambda:all(not t.get('avatar') for t in a.social['threads'] if t['id']==group_id),'group photo removed')
        b.poll(force=True);until(lambda:b.social and all(not t.get('avatar') for t in b.social['threads'] if t['id']==group_id),'other member gets removal')
        until(lambda:js(b,'!document.querySelector(".group-profile img")'),'group initials restored')
    finally:D.QFileDialog.getOpenFileName=original_dialog
    click(a,'[data-action=close-modal]');click(b,'[data-action=close-modal]');click(b,'[data-thread="'+tid+'"]')
    click(a,'[data-thread="'+tid+'"]');until(lambda:js(a,'!!document.querySelector("#message-input")'),'chat composer')
    # A real non-modal window minimizes independently and restores its exact
    # WebView/conversation/draft through the existing open action.
    window=a.window;view=window.web;fill(a,'#message-input','Keep this draft while minimized')
    assert window.parentWidget() is None and not window.isModal()
    assert window.windowFlags() & Qt.WindowType.WindowMinimizeButtonHint
    assert window.windowFlags() & Qt.WindowType.WindowMaximizeButtonHint
    window.showMinimized();wait(100)
    assert window.isMinimized() and not hosts[0].isMinimized() and a.timer.interval()==8000
    a.open();wait(100)
    assert a.window is window and a.window.web is view and not window.isMinimized() and a.timer.interval()==1000
    assert js(a,'document.querySelector("#message-input").value')=='Keep this draft while minimized'
    assert js(a,'ankiLink.state.thread')==tid
    fill(a,'#message-input','You got this 💜\nWant to study science?');a.window.activateWindow();a.window.web.setFocus();js(a,'document.querySelector("#message-input").focus()');QTest.keyClick(a.window.web.focusProxy() or a.window.web,Qt.Key.Key_Return)
    until(lambda:bool(a.client().messages(tid)['messages']),'sent chat');b.poll();until(lambda:js(b,'!!document.querySelector("#message-input")'),'recipient composer');b.active_thread=tid;b.poll()
    until(lambda:js(b,'document.querySelectorAll("[data-message-id]").length')>=1,'recipient message')
    assert 'You got this 💜' in js(b,'document.querySelector(".messages").textContent')
    assert not js(b,'!!document.querySelector(".message:not(.mine) .message-meta > span")')
    assert b.appearance()=='default'
    assert not js(b,'!!document.querySelector(".retro-desk")')
    fill(b,'#message-input','Draft through appearance changes')
    js(b,'window.appearanceMessage=document.querySelector("[data-message-id]")')
    click(b,'[data-action=account]')
    for selected in ('ankiretro','ankirise','ankimessage','default'):
        js(b,'(()=>{const select=document.querySelector("#appearance-theme");select.value='+json.dumps(selected)+';select.dispatchEvent(new Event("change",{bubbles:true}));})()')
        until(lambda:js(b,'ankiLink.state.setup.appearance')==selected,'appearance applied')
        assert D.Store(hosts[1].pm.profileFolder()).data['appearance']==selected
        assert js(b,'appearanceMessage===document.querySelector("[data-message-id]")')
        assert js(b,'document.querySelector("#message-input").value')=='Draft through appearance changes'
        assert js(b,'document.body.classList.contains("ankiretro")')==(selected=='ankiretro')
        assert js(b,'document.body.classList.contains("ankirise")')==(selected=='ankirise')
        assert js(b,'document.body.classList.contains("ankimessage")')==(selected=='ankimessage')
        assert js(b,'getComputedStyle(document.querySelector(".retro-frame")).backgroundImage.includes("to right")')==(selected=='ankirise')
        assert b.window.windowTitle()==('AnkiLink ♡' if selected=='ankiretro' else 'AnkiLink')
        if selected=='ankimessage':
            assert js(b,'getComputedStyle(document.querySelector(".message-search")).display')=='flex'
            js(b,'(()=>{const input=document.querySelector("#conversation-search");input.value="No matching test name";input.dispatchEvent(new Event("input",{bubbles:true}));})()')
            assert js(b,'!!document.querySelector(".thread[hidden]") && !document.querySelector(".search-empty").hidden')
        if selected=='default':
            assert not js(b,'!!document.querySelector(".thread[hidden]")')
    assert a.appearance()=='default'
    click(b,'[data-action=close-modal]');fill(b,'#message-input','')
    click(a,'[data-action=sticker]');click(a,'[data-sticker=cheer]');until(lambda:len(a.client().messages(tid)['messages'])>=2,'builtin sticker')
    from PIL import Image,ImageDraw
    picture=base/'study.png';image=Image.new('RGB',(700,390),'#eee8ff');draw=ImageDraw.Draw(image);draw.rounded_rectangle((35,35,665,355),radius=20,fill='#ffffff');draw.text((80,100),'SCIENCE STUDY NOTES',fill='#6252bd',font_size=32);draw.text((80,170),'One good question at a time.',fill='#333548',font_size=24);image.save(picture)
    original_dialog=D.QFileDialog.getOpenFileName;D.QFileDialog.getOpenFileName=lambda *args:(str(picture),'')
    click(a,'[data-action=image]');until(lambda:len(a.client().messages(tid)['messages'])>=3,'image upload')
    click(a,'[data-action=sticker]');click(a,'[data-action=upload-sticker]');until(lambda:len(a.client().messages(tid)['messages'])>=4,'custom image sticker')
    D.QFileDialog.getOpenFileName=original_dialog
    b.poll();until(lambda:js(b,'document.querySelectorAll(".message-photo").length')>=2,'downloaded images')
    b.window.activateWindow();b.window.web.setFocus();wait(200);b.window.web.grab().save(str(out/'chat-light.png'))
    # Polling must keep an existing image/GIF node and its current animation alive.
    js(b,'window.keptPhoto=document.querySelector(".message-photo")');b.poll();wait(200)
    assert js(b,'keptPhoto===document.querySelector(".message-photo")')
    click(b,'.message-photo');assert js(b,'!!document.querySelector(".photo-viewer")');click(b,'.photo-close');assert not js(b,'!!document.querySelector(".photo-viewer")')
    b.emit('setup',{'url':url,'dark':True,'remember_available':False,'signed_in':True});wait(200);b.window.web.grab().save(str(out/'chat-dark.png'))
    did=ca.decks.id('Midterms::Science::Lesson 1');config=ca.decks.config_dict_for_deck_id(did);config['new']['perDay']=17;config['desiredRetention']=.94;ca.decks.update_config(config)
    for q,answer in (('What does a heart pump?','Blood'),('The basic unit of life?','Cell')):
        note=ca.new_note(ca.models.by_name('Basic'));note.fields[:]=[q,answer];ca.add_note(note,did)
    f=ca.sched.get_or_create_filtered_deck(0);f.name='Practice::Science::Round 1';f.config.reschedule=False;del f.config.search_terms[1:];f.config.search_terms[0].search='deck:Midterms';f.config.search_terms[0].limit=100;fid=ca.sched.add_or_update_filtered_deck(f).id;ca.sched.rebuild_filtered_deck(fid)
    before=ca.db.all('SELECT * FROM cards');click(a,'[data-thread="'+group_id+'"]');click(a,'[data-action=share]');until(lambda:js(a,'!!document.querySelector("#deck-tree")'),'share deck tree')
    assert js(a,'document.querySelector("[data-share-group]").dataset.shareGroup')==group_id
    assert not js(a,'!!document.querySelector("[data-recipient]")')
    checkbox=js(a,'[...document.querySelectorAll("[data-deck]")].find(n=>n.parentElement.textContent.trim()==="Practice").dataset.deck')
    click(a,'[data-deck="'+checkbox+'"]');a.window.activateWindow();wait(200);a.window.web.grab().save(str(out/'share-decks.png'));click(a,'[data-action=share-send]')
    until(lambda:len(a.client().request('/v1/bootstrap')['invites'])==1,'sent deck invitation');until(lambda:not a.busy,'source export finished');assert ca.db.all('SELECT * FROM cards')==before
    b.poll(force=True);until(lambda:b.social and len(b.social['invites'])==1,'incoming deck');b.emit('bootstrap',b.social);click(b,'[data-thread="'+group_id+'"]');b.poll_messages(group_id)
    until(lambda:js(b,'!!document.querySelector(".deck-bubble [data-action=preview]")'),'group deck message')
    assert js(b,'document.querySelector(".message:not(.mine) .message-meta > span").textContent')==a.social['user']['name']
    click(b,'.deck-bubble [data-action=preview]')
    until(lambda:js(b,'!!document.querySelector("#destination")'),'received preview')
    b.window.activateWindow();wait(200);b.window.web.grab().save(str(out/'receive-deck.png'));click(b,'[data-action=accept]')
    until(lambda:len(cb.find_cards(''))==2,'native receiver import');until(lambda:not b.busy,'receiver import done')
    rfid=cb.decks.id_for_name('Practice::Science::Round 1');assert rfid and cb.decks.get(rfid)['resched'] is False
    assert len(cb.find_cards('deck:"Practice::Science::Round 1"'))==2
    until(lambda:a.client().request('/v1/bootstrap')['invites'][0]['state']=='accepted','acceptance receipt')
    assert hosts[1].reset_count==1 and cb.decks.config_dict_for_deck_id(cb.get_card(cb.find_cards('')[0]).odid)['new']['perDay']==17
    assert not any(m['kind']=='deck' for m in a.client().messages(tid)['messages']),'group deck never appears in the private conversation'
    assert js(a,'ankiLink.state.thread')==group_id
    for chat in (tid,group_id):
        click(b,'[data-thread="'+chat+'"]')
        for dark in (False,True):
            b.emit('setup',{'url':url,'dark':dark,'signed_in':True});wait(25)
            geometry=js(b,'(()=>{const h=document.querySelector(".chat-head").getBoundingClientRect(),a=document.querySelector(".chat-actions").getBoundingClientRect();return {gap:h.right-a.right,width:h.width};})()')
            assert 0<=geometry['gap']<=35,geometry
            for _ in range(4):
                selector='[data-action=conversation-options]';box=js(b,'(()=>{const r=document.querySelector('+json.dumps(selector)+').getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2];})()')
                QTest.mouseClick(b.window.web.focusProxy() or b.window.web,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,QtCore.QPoint(round(box[0]),round(box[1])));wait(25)
                assert js(b,'!!document.querySelector("#chat-notifications")'),'notification menu remains responsive'
                js(b,'window.keptNotification=document.querySelector("#chat-notifications");window.keptModal=document.querySelector(".modal");')
                b.emit('bootstrap',b.social);b.emit('status',{'people':[],'receipts':[],'typing':[]});wait(25)
                assert js(b,'keptModal===document.querySelector(".modal")&&keptNotification===document.querySelector("#chat-notifications")')
                assert js(b,'getComputedStyle(document.querySelector(".shade")).backdropFilter')=='none'
                QTest.keyClick(b.window.web.focusProxy() or b.window.web,Qt.Key.Key_Escape);wait(25)
                assert not js(b,'!!document.querySelector(".modal")')
    b.emit('setup',{'url':url,'dark':False,'signed_in':True});click(b,'[data-thread="'+tid+'"]')
    assert all(not c.window.web.page_.errors for c in controllers),[c.window.web.page_.errors for c in controllers]
    # Native in-Anki notice: no focus theft, no added status bar, bounded frame,
    # light/dark styling, immediate mute, and exact-conversation navigation.
    a.window.hide();b.window.hide();hosts[1].activateWindow();hosts[1].web.setFocus();wait(80)
    saved_cursor=dict(b.notification_cursor)
    message={'id':1000000,'sender':a.social['user']['id'],'kind':'text','text':'A quick message while you study. No need to leave your card.'}
    b.notify_messages(tid,[message]);wait(120);notice=b.notice
    assert notice and notice.width()<=340 and notice.height()<160
    assert app.focusWidget() is hosts[1].web,'notification must not steal study keyboard focus'
    assert hosts[1].findChild(QtWidgets.QStatusBar) is None,'notification must not create a bottom status bar'
    notice.grab().save(str(out/'notice-light.png'))
    theme.theme_manager.night_mode=True;notice.apply_theme();wait(80);notice.grab().save(str(out/'notice-dark.png'));theme.theme_manager.night_mode=False
    notice.mute_button.click();wait(80);assert b.notice is None and tid in b.muted_threads()
    message['id']+=1;b.notify_messages(tid,[message]);assert b.notice is None
    b.set_thread_muted(tid,False);message['id']+=1;b.notify_messages(tid,[message]);wait(80)
    QTest.mouseClick(b.notice.body,Qt.MouseButton.LeftButton);wait(100);assert b.dock.isVisible() and js(b,'ankiLink.state.thread')==tid
    assert len(cb.find_cards(''))==2,'notification click never imports again'
    for width in (300,420,680,820):
        hosts[1].resizeDocks([b.dock],[width],Qt.Orientation.Horizontal);wait(90)
        assert js(b,'document.documentElement.scrollWidth<=innerWidth'),f'chat overflow at {width}'
        click(b,'[data-action=conversation-options]')
        assert js(b,'document.documentElement.scrollWidth<=innerWidth'),f'options overflow at {width}'
        click(b,'[data-action=close-modal]')
    hosts[1].resizeDocks([b.dock],[360],Qt.Orientation.Horizontal);wait(120);b.dock.grab().save(str(out/'sidebar-conversation-dark.png'))
    click(b,'[data-action=back-chats]');click(b,'[data-tab=inbox]')
    assert js(b,'getComputedStyle(document.querySelector(".workspace")).display')=='flex'
    assert js(b,'document.documentElement.scrollWidth<=innerWidth'),'narrow deck inbox overflow'
    b.notification_cursor=saved_cursor
    print(json.dumps({'real_controller_two_user_flow':'passed','independent_minimize_restore_and_draft':'passed','sidebar_resize_shortcut_same_page_draft':'passed','notice_focus_mute_exact_chat_and_theme':'passed','delayed_group_navigation_and_feedback':'passed','group_details_shared_photo_and_removal':'passed','text_emoji_builtin_custom_stickers_images':'passed','stable_image_nodes':'passed','group_share_preview_native_import_receipt_no_DM':'passed','header_alignment_and_notification_menu_stress':'passed','source_unchanged':'passed','screenshots':str(out)}))
    for c in controllers:c.close()
    wait(150)  # Process deletion of independent windows/pages before app shutdown.
    pool.shutdown(wait=True)
    for h in hosts:h.col.close();h.close()
    server.shutdown();server.server_close();worker.join(2);temp.cleanup();app.quit()

if __name__=='__main__':main()
