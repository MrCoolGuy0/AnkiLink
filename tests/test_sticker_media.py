"""Actual Qt static/animated sticker preparation and own-account cache."""
import hashlib
import importlib
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
import test_message_controller as controller
D=controller.D

M=importlib.import_module('anki_link.media')
try:
    from PyQt6.QtGui import QImage,QImageReader
    from PyQt6.QtCore import Qt
except ImportError:QImage=None

@unittest.skipUnless(QImage,'Install PyQt6 privately for actual image codec checks')
class StickerMedia(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.qt=types.ModuleType('aqt.qt');self.qt.QImageReader=QImageReader;self.qt.Qt=Qt
    def test_static_sticker_becomes_small_keeps_transparency_and_original_is_unchanged(self):
        source=self.root/'large.png';image=QImage(1600,1000,QImage.Format.Format_ARGB32);image.fill(0x80AA33BB);image.save(str(source))
        original=source.read_bytes()
        with patch.dict('sys.modules',{'aqt.qt':self.qt}):prepared=M.prepare_sticker(source,self.root)
        got=QImage(str(prepared));self.assertEqual((got.width(),got.height()),(512,320));self.assertTrue(got.hasAlphaChannel())
        self.assertLess(prepared.stat().st_size,source.stat().st_size);self.assertEqual(source.read_bytes(),original)
    def test_profile_picture_is_small_and_source_is_unchanged(self):
        source=self.root/'avatar.png';image=QImage(1200,800,QImage.Format.Format_ARGB32);image.fill(0xFF8844AA);image.save(str(source));original=source.read_bytes()
        with patch.dict('sys.modules',{'aqt.qt':self.qt}):prepared=M.prepare_avatar(source,self.root)
        got=QImage(str(prepared));self.assertEqual(got.width(),256);self.assertAlmostEqual(got.width()/got.height(),1.5,delta=.01);self.assertEqual(source.read_bytes(),original);self.assertLess(prepared.stat().st_size,2*1024*1024)
    def test_animated_gif_bytes_and_frames_are_retained(self):
        source=self.root/'animated.gif'
        source.write_bytes(bytes.fromhex('47494638396101000100800000ff00000000ff21f904000a0000002c000000000100010000020244010021f904000a0000002c00000000010001000002024c01003b'))
        self.assertEqual(QImageReader(str(source)).imageCount(),2)
        with patch.dict('sys.modules',{'aqt.qt':self.qt}):self.assertEqual(M.prepare_sticker(source,self.root),source)
    def test_cache_is_hash_checked_and_separated_by_account_and_server(self):
        raw=b'image bytes';meta={'id':'one','sha256':hashlib.sha256(raw).hexdigest()}
        path=M.cache_path(self.root,'https://one.test','me',meta);M.cache_image(path,raw,meta)
        self.assertEqual(M.cached_image(path,meta),raw)
        self.assertNotEqual(path,M.cache_path(self.root,'https://two.test','me',meta))
        self.assertNotEqual(path,M.cache_path(self.root,'https://one.test','other',meta))
        path.write_bytes(b'corrupt');self.assertIsNone(M.cached_image(path,meta))

@unittest.skipUnless(QImage,'Install PyQt6 privately for sticker controller checks')
class StickerPipeline(unittest.TestCase):
    setUp=controller.MessageController.setUp
    finish=controller.MessageController.finish
    def test_creation_emits_local_preview_and_confirmed_bubble_without_self_download(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);source=root/'picture.png';image=QImage(1800,1200,QImage.Format.Format_ARGB32);image.fill(0xFFFF00FF);image.save(str(source))
            c=self.c;c.temp=types.SimpleNamespace(name=td);c.social={'user':{'id':'me','name':'Me'}};c.blobs=set()
            c.store.folder=root;c.store.data['url']='https://server.test';c.store.save=lambda:None
            requests=[];holder={}
            def request(path,raw,mime,name):
                requests.append(path);holder['raw']=raw
                meta={'id':'sticker','mime':mime,'name':name,'sha256':hashlib.sha256(raw).hexdigest(),'size':len(raw)};holder['meta']=meta;return meta
            client=c.client();client.request=request
            reader=QImageReader;dialog=types.SimpleNamespace(getOpenFileName=lambda *args:(str(source),''))
            qt=types.ModuleType('aqt.qt');qt.QImageReader=reader;qt.Qt=Qt
            with patch.object(D,'QFileDialog',dialog),patch.object(D,'QImageReader',reader),patch.dict('sys.modules',{'aqt.qt':qt}):
                c.send_image({'thread':'chat','sticker':True,'nonce':'sticker-nonce'});self.finish(0)
                self.assertEqual(self.events[-1][0],'attachment_pending');self.assertEqual(requests,[])
                self.finish(1);self.finish(2)
            self.assertEqual(requests,['/v1/upload']);self.assertEqual(self.events[-2][0],'blob');self.assertEqual(self.events[-1][0],'sent')
            self.assertEqual(self.events[-1][1]['id'],42);self.assertEqual(len(self.jobs),3,'prepare/upload/send are independent; no self-download or refresh')
            path=M.cache_path(root,'https://server.test','me',holder['meta']);self.assertEqual(M.cached_image(path,holder['meta']),holder['raw'])
            c.blobs.clear();c.preparing=set();client.download=lambda meta:self.fail('cached own sticker must not download again')
            c.blob(holder['meta']);self.finish(3);self.assertEqual(self.events[-1][0],'blob')

if __name__=='__main__':unittest.main()
