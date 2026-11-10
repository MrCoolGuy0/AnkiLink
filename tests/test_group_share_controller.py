"""Group routing fails safely on old servers and keeps personal invite IDs."""
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
import test_message_controller as base
D=base.D


class GroupController(unittest.TestCase):
    setUp=base.MessageController.setUp
    finish=base.MessageController.finish
    def group(self):
        self.c.busy=False;self.c.social={'user':{'id':'me'},'invites':[],'features':{'group_deck_shares':True},'threads':[{'id':'group','kind':'group','members':[{'id':'me'},{'id':'friend'},{'id':'third'}]}]}
    def test_old_server_missing_or_empty_group_never_exports_or_sends_private_invites(self):
        self.group();self.c.social['features']={}
        with self.assertRaisesRegex(ValueError,'unavailable'):self.c.send_decks({'thread':'group'})
        self.c.social['features']['group_deck_shares']=True
        with self.assertRaisesRegex(ValueError,'not found'):self.c.send_decks({'thread':'other'})
        self.c.social['threads'][0]['members']=[{'id':'me'}]
        with self.assertRaisesRegex(ValueError,'another member'):self.c.send_decks({'thread':'group'})
        self.assertEqual(self.jobs,[]);self.assertEqual(self.requests,[]);self.assertFalse(self.c.busy)
    def test_group_export_upload_and_invite_carry_only_the_explicit_thread(self):
        self.group();captured=[]
        class Query:
            def __init__(self,**kw):captured.append(kw)
            def failure(self,fn):return self
            def run_in_background(self):pass
        with tempfile.TemporaryDirectory() as folder:
            self.c.temp=types.SimpleNamespace(name=folder);self.c.store.save=lambda:None
            self.c.client().upload=lambda path,mime:{'id':'file'}
            self.c.client().action=lambda action,data:self.requests.append((action,data)) or {'thread':'group','invitations':['one','two']}
            with patch.object(D,'QueryOp',Query):self.c.send_decks({'thread':'group','decks':['90'],'nonce':'same-operation','recipients':['wrong-private-person']})
            manifest={'roots':['90'],'cards':[{'key':'card'}],'notes':{},'summary':{'title':'Science','cards':1}}
            captured[0]['success'](manifest);self.finish(0);self.finish(1)
            self.assertEqual(self.requests,[('invite',{'thread':'group','file':'file','summary':manifest['summary'],'nonce':'same-operation'})])
            self.assertFalse(self.c.busy);self.assertTrue(any(event=='shared' for event,data in self.events))
    def test_personal_message_invites_survive_bootstrap_limits_without_foreign_access(self):
        self.group();mine={'id':'mine','sender':'sender','recipient':'me','state':'pending','created':1};foreign={**mine,'id':'foreign','recipient':'someone-else'}
        self.c.remember_invites([mine,foreign]);self.assertEqual(self.c.invite('mine'),mine)
        with self.assertRaisesRegex(ValueError,'not found'):self.c.invite('foreign')
        self.c.remember_invites([{**mine,'state':'accepted'}]);self.c.remember_invites([mine]);self.assertEqual(self.c.invite('mine')['state'],'accepted')
        self.c.reset_session_work()
        with self.assertRaisesRegex(ValueError,'not found'):self.c.invite('mine')


if __name__=='__main__':unittest.main()
