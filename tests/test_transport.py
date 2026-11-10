"""Real persistent HTTP sockets, account scoping and bulk/chat isolation."""
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import threading
import unittest
from unittest.mock import patch
from test_relay import N
import test_message_controller as controller
D=controller.D

class Handler(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def setup(self):super().setup();self.server.connections+=1;self.connection.settimeout(3)
    def log_message(self,*args):pass
    def do_GET(self):self.route()
    def do_POST(self):self.route()
    def route(self):
        self.rfile.read(int(self.headers.get('Content-Length',0)))
        self.server.calls.append((self.path,self.headers.get('Authorization'),self.headers.get('Cookie')))
        if self.path=='/v1/upload':self.server.started.set();self.server.release.wait(3)
        body=json.dumps({'ok':True}).encode();self.send_response(302 if self.path=='/v1/redirect' else 200)
        if self.path=='/v1/redirect':self.send_header('Location','/v1/secret')
        self.send_header('Set-Cookie','ignore=me');self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)

class Transport(unittest.TestCase):
    def setUp(self):
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);self.server.daemon_threads=True;self.server.connections=0;self.server.calls=[]
        self.server.started=threading.Event();self.server.release=threading.Event()
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.client=N.Client('http://127.0.0.1:'+str(self.server.server_port),'token-a')
    def tearDown(self):self.server.release.set();self.client.close();self.server.shutdown();self.server.server_close();self.thread.join(2)
    def test_small_request_pools_reuse_connections_and_preserve_account_auth(self):
        with patch('requests.sessions.get_netrc_auth',return_value=('wrong-user','do-not-send')):
            self.client.request('/health')
        with ThreadPoolExecutor(max_workers=3) as workers:
            results=list(workers.map(lambda _:self.client.request('/v1/bootstrap'),range(6)))
        self.assertTrue(all(r['ok'] for r in results));self.assertLessEqual(self.server.connections,3)
        self.assertTrue(all(token=='Bearer token-a' and cookie is None for _,token,cookie in self.server.calls))
    def test_profile_upload_and_save_reuse_an_already_warm_background_connection(self):
        self.client.request('/v1/bootstrap');self.server.release.set()
        self.client.request('/v1/upload',raw=b'small avatar',mime='image/png',name='avatar.png',background=True)
        self.client.request('/v1/actions/profile',data={'avatar':'test'},background=True)
        self.assertEqual(self.server.connections,1)
    def test_redirect_is_not_followed_with_authentication(self):
        with self.assertRaisesRegex(N.NetworkError,'redirected'):self.client.request('/v1/redirect')
        self.assertEqual([c[0] for c in self.server.calls],['/v1/redirect'])
    def test_large_upload_cannot_occupy_warm_chat_connection(self):
        self.client.request('/health')
        with ThreadPoolExecutor(max_workers=1) as worker:
            upload=worker.submit(lambda:self.client.request('/v1/upload',raw=b'x'*(513*1024)))
            try:
                self.assertTrue(self.server.started.wait(2));self.assertTrue(self.client.request('/v1/actions/message',data={'text':'hello'})['ok'])
                self.assertFalse(upload.done());self.assertEqual(self.server.connections,2)
            finally:self.server.release.set()
            self.assertTrue(upload.result(timeout=2)['ok'])
    def test_even_tiny_upload_cannot_occupy_group_or_friend_connection(self):
        self.client.request('/health')
        with ThreadPoolExecutor(max_workers=1) as worker:
            upload=worker.submit(lambda:self.client.request('/v1/upload',raw=b'tiny image',mime='image/png'))
            try:
                self.assertTrue(self.server.started.wait(1))
                self.assertTrue(self.client.action('group',{'title':'Test','users':[]})['ok'])
                self.assertFalse(upload.done());self.assertEqual(self.server.connections,2)
            finally:self.server.release.set()
            self.assertTrue(upload.result(timeout=1)['ok'])
    def test_small_attachment_download_uses_media_pool(self):
        raw=b'picture';meta={'id':'small','size':len(raw),'sha256':__import__('hashlib').sha256(raw).hexdigest()}
        class Response:
            status_code=200;headers={'Content-Type':'image/png'}
            def __enter__(self):return self
            def __exit__(self,*args):pass
            raw=type('Raw',(),{'read':lambda _,*a,**kw:raw})()
        with patch.object(self.client.session,'request',side_effect=AssertionError('media held the action lane')),patch.object(self.client.bulk_session,'request',return_value=Response()) as bulk:
            self.assertEqual(self.client.download(meta),raw);self.assertEqual(bulk.call_count,1)

class ClientLifetime(unittest.TestCase):
    def test_controller_reuses_pool_and_replaces_it_on_account_or_server_change(self):
        c=D.Controller.__new__(D.Controller);c.store=type('Store',(),{'token':'a','data':{'url':'https://one.test'}})();made=[]
        class Client:
            def __init__(self,*args):self.args=args;self.closed=False;made.append(self)
            def close(self):self.closed=True
        with patch.object(D,'Client',Client):
            a=c.client();self.assertIs(c.client(),a)
            c.store.token='b';b=c.client();self.assertTrue(a.closed);self.assertIsNot(a,b)
            c.store.data['url']='https://two.test';self.assertIsNot(c.client(),b);self.assertTrue(b.closed)
        self.assertEqual(len(made),3)

class IncrementalPolling(unittest.TestCase):
    setUp=controller.MessageController.setUp
    finish=controller.MessageController.finish
    def test_only_fetch_new_messages_after_initial_history_and_keep_older_paging(self):
        requests=[]
        self.c.client().messages=lambda thread,after=0,before=0:(requests.append((after,before)) or {'messages':[{'id':7}]})
        self.c.poll_messages('chat');self.finish(0)
        self.c.poll_messages('chat');self.finish(1)
        self.c.poll_messages('chat',before=4);self.finish(2)
        self.assertEqual(requests,[(0,0),(7,0),(0,4)]);self.assertEqual(self.c.message_after['chat'],7)
    def test_discarded_inactive_thread_reply_does_not_skip_unshown_history(self):
        self.c.poll_messages('chat');self.c.active_thread='other';self.finish(0)
        self.assertNotIn('chat',getattr(self.c,'message_after',{}))

if __name__=='__main__':unittest.main()
