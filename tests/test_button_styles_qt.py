"""Actual AnkiWebView UI color/interaction regression; invoked by
test_native_webview.py --buttons. Synthetic social data, no remote requests.
--buttons-before demonstrates the old native-CSS white hover on Sign in.
"""
from pathlib import Path
import json
from zipfile import ZipFile


def check_buttons(js,view,wait,root,before=False):
    from PyQt6.QtCore import QPoint,Qt
    from PyQt6.QtTest import QTest
    def run(code):return js(code)
    def click(s):run('document.querySelector('+json.dumps(s)+').click()');wait(15)
    def emit(event,data=None):run('ankiLink.receive('+json.dumps(event)+','+json.dumps(data)+')');wait(15)
    def move(s):
        run('document.querySelector('+json.dumps(s)+').scrollIntoView({block:"center",inline:"nearest"})');wait(15)
        p=run('(()=>{const b=document.querySelector('+json.dumps(s)+').getBoundingClientRect();return [b.x+b.width/2,b.y+b.height/2]})()')
        QTest.mouseMove(view.focusProxy() or view,QPoint(round(p[0]),round(p[1])));wait(150)
        return QPoint(round(p[0]),round(p[1]))
    def stats(s):
        return run(r'''(()=>{const b=document.querySelector(SELECTOR),s=getComputedStyle(b),r=b.getBoundingClientRect();
          function rgba(c){return c.match(/[\d.]+/g).map(Number)}
          function over(a,b){const t=a[3]??1;return a.slice(0,3).map((v,i)=>v*t+b[i]*(1-t)).concat([1])}
          let bg=[255,255,255,1],chain=[];for(let n=b;n;n=n.parentElement)chain.unshift(n);
          for(const n of chain)bg=over(rgba(getComputedStyle(n).backgroundColor),bg);
          const fg=over(rgba(s.color),bg),lum=a=>a.slice(0,3).map(v=>v/255).map(v=>v<=.04045?v/12.92:Math.pow((v+.055)/1.055,2.4)).reduce((x,v,i)=>x+v*[.2126,.7152,.0722][i],0);
          const x=lum(fg),y=lum(bg);
          return {bg:s.backgroundColor,image:s.backgroundImage,fg:s.color,shadow:s.boxShadow,rect:[r.x,r.y,r.width,r.height],transform:s.transform,contrast:(Math.max(x,y)+.05)/(Math.min(x,y)+.05),hover:b.matches(':hover'),focus:b.matches(':focus-visible'),outline:s.outlineStyle,outlineWidth:s.outlineWidth,opacity:s.opacity,pressed:b.matches(':active')};})()'''.replace('SELECTOR',json.dumps(s)))
    if before:
        with ZipFile(root/'dist/AnkiLink-v1.0.2.ankiaddon') as z:old=z.read('web/app.css').decode()
        run('''document.querySelectorAll('link[rel=stylesheet]').forEach(n=>n.disabled=true);
          const native=document.createElement('link');native.rel='stylesheet';native.href=new URL('_anki/css/webview.css',document.baseURI);native.onload=()=>window.nativeStylesReady=true;document.head.appendChild(native);
          const own=document.createElement('style');own.textContent='''+json.dumps(old)+''';document.head.appendChild(own);''')
        for _ in range(40):
            if run('window.nativeStylesReady===true'):break
            wait(25)
        assert run('window.nativeStylesReady===true'),'Native Anki CSS must be present to reproduce'
        s='#auth-form button[type=submit]';move(s);old=stats(s)
        assert old['hover'] and ('rgb(255, 255, 255)' in old['image'] or old['bg']=='rgb(255, 255, 255)') and old['fg']=='rgb(255, 255, 255)',old
        print(json.dumps({'old_native_hover':'white reproduced','button':'Sign in','contrast':old['contrast']}),flush=True)
        return
    # Ordinary global theme CSS arriving later must not override the scoped UI.
    run('const hostile=document.createElement("style");hostile.textContent="button:hover,button:active,button:focus{background:linear-gradient(white,white)!important;color:white!important;box-shadow:0 0 8px white!important}";document.head.appendChild(hostile)')
    checks=[]
    def check(s,label,disabled=False):
        assert run('!!document.querySelector('+json.dumps(s)+')'),label
        # Settle any scroll needed to reach a picker item before measuring it.
        run('document.querySelector('+json.dumps(s)+').scrollIntoView({block:"center",inline:"nearest"})');wait(25)
        QTest.mouseMove(view.focusProxy() or view,QPoint(1,1));wait(135)
        base=stats(s);point=move(s);hover=stats(s)
        assert hover['hover'],(label,'real pointer did not reach button')
        assert hover['image']=='none' and hover['bg']!='rgb(255, 255, 255)',(label,hover)
        assert base['rect']==hover['rect'] and hover['transform']=='none',(label,base,hover)
        assert hover['contrast']>=3,(label,hover)
        if not disabled:
            # Cancel the resulting click without bypassing actual CSS :active.
            run('document.addEventListener("click",e=>{e.preventDefault();e.stopImmediatePropagation()},{capture:true,once:true})')
            QTest.mousePress(view.focusProxy() or view,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,point);wait(140)
            active=stats(s)
            QTest.mouseRelease(view.focusProxy() or view,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,point)
            assert active['pressed'] and active['image']=='none' and active['bg']!='rgb(255, 255, 255)' and active['contrast']>=3,(label,active)
            assert base['rect']==active['rect'],(label,base,active)
            # Give Tab a deterministic starting point, even for the last
            # control in a native Qt focus chain. No synthetic focus pseudo-state.
            view.setFocus()
            run('window.focusStart=document.createElement("input");focusStart.style="position:fixed;width:1px;height:1px;left:0;top:0";document.querySelector('+json.dumps(s)+').before(focusStart);focusStart.focus()')
            QTest.keyClick(view.focusProxy() or view,Qt.Key.Key_Tab);wait(140)
            run('focusStart.remove()')
            focus=stats(s)
            assert focus['focus'] and focus['outline']=='solid' and focus['outlineWidth']=='2px' and focus['image']=='none' and focus['contrast']>=3,(label,focus)
        else:assert hover['bg']==base['bg'],(label,base,hover)
        theme='dark' if run('document.body.classList.contains("dark")') else 'light'
        checks.append({'theme':theme,'button':label,'hover_contrast':round(hover['contrast'],2),'geometry':'stable','states':'hover/pressed/focus' if not disabled else 'disabled-hover'})
        if label in ('Sign in','Empty-state primary','Send message'):
            out=root.parent/'qa/hover103';out.mkdir(parents=True,exist_ok=True);view.grab().save(str(out/(theme+'-'+label.replace(' ','-')+'.png')))
        QTest.mouseMove(view.focusProxy() or view,QPoint(1,1));wait(5)
    friend={'id':'friend','name':'Mia','username':'mia','code':'FRIEND','status':'accepted','incoming':False}
    pending={**friend,'id':'pending','name':'Pending friend','status':'pending','incoming':True}
    user={'id':'self','name':'Jay','username':'jay','code':'ME'}
    invitation={'id':'inv','sender':'friend','recipient':'self','sender_name':'Mia','state':'pending','summary':{'title':'Science','cards':3,'filtered_decks':0}}
    empty={'user':user,'friends':[friend,pending],'threads':[],'invites':[invitation]}
    thread={'id':'chat','title':'Mia','kind':'direct','members':[user,friend],'last':None,'last_id':0,'unread':0}
    png='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aRZkAAAAASUVORK5CYII='
    meta={'id':'photo','name':'Study image','mime':'image/png','sha256':'unused'}
    for dark in (False,True):
        emit('signed_out');emit('setup',{'url':'http://127.0.0.1:8766','dark':dark,'signed_in':False,'remember_available':True})
        if run('!!document.querySelector("#auth-name")'):click('[data-action=auth-switch]')
        check('#auth-form button[type=submit]','Sign in');check('[data-action=auth-switch]','Create-account link')
        run('document.querySelector("#auth-form button[type=submit]").disabled=true');check('#auth-form button[type=submit]','Disabled sign in',True);run('document.querySelector("#auth-form button[type=submit]").disabled=false')
        click('[data-action=auth-switch]');check('#auth-form button[type=submit]','Create account')
        emit('bootstrap',empty)
        check('[data-tab=chats]','Selected tab');check('[data-tab=friends]','Inactive tab')
        check('.empty [data-action=add-friend]','Empty-state primary');check('.empty [data-action=share]','Empty-state secondary');check('[data-action=new-group]','Sidebar icon')
        click('.empty [data-action=add-friend]');check('[data-action=friend-send]','Friend dialog primary');check('[data-action=close-modal].btn','Dialog cancel');check('[data-action=close-modal].icon','Dialog close');click('[data-action=close-modal].icon')
        click('[data-action=account]');check('[data-action=logout]','Account dialog');click('[data-action=close-modal]')
        click('[data-tab=friends]');check('[data-friend-accept]','Accept friend');check('[data-friend-reject]','Decline friend');check('[data-action=direct]','Friend message icon')
        click('[data-tab=inbox]');check('[data-action=preview]','Deck invitation')
        emit('bootstrap',{**empty,'threads':[thread]});click('[data-tab=chats]');click('[data-thread]')
        check('[data-thread]','Selected conversation');check('.chat-head [data-action=share]','Chat share');check('[data-action=send]','Send message');check('[data-action=image]','Image icon')
        click('[data-action=emoji]');check('[data-emoji]','Emoji picker');click('[data-action=emoji]')
        click('[data-action=sticker]');check('[data-sticker]','Built-in sticker');check('[data-action=upload-sticker]','Upload sticker')
        emit('blob',{'id':'photo','src':png});emit('sticker_library',[meta]);check('[data-saved-sticker]','Saved sticker');click('[data-action=sticker]')
        emit('messages',{'thread':'chat','messages':[{'id':1,'sender':'friend','name':'Mia','kind':'image','attachment':meta,'created':1}]})
        click('[data-photo]');check('.photo-close','Image viewer close');click('.photo-close')
        emit('catalog',[{'id':'1','name':'Science','filtered':False},{'id':'2','name':'Science::Lesson 1','filtered':False}])
        check('.chevron:not([disabled])','Deck tree expand');click('.chevron:not([disabled])');check('.chevron[disabled]','Deck tree leaf',True);check('[data-action=share-send]','Share decks dialog');click('[data-action=close-modal].icon')
        emit('invite_preview',{'manifest':{'summary':{'title':'Science'},'with_settings':True,'with_progress':True,'filters':[{}]},'invitation':invitation,'new_cards':3,'updated_notes':0,'existing_cards':0,'destination':'From Mia','needs_fsrs':False,'conflicts':[]})
        check('[data-action=reject]','Import dialog ghost');check('[data-action=close-modal].btn','Import later');check('[data-action=accept]','Import primary');click('[data-action=close-modal].icon')
    print(json.dumps({'native_button_states':'passed','count':len(checks),'checks':checks,'styles':'isolated from native and late theme rules','network_or_collection_changes':'none'}),flush=True)
