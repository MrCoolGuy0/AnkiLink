"""AnkiLink window/sidebar entry points; no reviewer or scheduler overrides."""
from aqt import gui_hooks,mw
from aqt.qt import QAction,QKeySequence
from aqt.utils import showWarning

controller=None
action=None
sidebar_action=None

def open_link(*args):
    global controller
    if not mw or not mw.col:return
    try:
        if controller is None:
            from .dialog import Controller
            controller=Controller(mw,__name__,action)
            controller.sidebar_action=sidebar_action
        controller.open()
    except Exception as error:showWarning('AnkiLink could not open:\n'+str(error),parent=mw)

def toggle_sidebar(*args):
    global controller
    if not mw or not mw.col:return
    try:
        if controller is None:
            from .dialog import Controller
            controller=Controller(mw,__name__,action);controller.sidebar_action=sidebar_action
        controller.toggle_sidebar()
    except Exception as error:showWarning('AnkiLink sidebar could not open:\n'+str(error),parent=mw)

def close_link(*args):
    global controller
    if controller is not None:controller.close();controller=None
    if action:action.setText('AnkiLink')

def study_changed(*args):
    # Read the current state/deck only. Never answer, queue or schedule cards.
    if controller is not None:controller.study_changed()

def restore_link(*args):
    global controller
    if controller is not None or not mw or not mw.col:return
    try:
        from .config import Store
        if Store(mw.pm.profileFolder()).token:
            from .dialog import Controller
            controller=Controller(mw,__name__,action)
            controller.sidebar_action=sidebar_action
    except Exception:pass  # A failed connection must never prevent opening Anki.

if mw:
    mw.addonManager.setWebExports(__name__,r'web/.*\.(html|css|js|png|svg)')
    action=QAction('AnkiLink',mw);action.setShortcut(QKeySequence('Ctrl+Alt+L'));action.triggered.connect(open_link);mw.form.menuTools.addAction(action)
    sidebar_action=QAction('AnkiLink sidebar',mw);sidebar_action.setShortcut(QKeySequence('Ctrl+Alt+J'));sidebar_action.triggered.connect(toggle_sidebar);mw.form.menuTools.addAction(sidebar_action)
    gui_hooks.profile_will_close.append(close_link)
    gui_hooks.state_did_change.append(study_changed)
    gui_hooks.reviewer_did_show_question.append(study_changed)
    gui_hooks.profile_did_open.append(restore_link)

    # Each AnkiLink WebView owns its bridge handler; no global message hook.
