"""Synthetic profile UI/crop visual QA. Optional QtWebEngine, no user account."""
import importlib.util,json,os,sys,types
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen');os.environ.setdefault('QTWEBENGINE_DISABLE_SANDBOX','1');os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS','--no-sandbox --disable-gpu --disable-dev-shm-usage')
from PyQt6 import QtCore,QtGui,QtWidgets
from PyQt6.QtWebEngineWidgets import QWebEngineView
root=Path(__file__).resolve().parents[1];out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True);web=root/'anki_link/web'
app=QtWidgets.QApplication(['profile-qa']);view=QWebEngineView();view.resize(1100,800);view.show()
boot={'user':{'id':'me','name':'You','username':'you','code':'DEMO'},'friends':[],'invites':[],'threads':[{'id':'chat','title':'Study friend','kind':'direct','members':[{'id':'me','name':'You'},{'id':'friend','name':'Study friend','username':'friend'}],'unread':0}]}
html='<!doctype html><html><head><meta charset="utf-8"><style>'+web.joinpath('app.css').read_text()+web.joinpath('controls.css').read_text()+'</style></head><body>'+web.joinpath('index.html').read_text()+'<script>window.pycmd=()=>{};</script><script>'+web.joinpath('app.js').read_text()+'</script><script>document.addEventListener("DOMContentLoaded",()=>{window.ankiLink.receive("setup",{dark:false,url:"https://example.test"});window.ankiLink.receive("bootstrap",'+json.dumps(boot)+');document.querySelector("[data-thread]").click();});</script></body></html>'
qt=types.ModuleType('aqt.qt')
for mod in (QtCore,QtGui,QtWidgets):
 for n in dir(mod):
  if not n.startswith('_'):setattr(qt,n,getattr(mod,n))
sys.modules['aqt.qt']=qt
spec=importlib.util.spec_from_file_location('crop_qa',root/'anki_link/avatar_crop.py');crop=importlib.util.module_from_spec(spec);spec.loader.exec_module(crop)
def shot():
 view.grab().save(str(out/'chat-icons.png'))
 view.page().runJavaScript('document.querySelector("[data-action=account]").click();')
 QtCore.QTimer.singleShot(200,account)
def account():
 view.grab().save(str(out/'profile-account.png'))
 image=QtGui.QImage(900,600,QtGui.QImage.Format.Format_ARGB32);image.fill(QtGui.QColor('#e5def8'));p=QtGui.QPainter(image);p.setPen(QtCore.Qt.PenStyle.NoPen);p.setBrush(QtGui.QColor('#7866b5'));p.drawEllipse(350,130,200,200);p.drawRoundedRect(250,350,400,300,100,100);p.end()
 dialog=crop.CropDialog(None,image);dialog.show();QtWidgets.QApplication.processEvents();dialog.grab().save(str(out/'profile-crop.png'));dialog.close();view.close();app.quit()
view.loadFinished.connect(lambda ok:QtCore.QTimer.singleShot(200,shot) if ok else app.exit(2));view.setHtml(html,QtCore.QUrl('file://'+str(web)+'/'));QtCore.QTimer.singleShot(12000,lambda:app.exit(3));sys.exit(app.exec())
