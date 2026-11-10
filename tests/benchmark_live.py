"""Opt-in synthetic live smoke test. Config is read from stdin, never saved."""
import importlib.util
import json
import os
from pathlib import Path
import secrets
import sys
import time
import types
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PyQt6.QtCore import QObject,QCoreApplication
from PyQt6.QtWidgets import QApplication
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'anki_link'))
from net import Client
from test_message_controller import D
spec=importlib.util.spec_from_file_location('bench_live',ROOT/'anki_link/live.py');L=importlib.util.module_from_spec(spec);spec.loader.exec_module(L)
config=json.load(sys.stdin);app=QApplication([]);clients=[];owners=[];timings=[]
def until(predicate,limit=20):
    end=time.monotonic()+limit
    while not predicate() and time.monotonic()<end:QCoreApplication.processEvents();time.sleep(.003)
    if not predicate():raise RuntimeError('The synthetic live check timed out')
def owner(session):
    obj=types.SimpleNamespace(mw=QObject(),window_visible=lambda:True,closed=False,store=types.SimpleNamespace(token=session['token'],data={'url':config['url']}),events=[],fallback=[])
    obj.activity_payload=lambda idle=False:{'status':'online','share':False,'deck':''}
    obj.publish_presence=types.MethodType(D.Controller.publish_presence,obj)
    obj.live_ready=lambda:None;obj.live_event=lambda event,data:obj.events.append((event,data,time.monotonic()));obj.send_message_http=lambda data:obj.fallback.append(data)
    obj.live=L.Live(obj);owners.append(obj);return obj
try:
    sessions=[]
    for _ in range(2):
        client=Client(config['url']);clients.append(client)
        session=client.request('/v1/register',data={'username':'qa_live_'+secrets.token_hex(5),'name':'Synthetic live check','password':secrets.token_urlsafe(24),'join_code':config['join_code']});client.token=session['token'];sessions.append(session)
    clients[0].action('friend_request',{'code':sessions[1]['user']['code']});tid=clients[1].action('friend_decide',{'user':sessions[0]['user']['id'],'accept':True})['thread']
    a,b=[owner(s) for s in sessions];until(lambda:a.live.online and b.live.online)
    for i in range(3):
        nonce='live-'+secrets.token_hex(6);start=time.monotonic();a.live.send('message',{'thread':tid,'kind':'text','text':'Synthetic live connection check '+str(i),'nonce':nonce})
        until(lambda:any(e=='sent' and d.get('nonce')==nonce for e,d,_ in a.events) and any(e=='messages' and any(m.get('nonce')==nonce for m in d['messages']) for e,d,_ in b.events))
        ack=next((d,t) for e,d,t in a.events if e=='sent' and d.get('nonce')==nonce);delivery=next(t for e,d,t in b.events if e=='messages' and any(m.get('nonce')==nonce for m in d['messages']))
        b.live.send('delivered',{'thread':tid,'last':ack[0]['id']});until(lambda:any(e in ('status','receipts') and any(r['uid']==sessions[1]['user']['id'] and r['delivered']>=ack[0]['id'] for r in d.get('receipts',[])) for e,d,_ in a.events))
        timings.append({'ack_ms':round((ack[1]-start)*1000),'receiver_ms':round((delivery-start)*1000)})
    a.live.send('typing',{'thread':tid,'typing':True});until(lambda:any(e in ('typing','status') and (d.get('uid')==sessions[0]['user']['id'] if e=='typing' else any(r['uid']==sessions[0]['user']['id'] for r in d.get('typing',[]))) for e,d,_ in b.events))
    print(json.dumps({'service_version':sessions[0]['server_version'],'live_connected':True,'samples':timings,'http_fallbacks':sum(len(o.fallback) for o in owners),'typing_and_delivery':'passed'}))
finally:
    for obj in owners:obj.live.close()
    QCoreApplication.processEvents()
    for client in clients:
        try:
            if client.token:client.request('/v1/logout',data={})
        except Exception:pass
        client.close()
