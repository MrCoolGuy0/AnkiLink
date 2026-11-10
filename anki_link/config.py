"""Profile-local identity and transfer receipts. Windows tokens use DPAPI."""
from __future__ import annotations
import base64
import ctypes
import json
import os
from pathlib import Path
import secrets
import threading

def protect(value,decode=False):
    if os.name!='nt':raise ValueError('Saved sign-in is available on Windows only.')
    from ctypes import wintypes
    class Blob(ctypes.Structure):_fields_=[('size',wintypes.DWORD),('data',ctypes.POINTER(ctypes.c_ubyte))]
    raw=base64.b64decode(value) if decode else value.encode();buffer=ctypes.create_string_buffer(raw);source=Blob(len(raw),ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ubyte)));target=Blob()
    function=ctypes.windll.crypt32.CryptUnprotectData if decode else ctypes.windll.crypt32.CryptProtectData
    args=(ctypes.byref(source),None,None,None,None,0,ctypes.byref(target))
    if not function(*args):raise OSError('Windows could not save this sign-in.')
    try:result=ctypes.string_at(target.data,target.size);return result.decode() if decode else base64.b64encode(result).decode()
    finally:ctypes.windll.kernel32.LocalFree(target.data)

DEFAULT_SERVER='https://ankilink-jm.jdgarcia2697lag.chatgpt.site'
LEGACY_HOSTED_SERVERS=('https://anki-link-evans.earthybox12.chatgpt.site',
                       'https://anki-link-evans.begrgbrgbrt.chatgpt.site')

def migrate_hosted_address(data):
    """Move official URLs to the restored service, retaining account-local state."""
    original=data.get('url','')
    if not isinstance(original,str) or original.strip().rstrip('/') not in LEGACY_HOSTED_SERVERS:return False
    for field in ('muted_by_account','activity','stickers','chat_themes_by_account'):
        saved=data.get(field)
        if not isinstance(saved,dict):continue
        # Earlier official migrations retained alias keys; the active host owns
        # the latest preferences when multiple aliases exist for one account.
        items=sorted(saved.items(),key=lambda item:not(isinstance(item[0],str) and item[0].split('|',1)[0].strip().rstrip('/')==original.strip().rstrip('/')))
        for key,value in items:
            if not isinstance(key,str) or '|' not in key:continue
            url,user=key.split('|',1)
            if url.strip().rstrip('/') in LEGACY_HOSTED_SERVERS:
                saved.setdefault(DEFAULT_SERVER+'|'+user,value)
    data['url']=DEFAULT_SERVER
    return True

class Store:
    def __init__(self,profile):
        self.folder=Path(profile)/'anki_link';self.folder.mkdir(exist_ok=True);self.path=self.folder/'settings.json';self.lock=threading.RLock();self.token=''
        self.data={'url':DEFAULT_SERVER,'identity':secrets.token_hex(16),'imports':{},'lineage':{},'last_shared':{},'muted':[]}
        if self.path.exists():
            try:self.data.update(json.loads(self.path.read_text(encoding='utf-8')))
            except Exception:raise ValueError('AnkiLink settings could not be read. The existing file has been preserved.')
        if not self.data.get('url'):self.data['url']=DEFAULT_SERVER
        if migrate_hosted_address(self.data):self.save()
        if self.data.get('saved_token'):
            try:self.token=protect(self.data['saved_token'],True)
            except Exception:self.data.pop('saved_token',None)
    def save(self):
        with self.lock:
            p=self.path.with_suffix('.tmp');p.write_text(json.dumps(self.data,ensure_ascii=False,indent=2),encoding='utf-8');os.chmod(p,0o600);os.replace(p,self.path)
    def login(self,url,session,remember=False):
        with self.lock:
            self.token=session['token'];self.data.update(url=url,user=session['user']);self.data.pop('saved_token',None)
            if remember and os.name=='nt':self.data['saved_token']=protect(self.token)
            self.save()
    def logout(self):
        self.token='';self.data.pop('saved_token',None);self.data.pop('user',None);self.save()
