"""Actual Rust-backed Anki collections; isolated synthetic cards only."""
import copy
import importlib
import json
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest

ROOT=Path(__file__).resolve().parents[1]
pkg=types.ModuleType('anki_link');pkg.__path__=[str(ROOT/'anki_link')];sys.modules.setdefault('anki_link',pkg)
T=importlib.import_module('anki_link.transfer');Store=importlib.import_module('anki_link.config').Store
try:
    from anki.collection import Collection
except ImportError:Collection=None

@unittest.skipUnless(Collection,'Install anki in a private test environment to run native transfer checks')
class NativeTransfers(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.sender=Collection(str(self.root/'sender.anki2'))
        # Anki assigns consecutive millisecond IDs to stock note types. Two
        # profiles created in the same millisecond can give a sender cloze and
        # receiver Basic the same ID, an unrelated native import collision.
        # Model independent profiles, with disjoint stock-ID creation windows.
        wait=(max(m.id for m in self.sender.models.all_names_and_ids())+1)/1000-time.time()
        if wait>0:time.sleep(wait)
        self.receiver=Collection(str(self.root/'receiver.anki2'))
        self.addCleanup(self.sender.close);self.addCleanup(self.receiver.close)
        (self.root/'sp').mkdir();(self.root/'rp').mkdir();self.ss=Store(self.root/'sp');self.rs=Store(self.root/'rp')
        self.did=self.sender.decks.id('Midterms::Science::Lesson 1')
        self.note=self.add('Heart chambers','Four');self.path=self.root/'share.alink'
    def add(self,front,back,kind='Basic'):
        note=self.sender.new_note(self.sender.models.by_name(kind));note.fields[:]=[front,back];self.sender.add_note(note,self.did);return note
    def send(self,ids=None,settings=True,progress=False):return T.make_bundle(self.sender,self.ss,ids or [self.sender.decks.id('Midterms')],self.path,settings,progress)
    def receive(self,receipt='one',**opts):return T.apply_bundle(self.receiver,self.rs,self.path,dict(destination='From partner',settings=True,progress=False,build_filters=True,**opts),receipt)
    def test_exact_presets_new_limits_hierarchy_fresh_cards_and_no_sender_writes(self):
        config=self.sender.decks.config_dict_for_deck_id(self.did);config['new']['perDay']=17;config['desiredRetention']=.94;config['newGatherPriority']=2;self.sender.decks.update_config(config)
        deck=self.sender.decks.get(self.did);deck['newLimit']=12;self.sender.decks.update_dict(deck)
        native=self.sender._backend.get_deck(self.did)
        if 'desired_retention' in native.normal.DESCRIPTOR.fields_by_name:native.normal.desired_retention=.93;self.sender._backend.update_deck(native)
        card=self.note.cards()[0];self.sender.sched.set_due_date([card.id],'8');card=self.sender.get_card(card.id);card.reps=9;card.lapses=2;self.sender.update_card(card)
        before=self.sender.db.all('SELECT * FROM cards');self.send();self.assertEqual(self.sender.db.all('SELECT * FROM cards'),before)
        result=self.receive();self.assertEqual(result['cards'],1);c=self.receiver.get_card(self.receiver.find_cards('')[0]);self.assertEqual((c.type,c.reps,c.lapses),(0,0,0))
        did=self.receiver.decks.id_for_name('From partner::Midterms::Science::Lesson 1');self.assertTrue(did)
        got=self.receiver.decks.config_dict_for_deck_id(did);self.assertEqual(got['new']['perDay'],17);self.assertEqual(got['desiredRetention'],.94)
        deck=self.receiver.decks.get(did);self.assertEqual(deck['newLimit'],12);self.assertEqual(deck.get('desiredRetention'),self.sender.decks.get(self.did).get('desiredRetention'))
        if 'desired_retention' in native.normal.DESCRIPTOR.fields_by_name:self.assertAlmostEqual(self.receiver._backend.get_deck(did).normal.desired_retention,.93,places=5)
        self.assertEqual(self.receiver.decks.get_config(1)['new']['perDay'],20,'receiver Default is not overwritten')
    def test_repeated_send_edits_new_cards_and_receiver_progress_are_preserved(self):
        self.send();self.receive();cid=self.receiver.find_cards('')[0];self.receiver.sched.set_due_date([cid],'12')
        before=self.receiver.get_card(cid);self.note['Back']='Four chambers';self.sender.update_note(self.note);self.add('New question','New answer');self.send(settings=False)
        p=T.preview(self.receiver,self.rs,self.path);self.assertEqual(p['new_cards'],1);self.assertEqual(p['updated_notes'],1);self.assertEqual(p['conflicts'],[])
        T.apply_bundle(self.receiver,self.rs,self.path,{'destination':'From partner','settings':False},'two')
        self.assertEqual(len(self.receiver.find_cards('')),2);after=self.receiver.get_card(cid);self.assertEqual((after.type,after.due,after.ivl),(before.type,before.due,before.ivl))
        self.assertEqual(after.note()['Back'],'Four chambers')
        T.apply_bundle(self.receiver,self.rs,self.path,{'destination':'From partner','settings':False},'three');self.assertEqual(len(self.receiver.find_cards('')),2)
    def test_local_conflict_keep_or_explicit_replace(self):
        self.send();self.receive();cid=self.receiver.find_cards('')[0];local=self.receiver.get_card(cid).note();local['Back']='My explanation';self.receiver.update_note(local)
        self.note['Back']='Sender correction';self.sender.update_note(self.note);self.send()
        self.assertEqual(len(T.preview(self.receiver,self.rs,self.path)['conflicts']),1)
        self.receive('keep');self.assertEqual(self.receiver.get_card(cid).note()['Back'],'My explanation')
        self.receive('replace',replace_conflicts=True);self.assertEqual(self.receiver.get_card(cid).note()['Back'],'Sender correction')
    def test_filtered_only_recreated_below_empty_parents_with_home_and_no_duplicates(self):
        self.add('Other','Answer');f=self.sender.sched.get_or_create_filtered_deck(0);f.name='Practice::Science::Round 1';f.config.reschedule=False
        del f.config.search_terms[1:];f.config.search_terms[0].search='deck:'+T.quote('Midterms');f.config.search_terms[0].limit=100
        fid=self.sender.sched.add_or_update_filtered_deck(f).id;self.sender.sched.rebuild_filtered_deck(fid)
        before=self.sender.db.all('SELECT * FROM cards');self.send([self.sender.decks.id('Practice')]);self.assertEqual(self.sender.db.all('SELECT * FROM cards'),before)
        result=self.receive();self.assertEqual(len(self.receiver.find_cards('')),2);self.assertEqual(result['filtered'][0]['built'],2)
        target=self.receiver.decks.get(self.receiver.decks.id_for_name('From partner::Practice::Science::Round 1'));self.assertTrue(target['dyn']);self.assertFalse(target['resched'])
        for cid in self.receiver.find_cards(''):
            c=self.receiver.get_card(cid);self.assertTrue(c.odid);self.assertNotEqual(c.did,c.odid)
        self.receive('again');self.assertEqual(len(self.receiver.find_cards('')),2)
    def test_progress_copy_and_idempotent_completed_reset_receipt(self):
        card=self.note.cards()[0];self.sender.sched.set_due_date([card.id],'15');card=self.sender.get_card(card.id);card.reps=8;self.sender.update_card(card)
        self.send(progress=True);T.apply_bundle(self.receiver,self.rs,self.path,{'destination':'From partner','progress':True},'progress')
        cid=self.receiver.find_cards('')[0];self.assertEqual(self.receiver.get_card(cid).type,2);self.assertEqual(self.receiver.get_card(cid).reps,8)
        T.apply_bundle(self.receiver,self.rs,self.path,{'destination':'From partner','reset':True},'reset');self.assertEqual(self.receiver.get_card(cid).type,0)
        self.receiver.sched.set_due_date([cid],'10');T.apply_bundle(self.receiver,self.rs,self.path,{'destination':'From partner','reset':True},'reset')
        self.assertEqual(self.receiver.get_card(cid).type,2,'completed receipt cannot reset the card twice')
    def test_selected_cloze_card_does_not_send_unrelated_card_ordinals(self):
        note=self.add('{{c1::one}} then {{c2::two}}','',kind='Cloze');cards=note.cards();source=self.sender.sched.get_or_create_filtered_deck(0);source.name='Only c1';source.config.reschedule=False
        del source.config.search_terms[1:];source.config.search_terms[0].search='cid:'+str(cards[0].id);fid=self.sender.sched.add_or_update_filtered_deck(source).id;self.sender.sched.rebuild_filtered_deck(fid)
        self.send([fid]);self.receive();self.assertEqual(len(self.receiver.find_cards('')),1)
        self.assertEqual(self.receiver.get_card(self.receiver.find_cards('')[0]).ord,cards[0].ord)
    def test_filtered_sixty_to_eighty_adds_only_twenty_and_keeps_learning_state(self):
        for i in range(59):self.add('Question '+str(i),'Answer '+str(i))
        f=self.sender.sched.get_or_create_filtered_deck(0);f.name='Practice::Science::All';f.config.reschedule=False;del f.config.search_terms[1:]
        f.config.search_terms[0].search='deck:'+T.quote('Midterms');f.config.search_terms[0].limit=100;fid=self.sender.sched.add_or_update_filtered_deck(f).id;self.sender.sched.rebuild_filtered_deck(fid)
        self.send([self.sender.decks.id('Practice')]);self.receive('sixty');rfid=self.receiver.decks.id_for_name('From partner::Practice::Science::All')
        self.assertEqual(len(self.receiver.find_cards('')),60);self.receiver.sched.empty_filtered_deck(rfid)
        cid=self.receiver.find_cards('')[0];self.receiver.sched.set_due_date([cid],'11');before=self.receiver.get_card(cid)
        for i in range(20):self.add('Extra '+str(i),'New answer '+str(i))
        self.sender.sched.rebuild_filtered_deck(fid);self.send([self.sender.decks.id('Practice')]);p=T.preview(self.receiver,self.rs,self.path);self.assertEqual(p['new_cards'],20)
        result=self.receive('eighty');self.assertEqual(result['cards'],80);self.assertEqual(result['filtered'][0]['built'],80);self.assertEqual(len(self.receiver.find_cards('')),80)
        after=self.receiver.get_card(cid);self.assertEqual((after.type,after.ivl,after.odue),(before.type,before.ivl,before.due))
    def test_two_filter_rules_keep_their_groups_after_progress_is_removed(self):
        self.sender.sched.set_due_date([self.note.cards()[0].id],'0')
        for i in range(3):self.add('New '+str(i),'Answer')
        f=self.sender.sched.get_or_create_filtered_deck(0);f.name='Mixed practice';f.config.reschedule=False
        f.config.search_terms[0].search='deck:Midterms is:review';f.config.search_terms[0].limit=10;f.config.search_terms[0].order=0
        f.config.search_terms[1].search='deck:Midterms is:new';f.config.search_terms[1].limit=10;f.config.search_terms[1].order=2
        fid=self.sender.sched.add_or_update_filtered_deck(f).id;self.sender.sched.rebuild_filtered_deck(fid)
        manifest=self.send([fid]);self.assertEqual([len(g['members']) for g in manifest['filters'][0]['groups']],[1,3])
        self.receive();did=self.receiver.decks.id_for_name('From partner::Mixed practice');got=self.receiver.sched.get_or_create_filtered_deck(did)
        self.assertEqual([t.order for t in got.config.search_terms],[0,2]);self.assertEqual(len(self.receiver.find_cards('')),4)
    def test_destination_type_collision_is_rejected_before_import(self):
        self.send();f=self.receiver.decks.new_deck_legacy(True);f['name']='From partner';self.receiver.decks.add_deck_legacy(f)
        with self.assertRaisesRegex(ValueError,'different deck type'):self.receive()
        self.assertEqual(self.receiver.find_cards(''),[])

if __name__=='__main__':unittest.main()
