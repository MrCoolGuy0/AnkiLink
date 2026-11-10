"""A native resizable dock; the existing WebView moves here without reloading."""
from aqt.qt import QDockWidget,QWidget,QHBoxLayout,QLabel,QToolButton,QTimer,Qt


class Sidebar(QDockWidget):
    def __init__(self,owner):
        super().__init__('AnkiLink',owner.mw)
        self.owner=owner;self.setObjectName('anki_link_sidebar')
        self.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.setMinimumWidth(300)
        bar=QWidget(self);row=QHBoxLayout(bar);row.setContentsMargins(12,3,6,3)
        row.addWidget(QLabel('AnkiLink',bar));row.addStretch()
        for text,tip,callback in (('↗','Open in a separate window',owner.open),('×','Hide AnkiLink sidebar',owner.hide_sidebar)):
            button=QToolButton(bar);button.setText(text);button.setToolTip(tip);button.setFixedSize(26,26);button.setAutoRaise(True);button.clicked.connect(callback);row.addWidget(button)
        self.setTitleBarWidget(bar)
        self.save_timer=QTimer(self);self.save_timer.setSingleShot(True);self.save_timer.setInterval(450);self.save_timer.timeout.connect(self.save_width)
        self.visibilityChanged.connect(lambda *_:owner.sync_visibility())

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'save_timer') and self.isVisible():self.save_timer.start()

    def save_width(self):
        if self.owner.closed or self.owner.ui_mode!='dock' or not self.isVisible():return
        value=max(300,min(1800,self.width()))
        if self.owner.store.data.get('sidebar_width')!=value:
            self.owner.store.data['sidebar_width']=value;self.owner.store.save()

    def closeEvent(self,event):
        self.save_width();self.owner.hide_sidebar();event.accept()
