"""Native Qt/Chromium compact-control geometry and interaction regression.

Runs offline with synthetic people and messages. Screenshots default to a temp
folder; pass --output DIR to preserve review images. Requires PyQt6-WebEngine.
"""
from pathlib import Path
import argparse
import json
import math
import os
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    parser.add_argument('--appearance', choices=('default', 'ankiretro', 'ankiretro-baby-blue', 'ankiretro-maroon', 'ankirise', 'ankimessage'), default='ankiretro')
    args = parser.parse_args()
    retro = args.appearance.startswith('ankiretro')
    retro_variant = retro and args.appearance != 'ankiretro'
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS', '--no-sandbox --disable-gpu')
    from PyQt6.QtCore import QEventLoop, QTimer, QPoint, Qt, QUrl
    from PyQt6.QtTest import QTest
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtWebEngineWidgets import QWebEngineView

    app = QApplication(['compact-ui-qa'])
    view = QWebEngineView()
    web = Path(__file__).resolve().parents[1] / 'anki_link/web'
    out = args.output or Path(tempfile.mkdtemp(prefix='ankilink-compact-ui-'))
    out.mkdir(parents=True, exist_ok=True)

    def wait(ms=35):
        loop = QEventLoop()
        QTimer.singleShot(ms, loop.quit)
        loop.exec()

    def js(code):
        loop = QEventLoop()
        result = []
        view.page().runJavaScript(code, lambda value: (result.append(value), loop.quit()))
        QTimer.singleShot(5000, loop.quit)
        loop.exec()
        assert result, 'JavaScript evaluation timed out'
        return result[0]

    def emit(event, data=None):
        js('ankiLink.receive(' + json.dumps(event) + ',' + json.dumps(data) + ')')
        wait()

    def click(selector):
        rect = js('(()=>{const n=document.querySelector(' + json.dumps(selector) + ');if(!n)return null;const r=n.getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]})()')
        assert rect, selector
        point = QPoint(round(rect[0]), round(rect[1]))
        QTest.mouseMove(view.focusProxy() or view, point)
        wait(140)
        QTest.mouseClick(view.focusProxy() or view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point)
        wait()

    def rect(selector):
        return js('(()=>{const r=document.querySelector(' + json.dumps(selector) + ').getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height}})()')

    def bounded(selector, width):
        box = rect(selector)
        assert box['left'] >= 7 and box['right'] <= width - 7, (selector, width, box)
        assert box['top'] >= 7 and box['bottom'] <= 713, (selector, box)
        return box

    def check_message_header(identity_selector, width):
        head, identity, actions = (rect(selector) for selector in ('.chat-head', identity_selector, '.chat-actions'))
        assert abs((head['left'] + head['right']) - (identity['left'] + identity['right'])) < 1, (width, head, identity)
        assert actions['left'] - identity['right'] >= 4, (width, identity, actions)
        if width <= 700:
            assert identity['left'] - rect('.chat-back')['right'] >= 4
        share = js('''(() => {
            const button = document.querySelector('.chat-actions [data-action=share]');
            return [button.innerText.trim(), button.getAttribute('aria-label'), button.title];
        })()''')
        assert share == (['', 'Share decks', 'Share decks'] if width <= 700 else ['Share decks', 'Share decks', 'Share decks'])
        assert (rect('.chat-actions [data-action=share] svg')['width'] > 0) == (width <= 700)

    def check_message_tails():
        shot = view.grab()
        frame = shot.toImage()
        scale = shot.devicePixelRatio()

        def pixel(x, y):
            return frame.pixelColor(math.floor(x * scale), math.floor(y * scale))

        for selector, edge, side in (('.message:not(.mine) .text-bubble', 'left', -1),
                                     ('.mine .text-bubble', 'right', 1)):
            bubble = rect(selector)
            edge_x, bottom = bubble[edge], bubble['bottom']
            color = pixel((bubble['left'] + bubble['right']) / 2, bottom - 1.5)
            reaches = [distance for distance in range(1, 8)
                       if any(pixel(edge_x + side * (distance - .5), bottom - row) == color for row in (.5, 1.5, 2.5))]
            assert reaches and 2 <= max(reaches) <= 4, (selector, reaches)

    html = '<!doctype html><meta charset="utf-8">'
    html += '<style>' + '\n'.join((web / name).read_text() for name in ('app.css', 'controls.css', 'retro.css', 'rise.css', 'message.css')) + '</style>'
    html += (web / 'index.html').read_text()
    html += '<script>window.calls=[];window.pycmd=raw=>calls.push(JSON.parse(raw.slice(10)));</script><script>' + (web / 'app.js').read_text() + '</script>'
    view.resize(300, 720)
    view.show()
    loaded = QEventLoop()
    view.loadFinished.connect(loaded.quit)
    view.setHtml(html, QUrl.fromLocalFile(str(web / 'index.html')))
    QTimer.singleShot(10000, loaded.quit)
    loaded.exec()
    wait(100)
    assert js('!!window.ankiLink')
    me = {'id': 'me', 'name': 'Jay', 'username': 'jay'}
    member = {'id': 'member', 'name': 'Mia Long Display Name', 'username': 'mia_studies'}
    admin = {'id': 'admin', 'name': 'Theo', 'username': 'theo', 'admin': True}
    notice = 'Jay added Mia <img src=x onerror=alert(1)>'
    group = {'id': 'group', 'kind': 'group', 'title': 'Study friends', 'owner': 'me', 'membership_version': 1, 'members': [me, admin, member], 'unread': 0, 'last': {'kind': 'system', 'text': notice}}
    direct = {'id': 'direct', 'kind': 'direct', 'title': member['name'], 'members': [me, member], 'unread': 0}
    boot = {'user': me, 'friends': [], 'threads': [group, direct], 'invites': [], 'features': {'message_reactions': True, 'group_administration': True}}
    direct_messages = [{'id': 18, 'thread': 'direct', 'sender': 'member', 'name': member['name'], 'kind': 'text', 'text': 'Hey, how is studying going?', 'created': 18},
                       {'id': 19, 'thread': 'direct', 'sender': 'me', 'name': me['name'], 'kind': 'text', 'text': 'I just finished the first chapter.', 'created': 19}]
    messages = [{'id': i, 'thread': 'group', 'sender': 'member', 'name': member['name'], 'kind': 'text', 'text': 'Earlier study message ' + str(i), 'created': i} for i in range(1, 15)]
    messages += [{'id': 15, 'thread': 'group', 'sender': 'me', 'name': me['name'], 'kind': 'system', 'text': notice, 'created': 15},
                 {'id': 16, 'thread': 'group', 'sender': 'member', 'name': member['name'], 'kind': 'text', 'text': 'Ready for the next chapter?', 'created': 16, 'reactions': [{'emoji': '👍', 'count': 2, 'users': ['me', 'member']}]},
                 {'id': 17, 'thread': 'group', 'sender': 'me', 'name': me['name'], 'kind': 'text', 'text': 'Yes, see you at 7!', 'created': 17, 'reactions': [{'emoji': '🎉', 'count': 1, 'users': ['member']}]}]
    if retro:
        messages[13].update(kind='deck', text='Midterms::Biology')
    checks = []
    widths = (300, 420, 700, 820) if args.appearance == 'ankimessage' else (300, 420, 820)
    for dark in (False, True):
        theme = 'dark' if dark else 'light'
        for width in widths:
            view.resize(width, 720)
            emit('signed_out')
            emit('setup', {'dark': dark, 'appearance': args.appearance})
            emit('bootstrap', boot)
            if retro_variant and width == 300:
                click('.self [data-action=account]')
                options = js('Array.from(document.querySelector("#appearance-theme").options, o => o.text)')
                assert [label for label in options if label.startswith('AnkiRetro')] == [
                    'AnkiRetro', 'AnkiRetro · Baby Blue', 'AnkiRetro · Maroon']
                assert js('document.querySelector("#appearance-theme").value') == args.appearance
                js('''(() => {
                    const select = document.querySelector("#appearance-theme");
                    select.value = "ankiretro";
                    select.dispatchEvent(new Event("change", {bubbles: true}));
                })()''')
                assert js('calls.at(-1)') == {'action': 'appearance', 'theme': 'ankiretro'}
                emit('appearance', args.appearance)
                click('[data-action=close-modal]')
            if args.appearance == 'ankimessage':
                js('document.querySelector("[data-thread=direct]").click()')
                emit('messages', {'thread': 'direct', 'messages': direct_messages})
                wait(100)
                view.grab().save(str(out / f'{theme}-{width}-chat.png'))
                check_message_header('.chat-identity', width)
                check_message_tails()
                click('.chat-actions [data-action=share]')
                assert js('document.querySelector(".modal-head h2").textContent') == 'Share decks'
                assert js('calls.at(-1).action') == 'catalog'
                click('[data-action=close-modal]')
                click('.chat-actions [data-action=conversation-options]')
                assert js('!!document.querySelector("#chat-notifications")')
                click('[data-action=close-modal]')
                if width <= 700:
                    click('.chat-back')
                    assert js('!document.querySelector(".layout.conversation-open")')
            assert js('document.querySelector("[data-thread=group] small").textContent') == notice
            js('document.querySelector("[data-thread=group]").click()')
            emit('messages', {'thread': 'group', 'messages': messages})
            wait(100)
            assert js('document.documentElement.scrollWidth<=innerWidth'), width
            if retro:
                assert js("""(() => {
                    const style = (selector, pseudo) => getComputedStyle(document.querySelector(selector), pseudo);
                    return !document.querySelector(".brand-spark")
                        && style(".chat-head", "::before").content === "none"
                        && style(".messages").backgroundImage === "none"
                        && style(".messages").backgroundColor !== "rgba(0, 0, 0, 0)"
                        && style(".message:not(.mine) .text-bubble").backgroundColor !== style(".mine .text-bubble").backgroundColor
                        && style(".deck-bubble").backgroundImage === "none"
                        && style(".deck-symbol", "::after").content === "none"
                        && document.querySelector(".send-btn").innerText.trim() === "Send";
                })()"""), (theme, width, 'classic AnkiRetro palette and controls')
                editor, send_button, tools_button = (rect(s) for s in ('#message-input', '.send-btn', '.composer [data-action=emoji]'))
                assert editor['right'] < send_button['left'] and send_button['bottom'] < tools_button['top']
                assert tools_button['right'] <= send_button['right']
            if retro_variant:
                incoming = js('getComputedStyle(document.querySelector(".message:not(.mine) .text-bubble")).backgroundColor')
                red, green, blue = map(int, incoming.removeprefix('rgb(').removesuffix(')').split(', '))
                if args.appearance == 'ankiretro-baby-blue':
                    assert blue > green > red, (theme, incoming)
                else:
                    assert red > blue > green, (theme, incoming)
                head = rect('.chat-head')
                composer = rect('.composer')
                palette = js('getComputedStyle(document.querySelector(".chat-head")).backgroundColor')
                assert js('document.body.classList.contains(' + json.dumps(args.appearance) + ')')
                emit('appearance', 'ankiretro')
                assert head == rect('.chat-head') and composer == rect('.composer')
                assert palette != js('getComputedStyle(document.querySelector(".chat-head")).backgroundColor')
                assert js('document.body.className.split(" ").every(name => !name.startsWith("ankiretro-"))')
                emit('appearance', args.appearance)
            if args.appearance == 'ankirise':
                frame, head, message_area, composer = (rect(s) for s in ('.chat-workspace', '.chat-head', '.messages', '.composer'))
                assert head['left'] == message_area['left'] == frame['left'] + 2
                assert head['right'] == message_area['right'] == frame['right'] - 2
                assert head['bottom'] == message_area['top']
                assert composer['bottom'] <= frame['bottom'] - 2
                assert js('getComputedStyle(document.querySelector(".messages")).scrollbarGutter') == 'stable'
            if args.appearance == 'ankimessage':
                check_message_header('.group-summary', width)
            assert js('document.querySelector(".message-system").textContent') == notice
            assert js('!document.querySelector(".message-system img,.message-system button,.message-system .avatar,.message-system .delivery-status,.message-system .deck-symbol")')
            assert js('getComputedStyle(document.querySelector(".message-system")).textAlign') == 'center'
            assert js('getComputedStyle(document.querySelector(".message-system"), "::before").content') == 'none'
            assert js('getComputedStyle(document.querySelector(".message-system"), "::after").content') == 'none'
            own = '[data-message-id="17"]'
            bubble = rect(own + ' .bubble')
            add = rect(own + ' .reaction-add')
            assert abs(bubble['left'] - add['right'] - 5) < 1, (width, bubble, add)
            assert add['left'] >= 0 and add['right'] <= width, (width, add)
            chips = rect(own + ' .message-reactions')
            assert abs(chips['right'] - bubble['right']) < 1
            assert 0 <= chips['top'] - bubble['bottom'] <= 5
            old_height = js('document.querySelector(".messages").scrollHeight')
            click(own + ' .reaction-add')
            assert js('document.querySelector(".reaction-picker").parentElement===document.body')
            bounded('.reaction-picker', width)
            assert js('document.querySelector(".messages").scrollHeight') == old_height
            view.grab().save(str(out / f'{theme}-{width}-reaction.png'))
            click(own + ' .reaction-add')
            assert js('!document.querySelector(".reaction-picker")'), 'same button toggle'
            click(own + ' .reaction-add')
            click('#message-input')
            assert js('!document.querySelector(".reaction-picker")'), 'outside pointer dismissal'
            click(own + ' .reaction-add')
            QTest.keyClick(view.focusProxy() or view, Qt.Key.Key_Escape)
            wait()
            assert js('!document.querySelector(".reaction-picker") && document.activeElement.matches("[data-react-message=\\"17\\"]")')
            click(own + ' .reaction-add')
            js('document.querySelector(".messages").scrollTop-=20')
            wait()
            assert js('!document.querySelector(".reaction-picker")'), 'real scroll dismissal'
            js('document.querySelector(".messages").scrollTop=99999')
            wait()
            click(own + ' .reaction-add')
            click('[data-reaction-choice="👍"]')
            assert js('calls.filter(c=>c.action==="reaction").at(-1).emoji') == '👍', 'pointer emoji click dispatches before dismissal'
            emit('reaction_updated', {'thread': 'group', 'message': 17, 'reaction_version': 1, 'reactions': [{'emoji': '👍', 'count': 2, 'users': ['me', 'member']}]})
            click(own + ' [data-reaction-people="👍"]')
            assert js('document.querySelector(".reaction-people").textContent.includes("Jay")')
            bounded('.modal', width)
            assert js('document.querySelectorAll(".reaction-person .avatar").length') == 2
            face = rect('.reaction-person .avatar')
            assert face['width'] == 40 and face['height'] == 40
            copy = rect('.reaction-person-copy')
            assert copy['left'] - face['right'] >= 11
            assert js('document.querySelector(".reaction-summary-count").textContent') == '2 people'
            wait(200)
            view.grab().save(str(out / f'{theme}-{width}-reaction-people.png'))
            click('[data-action=close-modal]')
            click('[data-action=group-details]')
            assert js('!document.querySelector("[data-action=group-admin],[data-action=group-remove]")')
            row_width = rect('[data-member-menu=member]')['right']
            assert row_width <= width - 15, (width, row_width, rect('.modal'))
            click('[data-member-menu=member]')
            bounded('.member-menu', width)
            assert js('document.activeElement.matches(".member-menu button")'), 'portal preserves dialog keyboard focus'
            assert js('document.querySelectorAll(".member-menu [role=menuitem]").length') == 2
            view.grab().save(str(out / f'{theme}-{width}-member-menu.png'))
            QTest.keyClick(view.focusProxy() or view, Qt.Key.Key_Down)
            wait()
            assert js('document.activeElement.dataset.action') == 'group-remove'
            QTest.keyClick(view.focusProxy() or view, Qt.Key.Key_Escape)
            wait()
            assert js('!document.querySelector(".member-menu") && document.activeElement.matches("[data-member-menu=member]")')
            click('[data-member-menu=member]')
            click('.modal-head h2')
            assert js('!document.querySelector(".member-menu")'), 'member outside pointer dismissal'
            click('[data-member-menu=member]')
            click('[data-action=group-remove]')
            assert js('document.querySelector(".modal").textContent.includes("lose access")')
            assert js('calls.filter(c=>c.action==="group_remove").length') == 0, 'removal retains confirmation'
            click('[data-action=close-modal]')
            click('[data-action=conversation-options]')
            click('.chat-color-options summary')
            bounded('.chat-color-swatches', width)
            swatch = '[data-chat-color]:not([data-chat-color="default"])'
            color = js('document.querySelector(' + json.dumps(swatch) + ').dataset.chatColor')
            rgb = ', '.join(str(int(color[i:i+2], 16)) for i in (1, 3, 5))
            assert js('getComputedStyle(document.querySelector(' + json.dumps(swatch) + ')).backgroundColor') == f'rgb({rgb})'
            click(swatch)
            assert js('ankiLink.state.chatThemes.group') == color
            view.grab().save(str(out / f'{theme}-{width}-chat-colors.png'))
            assert js('document.documentElement.scrollWidth<=innerWidth')
            click('[data-action=close-modal]')
            assert js('getComputedStyle(document.querySelector(".mine .bubble")).backgroundColor') != 'rgba(0, 0, 0, 0)'
            if retro:
                click('.composer [data-action=emoji]')
                bounded('.picker', width)
                assert js('!!document.querySelector(".picker .emoji-grid")')
                click('.composer [data-action=emoji]')
                js('document.querySelector("#message-input").value = "Ready to review"')
                click('.send-btn')
                assert js('calls.findLast(c => c.action === "message")?.text') == 'Ready to review'
            checks.append({'width': width, 'theme': theme, 'geometry': 'bounded', 'native_pointer_and_keyboard': 'passed'})
    print(json.dumps({'compact_native_ui': 'passed', 'checks': checks, 'screenshots': str(out)}))
    view.close()
    app.quit()


if __name__ == '__main__':
    main()
