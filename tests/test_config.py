"""Known hosted-address transition: no network, credentials or collections used."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('link_config_migration',ROOT/'anki_link/config.py')
C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
OLD=C.LEGACY_HOSTED_SERVERS[0]
NEW=C.DEFAULT_SERVER

class HostedAddressMigration(unittest.TestCase):
    def test_current_host_preferences_win_over_stale_earlier_aliases(self):
        oldest,current=C.LEGACY_HOSTED_SERVERS
        data={'url':current,
              'muted_by_account':{oldest+'|me':[],current+'|me':['currently-muted']},
              'activity':{oldest+'|me':True,current+'|me':False},
              'stickers':{oldest+'|me':[{'id':'old'}],current+'|me':[{'id':'new'}]}}
        self.assertTrue(C.migrate_hosted_address(data))
        self.assertEqual(data['muted_by_account'][NEW+'|me'],['currently-muted'])
        self.assertFalse(data['activity'][NEW+'|me'])
        self.assertEqual(data['stickers'][NEW+'|me'],[{'id':'new'}])
        self.assertEqual(data['stickers'][oldest+'|me'],[{'id':'old'}])

    def test_v140_official_host_moves_to_restored_service_with_account_state(self):
        previous='https://anki-link-evans.begrgbrgbrt.chatgpt.site'
        target='https://ankilink-jm.jdgarcia2697lag.chatgpt.site'
        data={'url':previous,'identity':'unchanged-device','user':{'id':'same-account'},
              'saved_token':'unchanged-encrypted-token','imports':{'accepted':'unchanged'},
              'lineage':{'note':'unchanged'},'last_shared':{'deck':'unchanged'},
              'muted_by_account':{previous+'|same-account':['chat']},
              'activity':{previous+'|same-account':True},
              'stickers':{previous+'|same-account':[{'id':'same-file'}]}}
        before=copy.deepcopy(data)
        self.assertTrue(C.migrate_hosted_address(data))
        self.assertEqual(data['url'],target)
        for key in ('identity','user','saved_token','imports','lineage','last_shared'):
            self.assertEqual(data[key],before[key])
        for field in ('muted_by_account','activity','stickers'):
            self.assertEqual(data[field][target+'|same-account'],before[field][previous+'|same-account'])
        self.assertFalse(C.migrate_hosted_address(data),'reopening an updated profile must be idempotent')

    def profile(self,folder,data):
        path=Path(folder)/'anki_link/settings.json';path.parent.mkdir()
        path.write_text(json.dumps(data),encoding='utf-8');return path
    def test_saved_identity_tokens_receipts_and_preferences_survive_reopening(self):
        data={'url':OLD,'identity':'source-id','user':{'id':'me'},'saved_token':'synthetic-encrypted',
              'imports':{'receipt':{'done':True}},'lineage':{'source':{'note':'hash'}},
              'last_shared':{'deck':{'keys':['card']}},'muted':['legacy-thread'],
              'muted_by_account':{OLD+'|me':['chat'],OLD+'|second':['group']},
              'activity':{OLD+'|me':True},'stickers':{OLD+'|me':[{'id':'sticker'}]}}
        before=copy.deepcopy(data)
        with tempfile.TemporaryDirectory() as folder,patch.object(C,'protect',return_value='session-token') as crypto:
            path=self.profile(folder,data);store=C.Store(folder);self.assertEqual(store.token,'session-token')
            crypto.assert_called_once_with('synthetic-encrypted',True)
            saved=json.loads(path.read_text());self.assertEqual(saved['url'],NEW)
            for key in ('identity','user','saved_token','imports','lineage','last_shared','muted'):
                self.assertEqual(saved[key],before[key])
            for field in ('muted_by_account','activity','stickers'):
                self.assertEqual(saved[field][NEW+'|me'],before[field][OLD+'|me'])
                self.assertEqual(saved[field][OLD+'|me'],before[field][OLD+'|me'])
            self.assertEqual(saved['muted_by_account'][NEW+'|second'],['group'])
            content=path.read_bytes();C.Store(folder);self.assertEqual(path.read_bytes(),content,'migration is idempotent')
    def test_custom_servers_and_similar_domains_are_never_changed(self):
        for url in ('https://my-relay.test',OLD+'.example',OLD+'/other','http://anki-link-evans.earthybox12.chatgpt.site'):
            data={'url':url,'activity':{url+'|me':True}};before=copy.deepcopy(data)
            self.assertFalse(C.migrate_hosted_address(data));self.assertEqual(data,before)
    def test_newer_destination_preferences_take_precedence_and_other_accounts_stay(self):
        data={'url':OLD,'activity':{OLD+'|me':True,NEW+'|me':False,'https://other.test|me':True},
              'muted_by_account':{OLD+'|me':['old'],NEW+'|me':['current']}}
        C.migrate_hosted_address(data)
        self.assertFalse(data['activity'][NEW+'|me']);self.assertTrue(data['activity']['https://other.test|me'])
        self.assertEqual(data['muted_by_account'][NEW+'|me'],['current'])
    def test_known_trailing_slash_alias_migrates_and_fresh_profiles_use_current_host(self):
        data={'url':OLD+'/','stickers':{OLD+'/|me':[{'id':'one'}]}}
        self.assertTrue(C.migrate_hosted_address(data));self.assertEqual(data['stickers'][NEW+'|me'],[{'id':'one'}])
        with tempfile.TemporaryDirectory() as folder:self.assertEqual(C.Store(folder).data['url'],NEW)
    def test_corrupt_settings_are_preserved_and_not_replaced_by_defaults(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'anki_link/settings.json';path.parent.mkdir();path.write_text('{broken')
            with self.assertRaisesRegex(ValueError,'preserved'):C.Store(folder)
            self.assertEqual(path.read_text(),'{broken')

if __name__=='__main__':unittest.main()
