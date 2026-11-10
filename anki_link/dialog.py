from __future__ import annotations
import base64
import copy
import hashlib
import json
import mimetypes
import math
import os
from pathlib import Path
import tempfile
import time
import types
import uuid
from aqt.qt import QDialog,QVBoxLayout,QTimer,QFileDialog,QApplication,QImageReader,Qt,QSystemTrayIcon,QEvent
from aqt.webview import AnkiWebView
from aqt.operations import QueryOp,CollectionOp
from aqt.theme import theme_manager
from .config import Store
from .net import Client,server_url
from . import transfer
from . import media

APPEARANCE_CAPTIONS = {
    'default': (0xFFFFFFFF, 0xFFFFFFFF),
    'ankiretro': (0x974624, 0xFFFFFF),
    'ankiretro-baby-blue': (0xA57445, 0xFFFFFF),
    'ankiretro-maroon': (0x3D1E74, 0xFFFFFF),
    'ankirise': (0x766E45, 0xFFFBEF),
    'ankimessage': (0xFFFFFFFF, 0xFFFFFFFF),
}

class Window(QDialog):
    def __init__(self,owner):
        # A normal, independent window can minimize without taking Anki with
        # it. The profile controller retains and cleans up this same instance.
        super().__init__(None,Qt.WindowType.Window);self.owner=owner;self.resize(1180,800);self.setMinimumSize(760,550)
        from aqt.qt import QIcon
        self.retro_icon=QIcon(str(Path(__file__).parent/'web/retro-flower.svg'))
        self.apply_appearance()
        self.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint,True);self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint,True);self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint,True);self.setWindowModality(Qt.WindowModality.NonModal);self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose,False)
        if getattr(owner,'sidebar_action',None):self.addAction(owner.sidebar_action)
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0);self.web=AnkiWebView(parent=self,title='AnkiLink');layout.addWidget(self.web)
        # stdHtml(context=...) supplies rendering context only. The incoming
        # pycmd bridge has a separate handler/context registration in Anki.
        self.web.set_bridge_command(self.bridge,self)
        package=owner.mw.addonManager.addonFromModule(owner.module);prefix=f'/_addons/{package}/web/'
        html=(Path(__file__).parent/'web/index.html').read_text(encoding='utf-8')
        # This is a complete app, not an Anki toolbar. Native webview button
        # hover/focus rules otherwise replace our purple buttons with white.
        self.web.stdHtml(html,css=[prefix+'app.css',prefix+'controls.css',prefix+'retro.css',prefix+'rise.css',prefix+'message.css'],js=[prefix+'app.js'],context=self,default_css=False)
    def bridge(self,message):
        return self.owner.message((False,None),message,self)[1]
    def showEvent(self,event):
        super().showEvent(event)
        self.apply_appearance(color_caption=True)
    def apply_appearance(self, *, color_caption=False):
        appearance=self.owner.appearance()
        retro=appearance.startswith('ankiretro')
        self.setWindowTitle('AnkiLink ♡' if retro else 'AnkiLink')
        icon=self.retro_icon if retro and not self.retro_icon.isNull() else self.owner.mw.windowIcon()
        self.setWindowIcon(icon)
        if not color_caption or os.name!='nt':return
        try:
            import ctypes
            from ctypes import wintypes
            set_attribute=ctypes.windll.dwmapi.DwmSetWindowAttribute
            set_attribute.argtypes=(wintypes.HWND,wintypes.DWORD,wintypes.LPCVOID,wintypes.DWORD)
            set_attribute.restype=wintypes.LONG
            handle=wintypes.HWND(int(self.winId()))
            # Windows 11 supports caption and text COLORREF values (0x00BBGGRR).
            caption_color,text_color=APPEARANCE_CAPTIONS[appearance]
            caption=ctypes.c_uint32(caption_color)
            text=ctypes.c_uint32(text_color)
            if set_attribute(handle,35,ctypes.byref(caption),ctypes.sizeof(caption))==0:
                set_attribute(handle,36,ctypes.byref(text),ctypes.sizeof(text))
        except (AttributeError,OSError):
            pass  # Use the platform caption when custom colors are unavailable.
    def closeEvent(self,event):self.hide();self.owner.sync_visibility();event.accept()
    def changeEvent(self,event):
        super().changeEvent(event)
        if event.type()==QEvent.Type.WindowStateChange:self.owner.sync_visibility()

class Controller:
    def __init__(self,mw,module,action=None):
        self.mw=mw;self.module=module;self.menu_action=action;self.store=Store(mw.pm.profileFolder());self.window=None;self.closed=False;self.polling=False;self.busy=False;self.epoch=0;self.social=None;self.active_thread=None;self.previews={};self.blobs=set();self.preparing=set();self.last_notice=0;self.temp=tempfile.TemporaryDirectory(prefix='anki-link-')
        self.message_polls=set();self.message_after={};self.history_loaded=set();self.live=None;self.uploads={};self.avatar_job=None
        self.pending_actions={};self.refresh_queued=False;self.blob_queue=[];self.blob_active=0
        self.group_avatar_jobs={};self.group_photos={};self.removed_groups={};self.group_versions={};self.thread_files={};self.revoked_files=set();self.revoked_thread_files={};self.file_generations={};self.membership_epoch=0;self.legacy_removals={};self.thread_epochs={};self.reaction_cursor=0
        self.dock=None;self.ui_mode='window';self.web_ready=False;self.pending_open_thread=None
        self.notice=None;self.notification_cursor={}
        self.timer=QTimer(mw);self.timer.setInterval(8000);self.timer.timeout.connect(self.poll)
        self.tray=None
        if QSystemTrayIcon.isSystemTrayAvailable():self.tray=QSystemTrayIcon(mw.windowIcon(),mw);self.tray.setToolTip('AnkiLink');self.tray.activated.connect(lambda *_:self.open());self.tray.show()
        if self.store.token:self.timer.start();self.ensure_live()
    def client(self):
        key=(self.store.data['url'],self.store.token)
        if getattr(self,'http_key',None)!=key:
            if getattr(self,'http_client',None):self.http_client.close()
            self.http_key=key;self.http_client=Client(*key)
        return self.http_client
    def account_key(self):
        return self.store.data.get('url','')+'|'+self.store.data.get('user',{}).get('id','')
    def appearance(self):
        value=self.store.data.get('appearance')
        return value if isinstance(value,str) and value in APPEARANCE_CAPTIONS else 'default'
    def set_appearance(self,theme):
        if not isinstance(theme,str) or theme not in APPEARANCE_CAPTIONS:
            raise ValueError('Choose an appearance from the list.')
        previous=self.appearance()
        if theme!=previous:
            self.store.data['appearance']=theme
            try:
                self.store.save()
            except Exception:
                self.store.data['appearance']=previous
                self.emit('appearance',previous)
                raise
            if self.window:self.window.apply_appearance(color_caption=self.window.isVisible())
        self.emit('appearance',theme)
    def chat_themes(self):
        import re
        values=self.store.data.get('chat_themes_by_account',{}).get(self.account_key(),{})
        if not isinstance(values,dict):return {}
        return {key:value.lower() for key,value in values.items() if isinstance(key,str) and isinstance(value,str) and re.fullmatch(r'#[0-9a-fA-F]{6}',value)}
    def set_chat_theme(self,tid,color):
        import re
        if not isinstance(color,str) or color!='default' and not re.fullmatch(r'#[0-9a-fA-F]{6}',color):raise ValueError('Choose a valid chat color.')
        if not any(t['id']==tid for t in (self.social or {}).get('threads',[])):raise ValueError('Open an available conversation first.')
        themes=self.store.data.setdefault('chat_themes_by_account',{}).setdefault(self.account_key(),{})
        if color=='default':themes.pop(tid,None)
        else:themes[tid]=color.lower()
        self.store.save();self.emit('chat_themes',self.chat_themes())
    def activity_enabled(self):return self.store.data.get('activity',{}).get(self.account_key(),False) is True
    def activity_payload(self,idle=False):
        deck=''
        share=self.activity_enabled()
        collection=getattr(self.mw,'col',None)
        if share and not idle and getattr(self.mw,'state',None)=='review' and collection is not None:
            card=getattr(getattr(self.mw,'reviewer',None),'card',None)
            if card:
                cached=getattr(self,'activity_deck_cache',None);stamp=time.monotonic()
                if cached and cached[0]==card.did and stamp-cached[2]<30:deck=cached[1]
                else:
                    found=collection.decks.get(card.did)
                    if found:deck=found['name'].split('::')[-1];self.activity_deck_cache=(card.did,deck,stamp)
        return {'share':share,'status':'idle' if idle else 'online','deck':deck}
    def ensure_live(self):
        if self.closed or not self.store.token or getattr(self,'live',None):return
        try:
            from .live import Live
            self.live=Live(self)
        except ImportError:pass  # Older Qt builds retain the HTTP fallback.
    def stop_live(self):
        if getattr(self,'live',None):self.live.close();self.live=None
    def live_ready(self):
        if self.active_thread:self.live.watch(self.active_thread,self.message_after.get(self.active_thread,0) if self.active_thread in self.history_loaded else 0)
        self.publish_presence(force=True)
        self.emit('live_connected',None)
    def social_action(self,name,data):
        live=getattr(self,'live',None)
        if live and live.send(name,data):return
        client=self.client();self.run(lambda:client.action(name,data),failure=lambda _:None)
    def publish_presence(self, *, activity_change=False, force=False):
        if self.closed or not self.store.token:return
        if getattr(self,'presence_pending',False):
            if force:self.presence_resend=True
            return

        stamp=time.monotonic()
        recent=stamp-getattr(self,'last_presence_sent',float('-inf'))<20
        if recent and not (activity_change or force):return
        live=getattr(self,'live',None)
        payload=self.activity_payload(stamp-getattr(live,'last_input',stamp)>=300)
        if recent and not force and payload==getattr(self,'last_presence_payload',None):return

        self.last_presence_sent=stamp
        self.last_presence_payload=payload
        if live and live.send('presence',payload):return

        # Keep a single HTTP write in flight so a slow reply cannot pile up
        # study updates or overwrite a later change to the sharing setting.
        client=self.client()
        self.presence_pending=True
        def finished(_):
            self.presence_pending=False
            resend=getattr(self,'presence_resend',False)
            self.presence_resend=False
            self.publish_presence(activity_change=True,force=resend)
        self.run(lambda:client.action('presence',payload),finished,finished)

    def study_changed(self,*args):
        if self.store.token and not self.closed and self.activity_enabled():
            self.publish_presence(activity_change=True)
    def group_accessible(self,tid):
        return tid not in getattr(self,'removed_groups',{})
    def remember_thread_files(self,tid,rows):
        if not tid:return
        if not hasattr(self,'thread_files'):self.thread_files={}
        files=self.thread_files.setdefault(tid,{})
        for row in rows:
            meta=row.get('attachment') or row.get('avatar')
            if isinstance(meta,dict) and meta.get('id'):files[meta['id']]=dict(meta)
    def remove_group(self,tid,membership_version=None):
        if not hasattr(self,'removed_groups'):self.removed_groups={}
        group=next((t for t in (self.social or {}).get('threads',[]) if t['id']==tid),{})
        if membership_version is not None and membership_version<group.get('membership_version',0):return
        # Source ordering also protects older servers without removal versions.
        self.membership_epoch=getattr(self,'membership_epoch',0)+1
        if not hasattr(self,'thread_epochs'):self.thread_epochs={}
        self.thread_epochs[tid]=self.thread_epochs.get(tid,0)+1
        if not hasattr(self,'legacy_removals'):self.legacy_removals={}
        if membership_version is None and (tid not in self.removed_groups or tid in self.legacy_removals):self.legacy_removals[tid]=self.membership_epoch
        elif membership_version is not None:self.legacy_removals.pop(tid,None)
        self.removed_groups[tid]=max(self.removed_groups.get(tid,0),group.get('membership_version',0),membership_version or 0)
        self.remember_thread_files(tid,[group])
        for invitation in (self.social or {}).get('invites',[]):
            if invitation.get('thread')==tid:
                self.remember_thread_files(tid,[invitation]);path=getattr(self,'previews',{}).pop(invitation['id'],None)
                if path:Path(path).unlink(missing_ok=True)
        if self.social:
            self.social['threads']=[t for t in self.social.get('threads',[]) if t['id']!=tid]
            self.social['invites']=[i for i in self.social.get('invites',[]) if i.get('thread')!=tid]
        for key,item in list(getattr(self,'message_invites',{}).items()):
            if item.get('thread')==tid:
                self.remember_thread_files(tid,[item]);path=getattr(self,'previews',{}).pop(key,None);del self.message_invites[key]
                if path:Path(path).unlink(missing_ok=True)
        for key in ('message_after','notification_cursor','group_avatar_jobs','group_photos','group_versions'):
            getattr(self,key,{}).pop(tid,None)
        self.history_loaded.discard(tid)
        for key,item in list(self.uploads.items()):
            if item.get('thread')==tid:del self.uploads[key]
        files=getattr(self,'thread_files',{}).pop(tid,{})
        if not hasattr(self,'revoked_files'):self.revoked_files=set()
        self.revoked_files.update(files)
        if not hasattr(self,'revoked_thread_files'):self.revoked_thread_files={}
        self.revoked_thread_files.setdefault(tid,set()).update(files)
        if not hasattr(self,'file_generations'):self.file_generations={}
        for fid in files:self.file_generations[fid]=self.file_generations.get(fid,0)+1
        for fid,meta in files.items():
            getattr(self,'blobs',set()).discard(fid);getattr(self,'preparing',set()).discard(fid)
            try:
                cached=media.cache_path(self.store.folder,self.store.data['url'],self.social['user']['id'],meta)
                if cached:cached.unlink(missing_ok=True)
            except (AttributeError,KeyError,OSError):pass
        self.blob_queue=[meta for meta in getattr(self,'blob_queue',[]) if meta.get('id') not in files]
        if self.active_thread==tid:
            self.active_thread=None
            live=getattr(self,'live',None)
            if live:
                for key,(payload,_) in list(getattr(live,'pending',{}).items()):
                    if payload.get('thread')==tid:live.pending.pop(key,None)
        if getattr(self,'notice',None) and self.notice.thread['id']==tid:self.notice.close()
        self.emit('group_removed',{'thread':tid,'_membership_epoch':self.membership_epoch,**({'membership_version':membership_version} if membership_version is not None else {})})
    def membership_changed(self,data):
        tid=data['thread']
        if data.get('removed') and data['removed']==(self.social or {}).get('user',{}).get('id'):
            self.remove_group(tid,data.get('membership_version'));return
        self.membership_epoch=getattr(self,'membership_epoch',0)+1
        if not hasattr(self,'group_versions'):self.group_versions={}
        self.group_versions[tid]=max(self.group_versions.get(tid,0),data.get('membership_version',0))
        group=next((t for t in (self.social or {}).get('threads',[]) if t['id']==tid),None)
        if group and data.get('members') and data.get('membership_version',0)>=group.get('membership_version',0):
            group.update({k:data[k] for k in ('owner','members','membership_version')})
    def status_memberships(self,data,source_epoch=None):
        if source_epoch is not None and source_epoch<getattr(self,'membership_epoch',0):return
        if 'group_memberships' not in data or not self.social:return
        memberships={g['thread']:g.get('membership_version',0) for g in data['group_memberships']}
        for group in list(self.social.get('threads',[])):
            if group['kind']=='group' and group['id'] not in memberships:self.remove_group(group['id'])
        if any(version>next((g.get('membership_version',0) for g in self.social.get('threads',[]) if g['id']==tid),-1) for tid,version in memberships.items()):self.poll(force=True)
    def live_event(self,event,data,source_epoch=None):
        if self.closed:return
        if event=='group_removed':self.remove_group(data['thread'],data.get('membership_version'));return
        if event=='membership_updated':self.membership_changed(data);self.poll(force=True);return
        if event=='reaction_updated':
            if self.group_accessible(data['thread']):self.emit(event,data)
            return
        if event=='status':
            if source_epoch is not None and source_epoch<getattr(self,'membership_epoch',0):return
            self.status_memberships(data,source_epoch)
            if 'people' in data:
                self.presence_snapshot=(data['people'],data.get('server_time'),time.monotonic())
            cursor=data.get('reaction_cursor')
            if isinstance(cursor,(int,float)) and not isinstance(cursor,bool) and math.isfinite(cursor) and cursor>=0:self.reaction_cursor=max(getattr(self,'reaction_cursor',0),cursor)
        if event=='group_updated':self.group_changed(data);return
        if event=='messages':
            self.remember_invites(data.get('invites',[]))
            tid=data['thread']
            if not self.group_accessible(tid):return
            messages=data.get('messages',[]);self.remember_thread_files(tid,messages);self.status_memberships(data)
            if messages:
                last=max(m['id'] for m in messages)
                if data.get('history'):self.history_loaded.add(tid)
                if tid in self.history_loaded:self.message_after[tid]=max(self.message_after.get(tid,0),last)
                # Delivered acknowledges receipt by the app. Seen is sent only
                # by the visible, focused conversation in the WebView.
                self.social_action('delivered',{'thread':tid,'last':last})
                if not data.get('history'):self.notify_messages(tid,messages)
        if event=='sent':
            if not self.group_accessible(data.get('thread')):return
            self.uploads.pop(data.get('nonce'),None)
        if event in ('status','receipts','typing','messages','sent'):self.emit(event,data)
        elif event=='live_error' and data.get('action')=='watch':self.poll_messages(data['thread'])
    def avatar_progress(self,job,phase,error=None):
        if self.closed or self.epoch!=job['epoch'] or getattr(self,'avatar_job',None) is not job:return
        job['phase']=phase;value={'request':job['id'],'uid':job['owner'][1],'phase':phase,'remove':job['remove'],'retryable':bool(job['remove'] or job.get('path'))}
        if error:value['message']=error
        if job.get('raw') and phase in ('uploading','saving'):value['preview']='data:'+job['mime']+';base64,'+base64.b64encode(job['raw']).decode()
        self.emit('profile_progress',value)
    def set_avatar(self,data):
        previous=getattr(self,'avatar_job',None)
        if previous and previous['phase'] not in ('failed','cancelled'):return
        job={'id':data.get('request') or uuid.uuid4().hex,'epoch':self.epoch,'owner':(self.store.data['url'],self.store.data['user']['id']),'remove':data.get('remove') is True,'phase':'choosing','meta':None}
        self.avatar_job=job
        if job['remove']:self.save_avatar(job);return
        self.avatar_progress(job,'choosing')
        try:
            path,_=QFileDialog.getOpenFileName(self.ui_parent(),'Choose a profile picture','','Images (*.png *.jpg *.jpeg *.gif *.webp)')
            if not path:self.avatar_progress(job,'cancelled');self.avatar_job=None;return
            if Path(path).stat().st_size>12*1024*1024:raise ValueError('Choose an image up to 12 MB.')
        except Exception as error:self.avatar_progress(job,'failed',str(error));return
        job['path']=path;self.prepare_avatar(job)
    def choose_avatar_crop(self,path):
        from .avatar_crop import crop_avatar
        return crop_avatar(self.ui_parent(),path,self.temp.name)
    def prepare_avatar(self,job):
        self.avatar_progress(job,'preparing')
        def work():return media.prepare_avatar(job['path'],self.temp.name,edge=1600)
        def prepared(path):
            if getattr(self,'avatar_job',None) is not job:return
            self.avatar_progress(job,'cropping')
            try:
                cropped=self.choose_avatar_crop(path)
                if self.closed or self.epoch!=job['epoch'] or getattr(self,'avatar_job',None) is not job:return
                if not cropped:self.avatar_progress(job,'cancelled');self.avatar_job=None;return
                job['raw']=Path(cropped).read_bytes();job['mime']=mimetypes.guess_type(str(cropped))[0] or 'image/png';job['name']=Path(cropped).name
            except Exception as error:self.avatar_progress(job,'failed',str(error));return
            self.upload_avatar(job)
        self.run(work,prepared,lambda error:self.avatar_progress(job,'failed',error))
    def upload_avatar(self,job):
        self.avatar_progress(job,'uploading');client=self.client()
        def work():
            meta=client.request('/v1/upload',raw=job['raw'],mime=job['mime'],name=job['name'],background=True)
            media.cache_image(media.cache_path(self.store.folder,*job['owner'],meta),job['raw'],meta)
            return meta
        def uploaded(meta):
            if getattr(self,'avatar_job',None) is not job:return
            job['meta']=meta;self.save_avatar(job)
        self.run(work,uploaded,lambda error:self.avatar_progress(job,'failed',error))
    def save_avatar(self,job):
        self.avatar_progress(job,'saving');client=self.client()
        def finished(result):
            if getattr(self,'avatar_job',None) is not job:return
            user=result['user'];meta=job.get('meta')
            if meta:
                self.blobs.add(meta['id']);self.emit('blob',{'id':meta['id'],'src':'data:'+meta['mime']+';base64,'+base64.b64encode(job['raw']).decode()})
            if self.social:self.social['user']=user
            self.store.data['user']=user;self.store.save();self.avatar_job=None
            self.emit('profile_updated',{'user':user,'request':job['id'],'remove':job['remove']});self.poll(force=True)
        self.run(lambda:client.request('/v1/actions/profile',data={'avatar':None if job['remove'] else job['meta']['id']},background=True),finished,lambda error:self.avatar_progress(job,'failed',error))
    def retry_avatar(self,request):
        job=getattr(self,'avatar_job',None)
        if not job or job['id']!=request or job['epoch']!=self.epoch or job['phase']!='failed':return
        if job['remove'] or job.get('meta'):self.save_avatar(job)
        elif job.get('raw'):self.upload_avatar(job)
        elif job.get('path'):self.prepare_avatar(job)
    def group_job_current(self,job):
        return not self.closed and self.epoch==job['epoch'] and getattr(self,'group_avatar_jobs',{}).get(job['thread']) is job
    def group_avatar_progress(self,job,phase,error=None):
        if not self.group_job_current(job):return
        job['phase']=phase;value={'request':job['id'],'thread':job['thread'],'phase':phase,'remove':job['remove'],'retryable':bool(job['remove'] or job.get('path'))}
        if error:value['message']=error
        if job.get('raw') and phase in ('uploading','saving'):value['preview']='data:'+job['mime']+';base64,'+base64.b64encode(job['raw']).decode()
        self.emit('group_photo_progress',value)
    def set_group_avatar(self,data):
        tid=data['thread']
        if not hasattr(self,'group_avatar_jobs'):self.group_avatar_jobs={}
        previous=self.group_avatar_jobs.get(tid)
        if previous and previous['phase'] not in ('failed','cancelled'):return
        job={'id':data.get('request') or uuid.uuid4().hex,'epoch':self.epoch,'thread':tid,'owner':(self.store.data['url'],self.store.data['user']['id']),'remove':data.get('remove') is True,'phase':'choosing','meta':None}
        self.group_avatar_jobs[tid]=job
        try:
            group=next((t for t in (self.social or {}).get('threads',[]) if t['id']==tid and t['kind']=='group'),None)
            if not group:raise ValueError('Open this group first.')
            if job['remove']:self.save_group_avatar(job);return
            self.group_avatar_progress(job,'choosing')
            path,_=QFileDialog.getOpenFileName(self.ui_parent(),'Choose a group photo','','Images (*.png *.jpg *.jpeg *.gif *.webp)')
            if not path:self.group_avatar_progress(job,'cancelled');self.group_avatar_jobs.pop(tid,None);return
            if Path(path).stat().st_size>12*1024*1024:raise ValueError('Choose an image up to 12 MB.')
            job['path']=path;self.prepare_group_avatar(job)
        except Exception as error:self.group_avatar_progress(job,'failed',str(error))
    def choose_group_crop(self,path):
        from .avatar_crop import crop_avatar
        return crop_avatar(self.ui_parent(),path,self.temp.name,'Crop group photo')
    def prepare_group_avatar(self,job):
        self.group_avatar_progress(job,'preparing')
        def prepared(path):
            if not self.group_job_current(job):return
            self.group_avatar_progress(job,'cropping')
            try:
                cropped=self.choose_group_crop(path)
                if not self.group_job_current(job):return
                if not cropped:self.group_avatar_progress(job,'cancelled');self.group_avatar_jobs.pop(job['thread'],None);return
                job['raw']=Path(cropped).read_bytes();job['mime']='image/png';job['name']=Path(cropped).name
            except Exception as error:self.group_avatar_progress(job,'failed',str(error));return
            self.upload_group_avatar(job)
        self.run(lambda:media.prepare_avatar(job['path'],self.temp.name,edge=1600),prepared,lambda error:self.group_avatar_progress(job,'failed',error))
    def upload_group_avatar(self,job):
        self.group_avatar_progress(job,'uploading');client=self.client()
        def work():
            meta=client.request('/v1/upload',raw=job['raw'],mime=job['mime'],name=job['name'],bulk=True)
            media.cache_image(media.cache_path(self.store.folder,*job['owner'],meta),job['raw'],meta);return meta
        def uploaded(meta):
            if not self.group_job_current(job):return
            job['meta']=meta;self.save_group_avatar(job)
        self.run(work,uploaded,lambda error:self.group_avatar_progress(job,'failed',error))
    def save_group_avatar(self,job):
        self.group_avatar_progress(job,'saving');client=self.client()
        def finished(result):
            if not self.group_job_current(job):return
            meta=job.get('meta')
            if meta:
                self.blobs.add(meta['id']);self.emit('blob',{'id':meta['id'],'src':'data:'+job['mime']+';base64,'+base64.b64encode(job['raw']).decode()})
            self.group_avatar_jobs.pop(job['thread'],None);self.group_changed(result)
            self.emit('group_photo_saved',dict(result,request=job['id']));self.poll(force=True)
        self.run(lambda:client.action('group_photo',{'thread':job['thread'],'avatar':None if job['remove'] else job['meta']['id']}),finished,lambda error:self.group_avatar_progress(job,'failed',error))
    def retry_group_avatar(self,tid,request):
        job=getattr(self,'group_avatar_jobs',{}).get(tid)
        if not job or job['id']!=request or job['phase']!='failed' or not self.group_job_current(job):return
        if job['remove'] or job.get('meta'):self.save_group_avatar(job)
        elif job.get('raw'):self.upload_group_avatar(job)
        elif job.get('path'):self.prepare_group_avatar(job)
    def group_changed(self,data):
        if not hasattr(self,'group_photos'):self.group_photos={}
        tid=data['thread'];old=self.group_photos.get(tid,{})
        if data.get('avatar_version',0)<old.get('avatar_version',0):return
        fields={k:data[k] for k in ('avatar','avatar_version')};self.group_photos[tid]=fields
        for group in (self.social or {}).get('threads',[]):
            if group['id']==tid and group['kind']=='group':group.update(fields)
        self.emit('group_updated',data)
    def open(self):
        if self.window is None:self.window=Window(self)
        if getattr(self,'dock',None) and getattr(self,'ui_mode','window')=='dock':
            self.dock.save_width();self.ui_mode='window';self.window.web.setParent(self.window);self.dock.setWidget(None);self.dock.hide();self.window.layout().addWidget(self.window.web)
        if self.window.isMinimized():self.window.setWindowState(self.window.windowState() & ~Qt.WindowState.WindowMinimized)
        self.timer.setInterval(1000);self.window.show();self.window.web.show();self.window.raise_();self.window.activateWindow()
        if self.social:self.emit('bootstrap',self.social)
        elif self.store.token:self.poll()
    def show_sidebar(self):
        if self.window is None:self.window=Window(self)
        if self.dock is None:
            from .sidebar import Sidebar
            self.dock=Sidebar(self);self.mw.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea,self.dock)
        switching=self.ui_mode!='dock';self.ui_mode='dock';self.window.hide()
        if switching:self.dock.setWidget(self.window.web)
        self.dock.show();self.window.web.show();self.dock.raise_()
        if switching:
            width=max(300,min(int(self.store.data.get('sidebar_width',420)),max(300,self.mw.width()-300)))
            self.mw.resizeDocks([self.dock],[width],Qt.Orientation.Horizontal)
        self.sync_visibility()
        self.window.web.setFocus()
        if self.social:self.emit('bootstrap',self.social)
        elif self.store.token:self.poll()
    def hide_sidebar(self):
        if self.dock:self.dock.save_width();self.dock.hide()
        self.sync_visibility()
        main_web=getattr(self.mw,'web',None)
        if main_web:main_web.setFocus()
    def toggle_sidebar(self):
        if self.dock and self.dock.isVisible() and self.ui_mode=='dock':self.hide_sidebar()
        else:self.show_sidebar()
    def ui_parent(self):
        return self.dock if getattr(self,'ui_mode','window')=='dock' and getattr(self,'dock',None) else self.window
    def sync_visibility(self):
        if not self.closed:self.timer.setInterval(1000 if self.window_visible() else 8000)
    def window_visible(self):
        if getattr(self,'ui_mode','window')=='dock':
            return bool(self.dock and self.dock.isVisible() and not self.mw.isMinimized())
        return bool(self.window and self.window.isVisible() and not self.window.isMinimized())
    def window_focused(self):
        if not self.window_visible():return False
        if getattr(self,'ui_mode','window')!='dock':return self.window.isActiveWindow()
        focus=QApplication.focusWidget();web=self.window.web
        return bool(self.mw.isActiveWindow() and focus and (focus is web or web.isAncestorOf(focus)))
    def muted_threads(self):
        saved=self.store.data.get('muted_by_account',{}).get(self.account_key())
        return list(saved if saved is not None else self.store.data.get('muted',[]))
    def set_thread_muted(self,tid,muted):
        if self.closed or not any(t['id']==tid for t in (self.social or {}).get('threads',[])):return
        current=set(self.muted_threads());current.add(tid) if muted else current.discard(tid)
        self.store.data.setdefault('muted_by_account',{})[self.account_key()]=sorted(current);self.store.save()
        if muted and getattr(self,'notice',None) and self.notice.thread['id']==tid:self.notice.close()
        self.emit('notification_settings',{'muted':sorted(current)})
    def notify_messages(self,tid,messages):
        thread=next((t for t in (self.social or {}).get('threads',[]) if t['id']==tid),None)
        if not thread:return
        if not hasattr(self,'notification_cursor'):self.notification_cursor={}
        last=self.notification_cursor.get(tid,0)
        fresh=[m for m in messages if int(m.get('id',0))>last]
        if not fresh:return
        self.notification_cursor[tid]=max(int(m['id']) for m in fresh)
        me=(self.social or {}).get('user',{}).get('id')
        incoming=[m for m in fresh if m.get('sender') and m['sender']!=me and m.get('kind')!='system']
        if not incoming or tid in self.muted_threads() or (self.active_thread==tid and self.window_focused()):return
        # One compact notice, updated in place, avoids stacked popups during a
        # burst. The body is plain text and no avatar/media is downloaded here.
        from .notifications import Notice
        if getattr(self,'notice',None):self.notice.update_message(thread,incoming[-1])
        else:self.notice=Notice(self,thread,incoming[-1])
        self.notice.show();self.notice.raise_()
    def notification_bootstrap(self,boot,initial=False):
        if not hasattr(self,'notification_cursor'):self.notification_cursor={}
        for thread in boot.get('threads',[]):
            last=int(thread.get('last_id') or 0)
            if initial:self.notification_cursor[thread['id']]=max(self.notification_cursor.get(thread['id'],0),last)
            elif thread.get('last') and thread.get('unread'):
                self.notify_messages(thread['id'],[dict(thread['last'],id=last)])
            else:self.notification_cursor[thread['id']]=max(self.notification_cursor.get(thread['id'],0),last)
    def open_conversation(self,tid):
        if self.closed or not any(t['id']==tid for t in (self.social or {}).get('threads',[])):return
        self.pending_open_thread=tid
        if self.ui_mode=='window' and self.window_visible():self.open()
        else:self.show_sidebar()
        if self.web_ready:self.emit('open_thread',{'id':tid});self.pending_open_thread=None
    def emit(self,event,data=None):
        if self.closed or not self.window:return
        payload=json.dumps([event,data],ensure_ascii=True)
        self.window.web.eval('window.ankiLink && window.ankiLink.receive.apply(null,'+payload+');')
    def run(self,work,done=None,failure=None):
        epoch=self.epoch
        def finish(future):
            if self.closed or epoch!=self.epoch:return
            try:
                value=future.result()
                if done:done(value)
            except Exception as error:
                if failure:failure(str(error))
                else:self.emit('error',str(error))
                return
        # These jobs use HTTP/files, never the Anki collection. The default
        # executor is serialized with native answers and next-card queries.
        self.mw.taskman.run_in_background(work,finish,uses_collection=False)
    def operation_progress(self,request,message):
        if request:self.emit('operation',{'request':request,'phase':'loading','message':message})
    def reset_session_work(self):
        self.pending_actions={};self.refresh_queued=False;self.blob_queue=[];self.blob_active=0;self.preparing=set();self.busy=False
        self.group_avatar_jobs={};self.group_photos={};self.removed_groups={};self.group_versions={};self.thread_files={};self.revoked_files=set();self.revoked_thread_files={};self.file_generations={};self.membership_epoch=0;self.legacy_removals={};self.thread_epochs={};self.reaction_cursor=0
        self.message_invites={}
        self.notification_cursor={};self.pending_open_thread=None
        self.last_presence_sent=float('-inf')
        self.last_presence_payload=None
        self.presence_pending=False
        self.presence_resend=False
        self.presence_snapshot=None
        self.activity_deck_cache=None
        if getattr(self,'notice',None):self.notice.close()
    def operation_finish(self,request,event,data=None,error=None):
        if not request:
            self.emit('error' if error is not None else event,error if error is not None else data);return
        pending=getattr(self,'pending_actions',{})
        if request not in pending:return
        action=pending.pop(request)
        self.emit('operation',{'request':request,'action':action,'phase':'failed' if error is not None else 'done','event':event,'data':data,'message':error})
    def ready(self):
        self.web_ready=True
        self.message_after={};self.history_loaded=set()
        self.emit('setup',{'share_activity':self.activity_enabled(),'url':self.store.data.get('url',''),'signed_in':bool(self.store.token),'dark':theme_manager.night_mode,'remember_available':os.name=='nt','version':'2.0.11','muted':self.muted_threads(),'appearance':self.appearance()})
        if self.social:self.emit('bootstrap',self.social)
        elif self.store.token:self.poll()
        snapshot=getattr(self,'presence_snapshot',None)
        if snapshot:
            people,server_time,received_at=snapshot
            if server_time is not None:server_time+=time.monotonic()-received_at
            self.emit('status',{'people':people,'server_time':server_time})
        if self.pending_open_thread:self.emit('open_thread',{'id':self.pending_open_thread});self.pending_open_thread=None
    def poll(self,thread=None,before=0,force=False):
        if self.closed or not self.store.token:return
        active=thread or (self.active_thread if self.window_visible() else None)
        live=getattr(self,'live',None)
        if (self.social or {}).get('realtime') and not (live and live.online):
            self.publish_presence()
        if active:
            if live and live.online and not before:
                if thread:live.watch(active,self.message_after.get(active,0) if active in self.history_loaded else 0)
            else:self.poll_messages(active,before)
        if self.polling:
            # A mutation may finish after this refresh took its snapshot.
            # Coalesce one follow-up; never discard the forced refresh.
            if force:self.refresh_queued=True
            return
        if not force and self.social and time.monotonic()<getattr(self,'next_bootstrap',0):return
        self.polling=True;client=self.client();request_epoch=getattr(self,'membership_epoch',0);self.emit('refresh_state',{'loading':True})
        def work():
            boot=client.request('/v1/bootstrap');retried=False
            for invitation in boot['invites']:
                saved=self.store.data.get('imports',{}).get(invitation['id'])
                if invitation['recipient']==boot['user']['id'] and invitation['state']=='pending' and saved and saved.get('done'):
                    client.action('invite_state',{'id':invitation['id'],'state':'accepted','result':saved['result']});retried=True
            if retried:boot=client.request('/v1/bootstrap')
            return boot
        def done(result):
            previous={t['id']:t for t in (self.social or {}).get('threads',[]) if t['kind']=='group'}
            visible=[]
            for group in result.get('threads',[]):
                tid=group['id'];removed=getattr(self,'removed_groups',{}).get(tid)
                if removed is not None:
                    legacy=getattr(self,'legacy_removals',{}).get(tid)
                    if legacy is not None:
                        if request_epoch<legacy:continue
                    elif group.get('membership_version',0)<=removed:continue
                    self.removed_groups.pop(tid,None);getattr(self,'legacy_removals',{}).pop(tid,None)
                    # Restore access; per-file generations still reject old downloads.
                    getattr(self,'revoked_files',set()).difference_update(getattr(self,'revoked_thread_files',{}).pop(tid,set()))
                old=previous.get(tid)
                if old and old.get('membership_version',0)>group.get('membership_version',0):
                    group.update({k:old[k] for k in ('owner','members','membership_version') if k in old})
                visible.append(group)
            result['threads']=visible
            for tid in previous:
                if not any(t['id']==tid for t in visible):
                    if request_epoch<getattr(self,'membership_epoch',0):visible.append(previous[tid])
                    else:self.remove_group(tid)
            for group in result.get('threads',[]):
                saved=getattr(self,'group_photos',{}).get(group['id'])
                if saved and group.get('avatar_version',0)<saved['avatar_version']:group.update(saved)
                elif group['kind']=='group':
                    if not hasattr(self,'group_photos'):self.group_photos={}
                    self.group_photos[group['id']]={'avatar':group.get('avatar'),'avatar_version':group.get('avatar_version',0)}
            result['_membership_epoch']=request_epoch;self.membership_epoch=getattr(self,'membership_epoch',0)+1
            initial=self.social is None;self.polling=False;boot=result;boot['chat_themes']=self.chat_themes();self.social=boot;self.remember_invites(boot['invites']);self.ensure_live();self.next_bootstrap=time.monotonic()+(3 if self.window_visible() else 15)
            unread=sum(t['unread'] for t in boot['threads']);requests=sum(p['incoming'] and p['status']=='pending' for p in boot['friends'])
            if self.menu_action:self.menu_action.setText('AnkiLink'+(f' ({unread+requests})' if unread+requests else ''))
            if self.window:self.emit('bootstrap',boot)
            if not (getattr(self,'live',None) and self.live.online) and boot.get('realtime'):
                self.publish_presence()
                status_epoch=self.membership_epoch;reaction_after=getattr(self,'reaction_cursor',0)
                self.run(lambda:client.request('/v1/status?reaction_after='+str(reaction_after)),lambda result:self.live_event('status',result,status_epoch),lambda _:None)
            self.notification_bootstrap(boot,initial=initial)
            self.timer.start()
            if getattr(self,'refresh_queued',False):
                self.refresh_queued=False;self.poll(force=True)
            else:self.emit('refresh_state',{'loading':False})
        def failed(error):
            followup=getattr(self,'refresh_queued',False);self.polling=False;self.refresh_queued=False;self.emit('refresh_state',{'loading':False})
            if 'sign in' in error.lower():self.epoch+=1;self.reset_session_work();self.avatar_job=None;self.uploads.clear();self.timer.stop();self.stop_live();self.store.logout();self.social=None;self.emit('signed_out',None);self.emit('error',error)
            else:
                self.emit('connection_error',error)
                if followup:self.poll(force=True)
        self.run(work,done,failed)
    def poll_messages(self,thread,before=0):
        key=(thread,before);request_epoch=getattr(self,'membership_epoch',0);thread_epoch=getattr(self,'thread_epochs',{}).get(thread,0)
        if key in self.message_polls:return
        self.message_polls.add(key);client=self.client();after=0 if before else getattr(self,'message_after',{}).get(thread,0)
        def done(messages):
            self.message_polls.discard(key)
            if not self.group_accessible(thread) or thread_epoch!=getattr(self,'thread_epochs',{}).get(thread,0):return
            if request_epoch<getattr(self,'membership_epoch',0):
                messages=dict(messages);messages.pop('group_memberships',None)
            self.remember_thread_files(thread,messages.get('messages',[]));self.status_memberships(messages,request_epoch)
            self.remember_invites(messages.get('invites',[]))
            self.message_polls.discard(key)
            if thread==self.active_thread and not before:
                if not hasattr(self,'message_after'):self.message_after={}
                self.message_after[thread]=max([after]+[m['id'] for m in messages.get('messages',[])]);self.history_loaded.add(thread)
            if thread==self.active_thread:self.emit('messages',dict(messages,thread=thread,earlier=bool(before)))
            if after and not before:self.notify_messages(thread,messages.get('messages',[]))
        def failed(error):
            self.message_polls.discard(key);self.emit('connection_error',error)
        self.run(lambda:client.messages(thread,after=after,before=before),done,failed)
    def send_message(self,data):
        if not self.group_accessible(data.get('thread')):return
        live=getattr(self,'live',None)
        if live and live.send('message',data):return
        self.send_message_http(data)
    def send_message_http(self,data):
        # The write reply already confirms the message ID. Do not wait for a
        # bootstrap + messages round trip to display the sender's own message.
        if not self.group_accessible(data.get('thread')):return
        client=self.client();nonce=data['nonce'];thread=data['thread']
        self.run(lambda:client.action('message',data),
                 lambda result:self.live_event('sent',dict(result,nonce=nonce,thread=thread)),
                 lambda error:self.emit('message_failed',{'nonce':nonce,'thread':thread,'message':error}))
    def action(self,name,data,done=None,request=None):
        client=self.client()
        def finished(value):
            if done:done(value)
            self.poll(force=True)
        self.run(lambda:client.action(name,data),finished,lambda error:self.operation_finish(request,'error',error=error))
    def authenticate(self,data):
        url=server_url(data.get('url',''));client=Client(url);payload={k:data.get(k,'') for k in ('username','password','name','join_code')}
        def done(session):
            if getattr(self,'http_client',None):self.http_client.close()
            client.token=session['token'];self.http_key=(url,client.token);self.http_client=client
            self.stop_live();self.epoch+=1;self.reset_session_work();self.avatar_job=None;self.polling=False;self.message_polls.clear();self.message_after={};self.social=None;self.active_thread=None;self.blobs.clear();self.store.login(url,session,data.get('remember') is True);self.history_loaded=set();self.emit('activity_setting',{'enabled':self.activity_enabled()});self.emit('authenticated',session['user']);self.emit('notification_settings',{'muted':self.muted_threads()});self.ensure_live();self.poll();self.timer.start()
        def failed(error):client.close();self.emit('error',error)
        self.run(lambda:client.request('/v1/'+('register' if data.get('register') else 'login'),data=payload),done,failed)
    def send_image(self,data,clipboard=False):
        thread=data.get('thread');kind='sticker' if data.get('sticker') else 'image';nonce=data.get('nonce') or uuid.uuid4().hex
        if clipboard:
            image=QApplication.clipboard().image()
            if image.isNull():raise ValueError('The clipboard does not contain an image.')
            path=str(Path(self.temp.name)/(uuid.uuid4().hex+'.png'));image.save(path,'PNG')
        else:
            path,_=QFileDialog.getOpenFileName(self.ui_parent(),'Choose a sticker' if kind=='sticker' else 'Send an image','','Images (*.png *.jpg *.jpeg *.gif *.webp)')
            if not path:self.emit('cancelled',None);return
        p=Path(path)
        if p.stat().st_size>12*1024*1024 or not QImageReader(str(p)).canRead():raise ValueError('Choose a PNG, JPEG, GIF or WebP image up to 12 MB.')
        owner=(self.store.data['url'],self.social['user']['id'])
        def prepare():
            prepared=media.prepare_sticker(p,self.temp.name) if kind=='sticker' else p
            return prepared.read_bytes(),mimetypes.guess_type(prepared.name)[0] or 'image/png',prepared.name
        def prepared(value):
            if not self.group_accessible(thread):return
            raw,mime,name=value
            self.uploads[nonce]={'thread':thread,'kind':kind,'raw':raw,'mime':mime,'name':name,'owner':owner,'nonce':nonce,'meta':None}
            local={'id':'local-'+nonce,'mime':mime,'name':name}
            self.emit('attachment_pending',{'thread':thread,'kind':kind,'text':'','nonce':nonce,'attachment':local,'src':'data:'+mime+';base64,'+base64.b64encode(raw).decode()})
            self.upload_attachment(nonce)
        self.run(prepare,prepared)
    def upload_attachment(self,nonce):
        item=self.uploads.get(nonce)
        if not item or item.get('sending') or not self.group_accessible(item.get('thread')):return
        item['sending']=True;client=self.client()
        def work():
            meta=item.get('meta')
            if meta is None:
                meta=client.request('/v1/upload',raw=item['raw'],mime=item['mime'],name=item['name']);item['meta']=meta
            return meta
        def uploaded(meta):
            if not self.group_accessible(item.get('thread')) or self.uploads.get(nonce) is not item:return
            item['sending']=False;kind=item['kind'];owner=item['owner'];raw=item['raw']
            if kind=='sticker':
                media.cache_image(media.cache_path(self.store.folder,*owner,meta),raw,meta)
                key='|'.join(owner);saved=self.store.data.setdefault('stickers',{}).setdefault(key,[])
                if not any(s['id']==meta['id'] for s in saved):saved.append(meta);self.store.save()
            self.blobs.add(meta['id']);self.emit('blob',{'id':meta['id'],'src':'data:'+meta['mime']+';base64,'+base64.b64encode(raw).decode()})
            self.send_message({'thread':item['thread'],'kind':kind,'file':meta['id'],'text':'','nonce':nonce})
        def failed(error):
            item['sending']=False;self.emit('message_failed',{'thread':item['thread'],'nonce':nonce,'message':error})
        self.run(work,uploaded,failed)
    def blob(self,meta):
        meta=dict(meta);tid=meta.pop('_thread',None)
        if tid and not self.group_accessible(tid):return
        if tid:self.remember_thread_files(tid,[{'attachment':meta}])
        fid=meta.get('id')
        if fid in getattr(self,'revoked_files',set()):return
        if fid in self.blobs or fid in self.preparing:return
        self.preparing.add(fid)
        if not hasattr(self,'blob_queue'):self.blob_queue=[];self.blob_active=0
        self.blob_queue.append(dict(meta));self.pump_blobs()
    def pump_blobs(self):
        # Do not fill Anki's general executor with workers waiting for two
        # media sockets. Leave room for group/friend actions and message ACKs.
        while not self.closed and self.blob_queue and self.blob_active<2:
            meta=self.blob_queue.pop(0);self.blob_active+=1;self.load_blob(meta)
    def load_blob(self,meta):
        fid=meta['id'];generation=getattr(self,'file_generations',{}).get(fid,0);client=self.client();owner=(self.store.data['url'],self.social['user']['id'])
        cached=media.cache_path(self.store.folder,*owner,meta)
        def work():
            raw=media.cached_image(cached,meta) if cached else None
            if raw is None:
                raw=client.download(meta)
                if cached:media.cache_image(cached,raw,meta)
            return raw
        def done(raw):
            if fid in getattr(self,'revoked_files',set()) or generation!=getattr(self,'file_generations',{}).get(fid,0):
                if cached:cached.unlink(missing_ok=True)
                if generation==getattr(self,'file_generations',{}).get(fid,0):self.preparing.discard(fid)
                self.blob_active-=1;self.pump_blobs();return
            if not meta['mime'].startswith('image/'):raise ValueError('Invalid image attachment.')
            self.preparing.discard(fid);self.blobs.add(fid);self.blob_active-=1
            self.emit('blob',{'id':fid,'src':'data:'+meta['mime']+';base64,'+base64.b64encode(raw).decode()})
            self.pump_blobs()
        def failed(error):
            self.blob_active-=1
            if generation!=getattr(self,'file_generations',{}).get(fid,0):self.pump_blobs();return
            self.preparing.discard(fid)
            self.emit('attachment_error',{'id':fid,'message':error});self.pump_blobs()
        self.run(work,done,failed)
    def send_decks(self,data,request=None):
        if self.busy:raise ValueError('Wait for the current deck transfer to finish.')
        recipients=data.get('recipients',[])
        thread=data.get('thread')
        if thread:
            if not self.social or not self.social.get('features',{}).get('group_deck_shares'):
                raise ValueError('Group deck sharing is unavailable on this server. Update the server and try again.')
            group=next((t for t in self.social.get('threads',[]) if t['id']==thread and t['kind']=='group'),None)
            if not group:raise ValueError('Group conversation not found.')
            if len(group['members'])<2:raise ValueError('Add another member before sharing to this group.')
            target={'thread':thread}
        else:
            if not recipients:raise ValueError('Choose at least one friend.')
            target={'recipients':recipients}
        self.busy=True;epoch=self.epoch;path=Path(self.temp.name)/(uuid.uuid4().hex+'.alink');nonce=data.get('nonce') or uuid.uuid4().hex;client=self.client()
        self.operation_progress(request,'Preparing decks…')
        def prepared(manifest):
            if self.closed or epoch!=self.epoch or thread and not self.group_accessible(thread):self.busy=False;path.unlink(missing_ok=True);return
            def complete(result):
                self.busy=False
                self.store.data.setdefault('last_shared',{})[transfer.digest(sorted(manifest['roots']))]={'keys':[c['key'] for c in manifest['cards']],'notes':{g:n['hash'] for g,n in manifest['notes'].items()}};self.store.save()
                self.operation_finish(request,'shared',result);self.poll(force=True);path.unlink(missing_ok=True)
            def uploaded(meta):
                if thread and not self.group_accessible(thread):self.busy=False;path.unlink(missing_ok=True);return
                self.operation_progress(request,'Sending invitations…')
                self.run(lambda:client.action('invite',{**target,'file':meta['id'],'summary':manifest['summary'],'nonce':nonce}),complete,failed)
            self.operation_progress(request,'Uploading decks…');self.run(lambda:client.upload(path,'application/zip'),uploaded,failed)
        def failed(error):
            if self.closed or epoch!=self.epoch:return
            self.busy=False;self.operation_finish(request,'error',error=str(error))
        QueryOp(parent=self.mw,op=lambda col:transfer.make_bundle(col,self.store,data.get('decks',[]),path,data.get('settings') is True,data.get('progress') is True,str(data.get('search',''))),success=prepared).failure(lambda error:failed(str(error))).run_in_background()
    def remember_invites(self,rows):
        if not getattr(self,'social',None):return
        uid=self.social['user']['id'];cache=getattr(self,'message_invites',{});self.message_invites=cache
        for row in rows:
            if row.get('thread') and not self.group_accessible(row['thread']):continue
            if row.get('thread'):self.remember_thread_files(row['thread'],[row])
            if isinstance(row,dict) and isinstance(row.get('id'),str) and uid in (row.get('sender'),row.get('recipient')):
                old=cache.get(row['id'])
                if not (old and old.get('state')!='pending' and row.get('state')=='pending'):cache[row['id']]=row
        for key in sorted(cache,key=lambda key:cache[key].get('created',0))[:max(0,len(cache)-1000)]:cache.pop(key,None)
    def invite(self,iid):
        if not self.social:raise ValueError('Connect to the server first.')
        item=next((x for x in self.social['invites'] if x['id']==iid and x['recipient']==self.social['user']['id']),None)
        if item is None:item=getattr(self,'message_invites',{}).get(iid)
        if item and item.get('recipient')!=self.social['user']['id']:item=None
        if not item or not self.group_accessible(item.get('thread')):raise ValueError('Invitation not found.')
        return item
    def preview_invite(self,iid,request=None):
        item=self.invite(iid);client=self.client();epoch=self.epoch;path=Path(self.temp.name)/(iid+'.alink')
        tid=item.get('thread');thread_epoch=getattr(self,'thread_epochs',{}).get(tid,0)
        def valid():
            allowed=not self.closed and epoch==self.epoch and self.group_accessible(tid) and thread_epoch==getattr(self,'thread_epochs',{}).get(tid,0)
            if not allowed:
                path.unlink(missing_ok=True)
                if request:getattr(self,'pending_actions',{}).pop(request,None)
            return allowed
        self.operation_progress(request,'Downloading shared decks…')
        def failed(error):
            if valid():self.operation_finish(request,'error',error=str(error))
        def downloaded(raw):
            if not valid():return
            path.write_bytes(raw)
            self.operation_progress(request,'Checking shared cards…')
            def done(report):
                if not valid():return
                self.previews[iid]=str(path);self.operation_finish(request,'invite_preview',dict(report,invitation=item))
            QueryOp(parent=self.mw,op=lambda col:transfer.preview(col,self.store,path),success=done).failure(failed).run_in_background()
        self.run(lambda:client.download(item['attachment']),downloaded,failed)
    def accept(self,data,request=None):
        iid=data['id'];item=self.invite(iid)
        if self.busy:raise ValueError('A deck transfer is already in progress.')
        if self.mw.state=='review':raise ValueError('Return to Anki’s deck list before accepting a deck.')
        if iid not in self.previews:raise ValueError('Open the invitation preview first.')
        self.busy=True;epoch=self.epoch;path=self.previews[iid];client=self.client();options=data.get('options',{})
        self.operation_progress(request,'Importing cards…')
        def work(col):
            from anki.collection import OpChanges
            result=transfer.apply_bundle(col,self.store,path,options,iid)
            names=('card','note','deck','tag','notetype','config','deck_config','mtime','browser_table','browser_sidebar','note_text','study_queues')
            available={f.name for f in OpChanges.DESCRIPTOR.fields};changes=OpChanges(**{k:True for k in names if k in available})
            return types.SimpleNamespace(changes=changes,result=result)
        def done(result):
            if self.closed or epoch!=self.epoch:return
            self.busy=False;self.mw.reset();self.operation_finish(request,'imported',result.result)
            self.run(lambda:client.action('invite_state',{'id':iid,'state':'accepted','result':result.result}),lambda _:self.poll(force=True),lambda e:self.emit('receipt_pending',e))
        def failed(error):
            if self.closed or epoch!=self.epoch:return
            self.busy=False;self.operation_finish(request,'error',error=str(error))
        CollectionOp(parent=self.mw,op=work).success(done).failure(failed).run_in_background()
    def message(self,handled,message,context):
        if self.closed or handled[0] or not message.startswith('anki_link:') or not self.window or context is not self.window:return handled
        request=None
        try:
            if len(message)>250000:raise ValueError('Request too large.')
            data=json.loads(message[10:]);action=data.pop('action',None);identifier=data.pop('_request',None)
            if identifier is not None:
                if not isinstance(identifier,str) or not 1<=len(identifier)<=80:raise ValueError('Invalid request identifier.')
                if action not in ('friend_request','friend_decide','group','direct','catalog','share','preview_invite','accept_invite','reject_invite','reaction','group_add','group_remove','group_admin','group_leave'):raise ValueError('Invalid tracked action.')
                request=identifier
            if request:
                if not hasattr(self,'pending_actions'):self.pending_actions={}
                if request in self.pending_actions:return True,None
                self.pending_actions[request]=action
            if action=='ready':self.ready()
            elif action=='auth':self.authenticate(data)
            elif action=='logout':
                client=self.client();self.stop_live();self.epoch+=1;self.reset_session_work();self.polling=False;self.message_polls.clear();self.message_after={};self.timer.stop();self.run(lambda:client.request('/v1/logout',data={}),lambda _:None,lambda _:None);self.store.logout();self.social=None;self.active_thread=None;self.uploads.clear();self.avatar_job=None;self.emit('signed_out',None)
            elif not self.store.token:raise ValueError('Sign in first.')
            elif action=='refresh':self.poll(force=True)
            elif action=='thread':
                self.active_thread=data['id']
                if self.active_thread:self.poll(thread=data['id'],before=int(data.get('before',0)))
            elif action in ('friend_request','friend_decide','group','direct'):
                self.action(action,data,lambda r:self.operation_finish(request,'social_result',r) if request else self.emit('thread_created',r) if r.get('thread') else self.emit('notice','Done'),request=request)
            elif action=='reaction':
                if not self.group_accessible(data.get('thread')):raise ValueError('Group access has ended.')
                self.action(action,data,lambda result:self.operation_finish(request,'reaction_updated',result),request=request)
            elif action in ('group_add','group_remove','group_admin','group_leave'):
                if not self.group_accessible(data.get('thread')):raise ValueError('Group access has ended.')
                def group_done(result):
                    self.membership_changed(result);self.operation_finish(request,'group_result',result)
                self.action(action,data,group_done,request=request)
            elif action=='message':self.send_message(data)
            elif action in ('read','delivered','typing'):
                if action!='read' or self.window_focused():self.social_action(action,data)
            elif action=='mute_thread':self.set_thread_muted(data['id'],data.get('muted') is True)
            elif action=='activity':
                key=self.account_key();self.store.data.setdefault('activity',{})[key]=data.get('enabled') is True;self.store.save();self.publish_presence(force=True);self.emit('activity_setting',{'enabled':self.activity_enabled()})
            elif action=='avatar':self.set_avatar(data)
            elif action=='appearance':self.set_appearance(data.get('theme'))
            elif action=='chat_theme':self.set_chat_theme(data.get('thread'),data.get('color'))
            elif action=='group_photo':self.set_group_avatar(data)
            elif action=='retry_group_photo':self.retry_group_avatar(data.get('thread'),data.get('request'))
            elif action=='retry_avatar':self.retry_avatar(data.get('request'))
            elif action=='retry_attachment':self.upload_attachment(data['nonce'])
            elif action=='attach':self.send_image(data)
            elif action=='paste_image':self.send_image(data,True)
            elif action=='blob':self.blob(data)
            elif action=='stickers':
                key=self.store.data['url']+'|'+self.social['user']['id'];self.emit('sticker_library',self.store.data.get('stickers',{}).get(key,[]))
            elif action=='catalog':
                epoch=self.epoch
                def catalog_done(rows):
                    if not self.closed and self.epoch==epoch:self.operation_finish(request,'catalog',rows)
                def catalog_failed(error):
                    if not self.closed and self.epoch==epoch:self.operation_finish(request,'error',error=str(error))
                QueryOp(parent=self.mw,op=lambda col:transfer.catalog(col),success=catalog_done).failure(catalog_failed).run_in_background()
            elif action=='share':self.send_decks(data,request)
            elif action=='preview_invite':self.preview_invite(data['id'],request)
            elif action=='accept_invite':self.accept(data,request)
            elif action=='reject_invite':self.action('invite_state',{'id':data['id'],'state':'rejected'},lambda _:self.operation_finish(request,'notice','Deck invitation declined.'),request=request)
            else:raise ValueError('Unknown AnkiLink action.')
        except Exception as error:self.operation_finish(request,'error',error=str(error))
        return True,None
    def close(self):
        self.closed=True;self.stop_live();self.epoch+=1;self.timer.stop()
        if getattr(self,'http_client',None):self.http_client.close()
        if self.window:self.window.web.cleanup();self.window.deleteLater();self.window=None
        if getattr(self,'notice',None):self.notice.close()
        if getattr(self,'dock',None):self.dock.save_timer.stop();self.mw.removeDockWidget(self.dock);self.dock.deleteLater();self.dock=None
        if self.tray:self.tray.hide();self.tray.deleteLater()
        self.temp.cleanup()
