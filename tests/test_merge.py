"""Native collection regression for merging hierarchy, resends and prior folders."""
import copy
import unittest
import test_transfer as native
T=native.T

@unittest.skipUnless(native.Collection,'Install anki privately for native merge checks')
class MergeTransfers(unittest.TestCase):
    setUp=native.NativeTransfers.setUp
    add=native.NativeTransfers.add
    send=native.NativeTransfers.send
    def merge(self,receipt='merge',**options):
        return T.apply_bundle(self.receiver,self.rs,self.path,{'merge':True,'settings':False,**options},receipt)
    def matching(self,note):
        return next(self.receiver.get_note(nid) for nid,guid in self.receiver.db.all('SELECT id,guid FROM notes') if guid==note.guid)
    def state(self,cid):
        columns=[r[1] for r in self.receiver.db.all('PRAGMA table_info(cards)')]
        values=self.receiver.db.all('SELECT * FROM cards WHERE id=?',cid)[0]
        return {k:v for k,v in zip(columns,values) if k not in ('did','odid','mod','usn')}
    def test_leaf_first_then_parent_keeps_ancestors_and_reuses_the_original_lesson(self):
        self.did=self.sender.decks.id('Midterms::Science::Lesson 2');self.add('Second lesson','Answer 2')
        self.did=self.sender.decks.id('Midterms::Science::Lesson 3');lesson3=self.did;third=self.add('Third lesson','Answer 3')
        self.did=self.sender.decks.id('Midterms');self.add('Parent-only card','Do not send with a leaf')
        self.did=self.sender.decks.id('Midterms::Other subject');self.add('Other subject','Do not send with Science')
        source=self.sender.db.all('SELECT * FROM cards')
        manifest=self.send([lesson3],settings=False)
        self.assertEqual({d['name'] for d in manifest['decks']},{'Midterms','Midterms::Science','Midterms::Science::Lesson 3'})
        self.assertEqual(len(manifest['cards']),1);self.assertEqual(set(manifest['notes']),{third.guid})
        self.merge('leaf-first')
        self.assertEqual(len(self.receiver.find_cards('')),1)
        for name in ('Midterms','Midterms::Science','Midterms::Science::Lesson 3'):self.assertTrue(self.receiver.decks.id_for_name(name))
        self.assertIsNone(self.receiver.decks.id_for_name('Midterms::Science::Lesson 1'))
        self.assertIsNone(self.receiver.decks.id_for_name('Midterms::Science::Lesson 2'))
        self.assertIsNone(self.receiver.decks.id_for_name('Midterms::Other subject'))
        self.assertFalse(any(d['name']=='Lesson 3' for d in self.receiver.decks.all()))
        cid=self.matching(third).cards()[0].id;did=self.receiver.get_card(cid).did
        self.receiver.sched.set_due_date([cid],'9');before=self.state(cid)
        self.send([self.sender.decks.id('Midterms::Science')],settings=False)
        result=self.merge('parent-later')
        self.assertEqual(result['new_cards'],2);self.assertEqual(len(self.receiver.find_cards('')),3)
        self.assertEqual(self.matching(third).cards()[0].id,cid);self.assertEqual(self.receiver.get_card(cid).did,did);self.assertEqual(self.state(cid),before)
        expected={'Midterms','Midterms::Science',*[f'Midterms::Science::Lesson {i}' for i in (1,2,3)]}
        self.assertEqual({d['name'] for d in self.receiver.decks.all() if d['name']!='Default'},expected)
        self.merge('repeat-parent');self.assertEqual(len(self.receiver.find_cards('')),3);self.assertEqual(self.state(cid),before)
        self.assertEqual(self.sender.db.all('SELECT * FROM cards'),source)
    def test_existing_parents_lessons_and_added_siblings_are_reused_without_reset(self):
        self.receiver.decks.id('Midterms::Science::Lesson 1')
        other=self.receiver.decks.id('Midterms::Other subject')
        unrelated=self.receiver.new_note(self.receiver.models.by_name('Basic'));unrelated.fields[:]=['Her own note','Keep'];self.receiver.add_note(unrelated,other)
        self.send(settings=False);self.merge('first')
        cid=self.matching(self.note).cards()[0].id;self.receiver.sched.set_due_date([cid],'12')
        c=self.receiver.get_card(cid);c.reps=10;c.lapses=3;self.receiver.update_card(c);before=self.state(cid)
        self.note['Back']='Updated chambers';self.sender.update_note(self.note)
        self.add('Another question','Answer')
        self.did=self.sender.decks.id('Midterms::Science::Lesson 2');self.add('New lesson','New answer')
        source=self.sender.db.all('SELECT * FROM cards');self.send(settings=False);self.assertEqual(self.sender.db.all('SELECT * FROM cards'),source)
        result=self.merge('second')
        self.assertEqual(result['new_cards'],2);self.assertEqual(len(self.receiver.find_cards('')),4)
        self.assertEqual(self.state(cid),before);self.assertEqual(self.receiver.get_card(cid).note()['Back'],'Updated chambers')
        self.assertEqual(self.receiver.get_card(cid).did,self.receiver.decks.id_for_name('Midterms::Science::Lesson 1'))
        self.assertTrue(self.receiver.decks.id_for_name('Midterms::Science::Lesson 2'))
        self.assertFalse(any(d['name'].startswith(('From ','Shared::')) for d in self.receiver.decks.all()))
        self.assertEqual(self.receiver.get_card(unrelated.cards()[0].id).did,other)
        self.merge('third');self.assertEqual(len(self.receiver.find_cards('')),4);self.assertEqual(self.state(cid),before)
    def test_previous_received_folder_is_repaired_on_resend(self):
        self.send(settings=False)
        T.apply_bundle(self.receiver,self.rs,self.path,{'destination':'From partner','settings':False},'old')
        cid=self.matching(self.note).cards()[0].id;self.receiver.sched.set_due_date([cid],'9');before=self.state(cid)
        self.receiver.decks.id('Midterms::Science::Lesson 1');self.add('Second','Answer');self.send(settings=False)
        result=self.merge('repair')
        self.assertEqual(self.state(cid),before);self.assertEqual(len(self.receiver.find_cards('')),2)
        self.assertEqual(self.receiver.get_card(cid).did,self.receiver.decks.id_for_name('Midterms::Science::Lesson 1'))
        self.assertFalse(self.receiver.decks.id_for_name('From partner'));self.assertGreater(result['removed_empty_decks'],0)
        self.assertEqual(result['moved_cards'],1)
    def test_cleanup_never_deletes_other_cards_or_unrelated_branches(self):
        self.send(settings=False);T.apply_bundle(self.receiver,self.rs,self.path,{'destination':'From partner'},'old')
        keep=self.receiver.decks.id('From partner::Keep this')
        n=self.receiver.new_note(self.receiver.models.by_name('Basic'));n.fields[:]=['Unrelated','Keep'];self.receiver.add_note(n,keep)
        before=self.receiver.db.all('SELECT * FROM cards WHERE nid=?',n.id)
        self.merge('repair')
        self.assertTrue(self.receiver.decks.id_for_name('From partner'));self.assertTrue(self.receiver.decks.id_for_name('From partner::Keep this'))
        self.assertEqual(self.receiver.db.all('SELECT * FROM cards WHERE nid=?',n.id),before)
        self.assertFalse(self.receiver.decks.id_for_name('From partner::Midterms::Science::Lesson 1'))
    def test_partial_resends_remember_old_folder_until_other_lessons_are_merged(self):
        one=self.did;self.did=self.sender.decks.id('Midterms::Science::Lesson 2');two=self.did;self.add('Second lesson','Answer')
        self.send(settings=False);T.apply_bundle(self.receiver,self.rs,self.path,{'destination':'From partner'},'old')
        self.send([one],settings=False);self.merge('one')
        self.assertTrue(self.receiver.decks.id_for_name('From partner::Midterms::Science::Lesson 2'))
        self.send([two],settings=False);self.merge('two')
        self.assertFalse(self.receiver.decks.id_for_name('From partner'));self.assertEqual(len(self.receiver.find_cards('')),2)
    def test_previously_received_lesson_dragged_elsewhere_is_consolidated_on_resend(self):
        self.send(settings=False);T.apply_bundle(self.receiver,self.rs,self.path,{'destination':'From partner'},'old')
        cid=self.matching(self.note).cards()[0].id
        moved=self.receiver.decks.id('Midterms::Science duplicate::Lesson 1');self.receiver.set_deck([cid],moved)
        self.receiver.sched.set_due_date([cid],'9');before=self.state(cid)
        self.receiver.decks.id('Midterms::Science::Lesson 1');self.merge('repair')
        self.assertEqual(self.state(cid),before)
        self.assertEqual(self.receiver.get_card(cid).did,self.receiver.decks.id_for_name('Midterms::Science::Lesson 1'))
        self.assertFalse(self.receiver.decks.id_for_name('Midterms::Science duplicate'))
    def test_matching_local_edit_is_kept_until_explicitly_replaced(self):
        self.send(settings=False);self.merge('first');n=self.matching(self.note);n['Back']='Her edit';self.receiver.update_note(n)
        self.note['Back']='His edit';self.sender.update_note(self.note);self.send(settings=False)
        self.merge('keep');self.assertEqual(self.matching(self.note)['Back'],'Her edit')
        self.merge('replace',replace_conflicts=True);self.assertEqual(self.matching(self.note)['Back'],'His edit')
    def test_separate_folder_remains_an_explicit_option_and_choice_is_remembered(self):
        self.send(settings=False);self.assertTrue(T.preview(self.receiver,self.rs,self.path)['merge'])
        T.apply_bundle(self.receiver,self.rs,self.path,{'merge':False,'destination':'Separate'},'separate')
        self.assertFalse(T.preview(self.receiver,self.rs,self.path)['merge']);self.assertTrue(self.receiver.decks.id_for_name('Separate::Midterms::Science::Lesson 1'))
        self.merge('now-merge');self.assertTrue(T.preview(self.receiver,self.rs,self.path)['merge'])
    def test_filtered_type_collision_is_rejected_before_any_receiver_changes(self):
        f=self.receiver.decks.new_deck_legacy(True);f['name']='Midterms';self.receiver.decks.add_deck_legacy(f)
        self.send(settings=False);before=self.receiver.db.all('SELECT * FROM cards')
        with self.assertRaisesRegex(ValueError,'different deck type'):self.merge()
        self.assertEqual(self.receiver.db.all('SELECT * FROM cards'),before)
    def test_same_leaf_name_under_other_subject_is_not_merged(self):
        other=self.receiver.decks.id('Midterms::Other::Lesson 1');self.send(settings=False);self.merge()
        self.assertNotEqual(self.matching(self.note).cards()[0].did,other)
    def test_case_variant_old_folder_cannot_cause_unrelated_descendants_to_be_deleted(self):
        self.send(settings=False);T.apply_bundle(self.receiver,self.rs,self.path,{'destination':'From partner'},'old')
        keep=self.receiver.decks.id('From partner::Her other subject')
        n=self.receiver.new_note(self.receiver.models.by_name('Basic'));n.fields[:]=['Keep','Keep'];self.receiver.add_note(n,keep)
        before=self.receiver.db.all('SELECT * FROM cards WHERE nid=?',n.id)
        self.rs.data['destinations'][self.ss.data['identity']]='from PARTNER'
        self.merge('repair')
        self.assertEqual(self.receiver.db.all('SELECT * FROM cards WHERE nid=?',n.id),before)
        self.assertTrue(self.receiver.decks.id_for_name('From partner::Her other subject'))
    def test_filtered_received_branch_can_be_merged_and_rebuilt_without_duplicates(self):
        f=self.sender.sched.get_or_create_filtered_deck(0);f.name='Practice::Science::Round 1';f.config.reschedule=False
        del f.config.search_terms[1:];f.config.search_terms[0].search='deck:Midterms';f.config.search_terms[0].limit=100
        fid=self.sender.sched.add_or_update_filtered_deck(f).id;self.sender.sched.rebuild_filtered_deck(fid)
        self.send([fid],settings=True)
        T.apply_bundle(self.receiver,self.rs,self.path,{'destination':'From partner','settings':True},'old')
        result=self.merge('merged',settings=True)
        target=self.receiver.decks.id_for_name('Practice::Science::Round 1')
        self.assertTrue(target);self.assertFalse(self.receiver.decks.get(target)['resched'])
        self.assertEqual(result['filtered'][0]['built'],1);self.assertEqual(len(self.receiver.find_cards('')),1)
        self.assertFalse(self.receiver.decks.id_for_name('From partner'))
        card=self.matching(self.note).cards()[0];self.assertEqual(card.did,target)
        self.assertEqual(card.odid,self.receiver.decks.id_for_name('Midterms::Science::Lesson 1'))
    def test_existing_unrelated_filtered_round_keeps_its_progress_and_membership(self):
        self.send(settings=False);self.merge('first');cid=self.matching(self.note).cards()[0].id
        f=self.receiver.sched.get_or_create_filtered_deck(0);f.name='Her practice';f.config.reschedule=False
        del f.config.search_terms[1:];f.config.search_terms[0].search='cid:'+str(cid);fid=self.receiver.sched.add_or_update_filtered_deck(f).id
        self.receiver.sched.rebuild_filtered_deck(fid);before=self.state(cid)
        self.merge('again');self.assertEqual(self.state(cid),before);self.assertEqual(self.receiver.get_card(cid).did,fid)
    def test_old_wrapped_home_moves_without_removing_a_card_from_her_own_filter(self):
        self.send(settings=False);T.apply_bundle(self.receiver,self.rs,self.path,{'destination':'From partner'},'old')
        cid=self.matching(self.note).cards()[0].id
        f=self.receiver.sched.get_or_create_filtered_deck(0);f.name='Her practice';f.config.reschedule=False
        del f.config.search_terms[1:];f.config.search_terms[0].search='cid:'+str(cid);fid=self.receiver.sched.add_or_update_filtered_deck(f).id
        self.receiver.sched.rebuild_filtered_deck(fid);before=self.state(cid)
        self.merge('repair');card=self.receiver.get_card(cid)
        self.assertEqual(self.state(cid),before);self.assertEqual(card.did,fid)
        self.assertEqual(card.odid,self.receiver.decks.id_for_name('Midterms::Science::Lesson 1'))
        self.assertFalse(self.receiver.decks.id_for_name('From partner'))
    def test_card_from_manual_apkg_import_is_reused_by_identity_on_resend(self):
        from anki.collection import ExportAnkiPackageOptions,CardIdsLimit,ImportAnkiPackageRequest,ImportAnkiPackageOptions
        apkg=self.root/'manual.apkg'
        self.sender.export_anki_package(out_path=str(apkg),options=ExportAnkiPackageOptions(with_scheduling=False,with_deck_configs=False,with_media=False,legacy=True),limit=CardIdsLimit(card_ids=self.sender.find_cards('')))
        self.receiver.import_anki_package(ImportAnkiPackageRequest(package_path=str(apkg),options=ImportAnkiPackageOptions(merge_notetypes=True,with_scheduling=False,with_deck_configs=False)))
        cid=self.matching(self.note).cards()[0].id;self.receiver.sched.set_due_date([cid],'7');before=self.state(cid)
        self.add('New card','New answer');self.send(settings=False);self.merge('resend')
        self.assertEqual(len(self.receiver.find_cards('')),2);self.assertEqual(self.state(cid),before)
        self.assertEqual(self.matching(self.note).cards()[0].id,cid)
    def test_new_cloze_sibling_is_added_once_and_existing_cloze_keeps_progress(self):
        n=self.add('{{c1::one}} then {{c2::two}}','',kind='Cloze');self.send(settings=False);self.merge('first')
        cid=self.matching(n).cards()[0].id;self.receiver.sched.set_due_date([cid],'11');before=self.state(cid)
        n['Text']='{{c1::one}} then {{c2::two}} then {{c3::three}}';self.sender.update_note(n)
        self.send(settings=False);self.merge('second');self.merge('third')
        self.assertEqual(len(self.matching(n).cards()),3);self.assertEqual(self.state(cid),before)

if __name__=='__main__':unittest.main()
