"""Compact, focus-preserving notifications inside Anki; no network or collection work."""
from aqt.qt import QFrame,QLabel,QToolButton,QVBoxLayout,QHBoxLayout,QTimer,QEvent,Qt,QColor,QGraphicsDropShadowEffect,QStatusBar


def preview_text(message):
    kind=message.get('kind','text')
    if kind=='image':return 'Sent an image'
    if kind=='sticker':return 'Sent a sticker'
    if kind=='deck':return 'Shared a deck: '+str(message.get('text') or 'Deck invitation')[:100]
    return ' '.join(str(message.get('text') or 'New message').split())[:160]


class Notice(QFrame):
    def __init__(self,owner,thread,message):
        super().__init__(owner.mw)
        self.owner=owner;self.thread=thread;self.setObjectName('ankiLinkNotice')
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating,True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        root=QVBoxLayout(self);root.setContentsMargins(15,12,12,10);root.setSpacing(5)
        top=QHBoxLayout();top.setSpacing(9)
        self.avatar=QLabel(self);self.avatar.setObjectName('noticeAvatar');self.avatar.setFixedSize(32,32);self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title=QLabel(self);self.title.setObjectName('noticeTitle');self.title.setTextFormat(Qt.TextFormat.PlainText);self.title.setMinimumWidth(0)
        self.dismiss=QToolButton(self);self.dismiss.setText('×');self.dismiss.setToolTip('Dismiss');self.dismiss.setFixedSize(24,24);self.dismiss.clicked.connect(self.close)
        top.addWidget(self.avatar);top.addWidget(self.title,1);top.addWidget(self.dismiss);root.addLayout(top)
        self.body=QLabel(self);self.body.setTextFormat(Qt.TextFormat.PlainText);self.body.setWordWrap(True);self.body.setMaximumHeight(40);root.addWidget(self.body)
        actions=QHBoxLayout();actions.setSpacing(12)
        self.open_button=QToolButton(self);self.open_button.setText('Open');self.open_button.clicked.connect(self.open_thread)
        self.mute_button=QToolButton(self);self.mute_button.setText('Mute');self.mute_button.clicked.connect(self.mute)
        actions.addWidget(self.open_button);actions.addWidget(self.mute_button);actions.addStretch();root.addLayout(actions)
        for control in (self.dismiss,self.open_button,self.mute_button):control.setFocusPolicy(Qt.FocusPolicy.NoFocus);control.setCursor(Qt.CursorShape.PointingHandCursor)
        shadow=QGraphicsDropShadowEffect(self);shadow.setBlurRadius(22);shadow.setOffset(0,4);shadow.setColor(QColor(0,0,0,45));self.setGraphicsEffect(shadow)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.timeout.connect(self.close)
        owner.mw.installEventFilter(self);self.update_message(thread,message)

    def update_message(self,thread,message):
        self.thread=thread;self.message=message
        title=thread.get('title') or message.get('name') or 'New message'
        self.avatar.setText(''.join(part[0] for part in title.split()[:2]).upper())
        self.full_title=title;self.body.setText(preview_text(message));self.apply_theme();self.reposition();self.timer.start(6500)

    def apply_theme(self):
        from aqt.theme import theme_manager
        dark=theme_manager.night_mode
        bg,ink,muted,border,accent,soft=('#222532','#eceef8','#a5abc1','#363b50','#b2a2ff','#38314f') if dark else ('#ffffff','#25273a','#7c8196','#e7e9f0','#6854dc','#efecff')
        self.setStyleSheet(f'QFrame#ankiLinkNotice {{background:{bg};border:1px solid {border};border-radius:14px;}} QLabel {{color:{ink};background:transparent;border:0;font-size:12px;}} QLabel#noticeTitle {{font-weight:600;font-size:13px;}} QLabel#noticeAvatar {{background:{soft};color:{accent};border-radius:10px;font-weight:600;}} QToolButton {{background:transparent;color:{accent};border:0;border-radius:5px;padding:3px 5px;font-size:12px;}} QToolButton:hover {{background:{soft};}}')

    def reposition(self):
        host=self.owner.mw
        width=min(340,max(220,host.width()-32));self.setFixedWidth(width)
        self.title.setText(self.title.fontMetrics().elidedText(self.full_title,Qt.TextElideMode.ElideRight,max(60,width-105)))
        self.adjustSize();bottom=host.height()-16
        status=host.findChild(QStatusBar)
        if status and status.isVisible():bottom-=status.height()
        self.move(max(8,host.width()-self.width()-16),max(8,bottom-self.height()))

    def eventFilter(self,obj,event):
        if obj is self.owner.mw and event.type() in (QEvent.Type.Resize,QEvent.Type.Show):self.reposition()
        return False

    def enterEvent(self,event):self.timer.stop();super().enterEvent(event)
    def leaveEvent(self,event):self.timer.start(3500);super().leaveEvent(event)

    def mouseReleaseEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:self.open_thread()
        super().mouseReleaseEvent(event)

    def open_thread(self):
        tid=self.thread['id'];self.close();self.owner.open_conversation(tid)

    def mute(self):
        self.owner.set_thread_muted(self.thread['id'],True)

    def closeEvent(self,event):
        self.timer.stop();self.owner.mw.removeEventFilter(self)
        if getattr(self.owner,'notice',None) is self:self.owner.notice=None
        super().closeEvent(event);self.deleteLater()
