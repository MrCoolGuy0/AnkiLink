"""Windows-style SQLite handle locks, using real SQLite and native Anki exports.

Linux permits unlinking an open SQLite file. Reject that cleanup explicitly so
the regression also fails on non-Windows hosts instead of relying on GC timing.
"""
from contextlib import contextmanager, closing
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import test_transfer as native
T=native.T

@contextmanager
def windows_database_locks():
    connect=T.sqlite3.connect;temporary=T.tempfile.TemporaryDirectory;handles=[]
    class Connection(sqlite3.Connection):
        closed=False
        def close(self):
            try:super().close()
            finally:self.closed=True
    def tracked(database,*args,**kwargs):
        kwargs['factory']=Connection
        db=connect(database,*args,**kwargs);handles.append((Path(database).resolve(),db));return db
    class Directory(temporary):
        def cleanup(self):
            for path,db in handles:
                if path.is_relative_to(Path(self.name).resolve()) and not db.closed:
                    raise PermissionError(32,'Temporary database is still open',str(path))
            super().cleanup()
    try:
        with patch.object(T.sqlite3,'connect',tracked),patch.object(T.tempfile,'TemporaryDirectory',Directory):
            yield handles
    finally:
        for _,db in handles:db.close()

class ReadBundleLocks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
    def bundle(self,invalid=False):
        database=self.root/'fixture.sqlite'
        with closing(sqlite3.connect(database)) as db,db:
            db.executescript('CREATE TABLE notes(id INTEGER,guid TEXT,flds TEXT);CREATE TABLE cards(nid INTEGER,ord INTEGER);')
            db.execute('INSERT INTO notes VALUES(1,?,?)',('note-guid','Question\x1fAnswer'))
            db.execute('INSERT INTO cards VALUES(1,0)')
        apkg=self.root/'fixture.apkg'
        with ZipFile(apkg,'w') as z:z.write(database,'collection.anki21')
        raw=apkg.read_bytes()
        manifest={'format':1,'source':'a'*32,'cards':[{'key':'note-guid#0','home':'Deck'}],'decks':[{'name':'Deck'}],
                  'notes':{'note-guid':{'fields':['Question','Invalid' if invalid else 'Answer']}},
                  'package_sha256':hashlib.sha256(raw).hexdigest()}
        path=self.root/'fixture.alink'
        with ZipFile(path,'w') as z:
            z.writestr('manifest.json',json.dumps(manifest));z.writestr('decks.apkg',raw)
        return path
    def test_valid_preview_closes_database_before_cleanup(self):
        path=self.bundle()
        with windows_database_locks() as handles:
            manifest,_=T.read_bundle(path)
            self.assertEqual(manifest['source'],'a'*32)
            self.assertEqual(len(handles),1);self.assertTrue(all(db.closed for _,db in handles))
    def test_invalid_preview_closes_database_without_masking_original_error(self):
        path=self.bundle(invalid=True)
        with windows_database_locks() as handles:
            with self.assertRaisesRegex(ValueError,'notes do not match'):T.read_bundle(path)
            self.assertTrue(all(db.closed for _,db in handles))

@unittest.skipUnless(native.Collection,'Install anki in a private test environment for native export checks')
class NativeWindowsLocks(unittest.TestCase):
    # Reuse only fixture helpers, without duplicating its nine unrelated tests.
    setUp=native.NativeTransfers.setUp
    add=native.NativeTransfers.add
    send=native.NativeTransfers.send
    def test_windows_send_preview_accept_repeatedly_release_temporary_databases(self):
        before=self.sender.db.all('SELECT * FROM cards')
        with windows_database_locks() as handles:
            for i,(settings,progress) in enumerate(((True,False),(False,False),(True,True))):
                self.send(settings=settings,progress=progress)
                T.preview(self.receiver,self.rs,self.path)
                T.apply_bundle(self.receiver,self.rs,self.path,
                    {'destination':'From partner','settings':settings,'progress':progress,'build_filters':True},'windows-'+str(i))
                self.assertEqual(self.sender.db.all('SELECT * FROM cards'),before)
                self.assertEqual(len(self.receiver.find_cards('')),1)
                self.assertTrue(all(db.closed for _,db in handles))
            self.assertGreaterEqual(len(handles),12)

if __name__=='__main__':unittest.main()
