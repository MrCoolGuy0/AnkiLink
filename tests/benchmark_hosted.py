"""Opt-in live timing with two isolated QA accounts; JSON config on stdin.

Requires private requests/PyQt6 runtimes. Creates synthetic accounts/messages,
never reads an existing user's chat. No credentials are printed or persisted.
Not part of automatic unit-test discovery.
"""
import importlib
import json
from pathlib import Path
import secrets
import sys
import tempfile
import time
import types
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
pkg=types.ModuleType('anki_link');pkg.__path__=[str(ROOT/'anki_link')];sys.modules.setdefault('anki_link',pkg)
N=importlib.import_module('anki_link.net');M=importlib.import_module('anki_link.media')

def main():
    from PyQt6.QtGui import QImage,QImageReader
    from PyQt6.QtCore import Qt
    config=json.load(sys.stdin);clients=[N.Client(config['url']) for _ in range(2)]
    users=[];suffix=secrets.token_hex(5)
    try:
        health=clients[0].request('/health');assert health['version']==config['expected_version']
        for i,c in enumerate(clients):
            session=c.request('/v1/register',data={'username':'qa_speed_'+suffix+'_'+str(i),'name':'AnkiLink speed QA','password':secrets.token_urlsafe(24),'join_code':config['join_code']})
            c.token=session['token'];users.append(session['user']);assert session['server_version']==health['version']
        a,b=clients;a.action('friend_request',{'code':users[1]['code']});b.action('friend_decide',{'user':users[0]['id'],'accept':True})
        tid=a.action('direct',{'user':users[1]['id']})['thread'];last=0
        for kind in ('text','sticker','text'):
            start=time.perf_counter();nonce=secrets.token_hex(12)
            ack=a.action('message',{'thread':tid,'kind':kind,'text':'cheer' if kind=='sticker' else 'Synthetic timing check','nonce':nonce});acked=time.perf_counter()
            messages=b.messages(tid,after=last)['messages'];assert any(m['nonce']==nonce for m in messages);last=ack['id']
            print(json.dumps({'kind':kind,'server_ack_ms':round((acked-start)*1000),'ack_plus_recipient_fetch_ms':round((time.perf_counter()-start)*1000)}),flush=True)
        qt=types.ModuleType('aqt.qt');qt.QImageReader=QImageReader;qt.Qt=Qt
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'synthetic.png';image=QImage(1600,1000,QImage.Format.Format_ARGB32);image.fill(0x80AA33BB);image.save(str(source))
            with patch.dict(sys.modules,{'aqt.qt':qt}):path=M.prepare_sticker(source,td)
            raw=path.read_bytes();start=time.perf_counter()
            meta=a.request('/v1/upload',raw=raw,mime='image/webp' if path.suffix=='.webp' else 'image/png',name='synthetic-sticker'+path.suffix);uploaded=time.perf_counter();nonce=secrets.token_hex(12)
            a.action('message',{'thread':tid,'kind':'sticker','file':meta['id'],'text':'','nonce':nonce});acked=time.perf_counter()
            got=b.messages(tid,after=last)['messages'];attachment=next(m['attachment'] for m in got if m['nonce']==nonce);assert b.download(attachment)==raw
            print(json.dumps({'kind':'uploaded_sticker','bytes':len(raw),'upload_ms':round((uploaded-start)*1000),'upload_plus_send_ms':round((acked-start)*1000),'upload_send_fetch_download_ms':round((time.perf_counter()-start)*1000)}),flush=True)
    finally:
        for c in clients:
            try:
                if c.token:c.request('/v1/logout',data={})
            finally:c.close()

if __name__=='__main__':main()
