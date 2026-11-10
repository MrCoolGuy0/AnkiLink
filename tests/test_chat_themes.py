import tempfile,unittest
from pathlib import Path
import test_message_controller as base
from anki_link.config import Store

class ChatThemes(unittest.TestCase):
    def setUp(self):
        base.MessageController.setUp(self)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.c.store=Store(self.tmp.name);self.c.store.data.update(url='https://one.test',user={'id':'me'})
        self.c.social={'user':{'id':'me'},'threads':[{'id':'chat','kind':'direct'}]}
    def test_ankiretro_palettes_use_the_existing_appearance_setting(self):
        self.c.window = None
        self.assertEqual(self.c.appearance(), 'default')
        for appearance in ('ankiretro-baby-blue', 'ankiretro-maroon', 'ankiretro'):
            with self.subTest(appearance=appearance):
                self.c.set_appearance(appearance)
                self.assertEqual(self.events[-1], ('appearance', appearance))
                self.c.store = Store(self.tmp.name)
                self.assertEqual(self.c.appearance(), appearance)

    def test_saved_theme_survives_reopening_and_is_account_scoped(self):
        self.c.set_chat_theme('chat','#123abc')
        reopened=Store(self.tmp.name);self.assertEqual(reopened.data['chat_themes_by_account']['https://one.test|me']['chat'],'#123abc')
        self.assertEqual(self.c.chat_themes(),{'chat':'#123abc'})
        self.c.store.data['user']={'id':'another'};self.assertEqual(self.c.chat_themes(),{})
        self.c.store.data['user']={'id':'me'};self.c.set_chat_theme('chat','default');self.assertEqual(self.c.chat_themes(),{})
    def test_invalid_colors_and_unknown_chats_never_save(self):
        before=self.c.store.path.read_bytes() if self.c.store.path.exists() else None
        for value in ['red','url(evil)','#123','<script>',None]:
            with self.assertRaises(ValueError):self.c.set_chat_theme('chat',value)
        with self.assertRaises(ValueError):self.c.set_chat_theme('absent','#123abc')
        self.assertEqual(self.c.chat_themes(),{})
