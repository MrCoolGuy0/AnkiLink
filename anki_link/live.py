"""Qt-owned live connection. Account tokens never enter HTML or URL queries."""
from __future__ import annotations
import json
import time
from PyQt6.QtCore import QObject,QTimer,QUrl,QEvent
from PyQt6.QtNetwork import QNetworkRequest
from PyQt6.QtWebSockets import QWebSocket

class Live(QObject):
    def __init__(self,owner):
        super().__init__(owner.mw);self.owner=owner;self.socket=QWebSocket();self.socket.setParent(self)
        self.online=False;self.stopped=False;self.attempt=0;self.last_input=time.monotonic();self.last_pull=0;self.pending={};self.key=None
        self.socket.connected.connect(self.connected);self.socket.disconnected.connect(self.disconnected)
        self.socket.textMessageReceived.connect(self.receive)
        self.socket.errorOccurred.connect(lambda *_:self.disconnected())
        self.timer=QTimer(self);self.timer.setInterval(1000);self.timer.timeout.connect(self.tick);self.timer.start()
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().installEventFilter(self)
        self.retry_at=0;self.connect_now()
    def eventFilter(self,obj,event):
        if event.type() in (QEvent.Type.KeyPress,QEvent.Type.MouseButtonPress,QEvent.Type.Wheel,QEvent.Type.MouseMove):self.last_input=time.monotonic()
        return False
    def connect_now(self):
        if self.stopped or not self.owner.store.token:return
        self.key=(self.owner.store.data['url'],self.owner.store.token)
        url=self.key[0].replace('https://','wss://',1).replace('http://','ws://',1)+'/v1/live'
        request=QNetworkRequest(QUrl(url));request.setRawHeader(b'Authorization',('Bearer '+self.key[1]).encode());request.setRawHeader(b'User-Agent',b'AnkiLink/1.4.0')
        self.retry_at=float('inf');self.connect_started=time.monotonic();self.socket.open(request)
    def connected(self):
        # Wait for the protocol greeting, not just the upgrade, before sending.
        self.attempt=0;self.connect_started=time.monotonic()
    def disconnected(self):
        if self.stopped:return
        self.online=False
        if self.retry_at==float('inf'):
            self.retry_at=time.monotonic()+min(15,0.5*2**min(self.attempt,5));self.attempt+=1
        # A lost ACK is retried via HTTP with exactly the same nonce.
        pending=list(self.pending.values());self.pending.clear()
        for data,_ in pending:self.owner.send_message_http(data)
    def send(self,action,data):
        if not self.online or self.stopped:return False
        if action=='message':self.pending[data['nonce']]=(dict(data),time.monotonic())
        try:self.socket.sendTextMessage(json.dumps({'action':action,'data':data},ensure_ascii=False));return True
        except Exception:self.disconnected();return False
    def watch(self,thread,after=0):return self.send('watch',{'thread':thread,'after':after})
    def receive(self,text):
        if self.stopped or len(text)>2*1024*1024:return
        try:
            frame=json.loads(text);event=frame['event'];data=frame.get('data')
            if event=='live_ready':
                self.online=True;self.retry_at=float('inf');self.owner.live_ready();return
            if event=='sent':self.pending.pop(data.get('nonce'),None)
            if event=='live_error' and data.get('action')=='message':
                old=self.pending.pop(data.get('nonce'),None)
                if old:self.owner.send_message_http(old[0])
                return
            self.owner.live_event(event,data)
        except (ValueError,KeyError,TypeError):return
    def tick(self):
        if self.stopped:return
        visible=self.owner.window_visible() if hasattr(self.owner,'window_visible') else bool(self.owner.window and self.owner.window.isVisible() and not self.owner.window.isMinimized())
        interval=250 if visible else 1000
        if self.timer.interval()!=interval:self.timer.setInterval(interval)
        stamp=time.monotonic()
        if not self.online:
            if stamp>=self.retry_at:self.socket.abort();self.connect_now()
            elif self.retry_at==float('inf') and stamp-getattr(self,'connect_started',stamp)>15:self.socket.abort();self.disconnected()
            return
        if stamp-self.last_pull>=(0.25 if visible else 2):self.last_pull=stamp;self.send('pull',{'reaction_after':getattr(self.owner,'reaction_cursor',0)})
        self.owner.publish_presence()
        for key,(data,sent) in list(self.pending.items()):
            if stamp-sent>8:self.pending.pop(key,None);self.owner.send_message_http(data)
    def close(self):
        self.stopped=True;self.online=False;self.timer.stop();self.pending.clear();self.socket.close();self.deleteLater()
