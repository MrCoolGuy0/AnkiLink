"""Bounded HTTP client; tokens stay in Python, never in the WebView or URLs."""
from __future__ import annotations
import hashlib
import json
from http.cookiejar import DefaultCookiePolicy
from pathlib import Path
from urllib.parse import urlencode,urlsplit

class NetworkError(Exception):pass

def server_url(value):
    value=str(value).strip().rstrip('/');u=urlsplit(value)
    if u.username or u.password or u.query or u.fragment or u.path not in ('','/') or not u.hostname:raise ValueError('Enter the server address, such as https://link.example.com.')
    local=u.hostname in ('localhost','127.0.0.1','::1')
    if u.scheme!='https' and not (u.scheme=='http' and local):raise ValueError('Use HTTPS. HTTP is allowed only for a server on this computer.')
    return value

class Client:
    def __init__(self,url,token=''):
        # requests is bundled with supported Anki releases. Keep this pool for
        # the signed-in account instead of repeating TLS for every API call.
        import requests
        self.url=server_url(url);self.token=token
        class BearerOnly(requests.auth.AuthBase):
            def __call__(self,request):return request
        def pool(size):
            session=requests.Session();session.headers.clear()
            session.auth=BearerOnly()  # Never substitute machine .netrc credentials.
            session.cookies.set_policy(DefaultCookiePolicy(allowed_domains=()))
            adapter=requests.adapters.HTTPAdapter(pool_connections=4,pool_maxsize=size,pool_block=True,max_retries=0)
            session.mount('https://',adapter);session.mount('http://',adapter);return session
        # Brief chat/API requests share a warm connection rather than opening
        # another TLS connection when a poll is momentarily in flight. Large
        # files have their own pool, so a deck upload cannot occupy this lane.
        self.session=pool(1);self.bulk_session=pool(2);self.background_session=pool(2)
    def close(self):self.session.close();self.bulk_session.close();self.background_session.close()
    def request(self,path,data=None,raw=None,mime=None,name=None,limit=300*1024*1024,bulk=False,background=False):
        if not path.startswith('/v1/') and path!='/health':raise ValueError('Invalid API path.')
        headers={'Accept':'application/json','User-Agent':'AnkiLink/1.4.0'}
        if self.token:headers['Authorization']='Bearer '+self.token
        if data is not None:raw=json.dumps(data,ensure_ascii=False).encode();headers['Content-Type']='application/json'
        if mime:headers['Content-Type']=mime
        if name:headers['X-File-Name']=''.join(c for c in Path(name).name if 32<=ord(c)<127)[:160] or 'attachment'
        import requests
        from urllib3.exceptions import HTTPError as StreamError
        try:
            # Small pictures/stickers also belong in the media lane. A warm
            # chat socket must not wait behind an avatar or attachment.
            pool=self.bulk_session if bulk or path=='/v1/upload' or path.startswith('/v1/files/') or (raw is not None and len(raw)>512*1024) else self.session
            if background or (raw is None and path.startswith(('/v1/bootstrap','/v1/messages','/v1/status'))):pool=self.background_session
            with pool.request('POST' if raw is not None else 'GET',self.url+path,data=raw,headers=headers,stream=True,timeout=(15,60),allow_redirects=False) as response:
                if 300<=response.status_code<400:raise NetworkError('The server redirected this request. Use its final HTTPS address.')
                if response.status_code>=400:
                    try:message=json.loads(response.raw.read(5000,decode_content=True)).get('error','Server request failed.')
                    except Exception:message='Server request failed ('+str(response.status_code)+').'
                    raise NetworkError(message)
                length=int(response.headers.get('Content-Length','0'))
                if length>limit:raise NetworkError('The download is too large.')
                content=response.raw.read(limit+1,decode_content=True)
                if len(content)>limit:raise NetworkError('The download is too large.')
                return json.loads(content) if response.headers.get('Content-Type','').startswith('application/json') else content
        except (requests.RequestException,StreamError,TimeoutError,OSError) as error:raise NetworkError('Could not reach the sharing server. Check the connection and try again.') from error
    def action(self,action,data):return self.request('/v1/actions/'+action,data=data)
    def upload(self,path,mime):
        p=Path(path);return self.request('/v1/upload',raw=p.read_bytes(),mime=mime,name=p.name)
    def download(self,meta):
        content=self.request('/v1/files/'+meta['id'],bulk=meta.get('size',0)>512*1024)
        if not isinstance(content,bytes) or hashlib.sha256(content).hexdigest()!=meta['sha256']:raise NetworkError('The attachment did not pass its download check. Try again.')
        return content
    def messages(self,thread,after=0,before=0):return self.request('/v1/messages?'+urlencode({'thread':thread,'after':after,'before':before}))
