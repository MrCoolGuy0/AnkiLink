"""Real Qt crop geometry and preview, with synthetic pixels and no uploads."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PyQt6 import QtCore,QtGui,QtWidgets
qt=types.ModuleType('aqt.qt')
for module in (QtCore,QtGui,QtWidgets):
    for name in dir(module):
        if not name.startswith('_'):setattr(qt,name,getattr(module,name))
spec=importlib.util.spec_from_file_location('avatar_crop_test',Path(__file__).resolve().parents[1]/'anki_link/avatar_crop.py');C=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'aqt.qt':qt}):spec.loader.exec_module(C)
class CropTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    def image(self):
        image=QtGui.QImage(600,300,QtGui.QImage.Format.Format_ARGB32);image.fill(QtGui.QColor('red'));p=QtGui.QPainter(image);p.fillRect(300,0,300,300,QtGui.QColor('blue'));p.end();return image
    def test_drag_and_zoom_change_crop_inside_fixed_frame(self):
        image=self.image();canvas=C.CropCanvas(image);canvas.resize(360,360);frame=canvas.frame();before=canvas.source_rect();canvas.set_zoom(2);canvas.move_crop(-100,0)
        self.assertEqual(canvas.frame(),frame);self.assertLess(canvas.source_rect().width(),before.width());self.assertEqual(canvas.cropped_image().size(),QtCore.QSize(256,256));self.assertEqual(canvas.cropped_image().pixelColor(128,128),QtGui.QColor('blue'))
        for dx in (-100000,100000):
            canvas.move_crop(dx,dx);r=canvas.source_rect();self.assertGreaterEqual(r.left(),0);self.assertGreaterEqual(r.top(),0);self.assertLessEqual(r.right(),image.width());self.assertLessEqual(r.bottom(),image.height())
        canvas.reset();self.assertEqual(canvas.source_rect(),before)
    def test_cancel_returns_no_file_and_accept_outputs_square_without_modifying_source(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'original.png';self.image().save(str(path));before=path.read_bytes()
            with patch.object(C.CropDialog,'exec',return_value=QtWidgets.QDialog.DialogCode.Rejected):self.assertIsNone(C.crop_avatar(None,path,td))
            self.assertEqual(list(Path(td).iterdir()),[path])
            with patch.object(C.CropDialog,'exec',return_value=QtWidgets.QDialog.DialogCode.Accepted):out=C.crop_avatar(None,path,td)
            self.assertEqual(QtGui.QImage(str(out)).size(),QtCore.QSize(256,256));self.assertEqual(path.read_bytes(),before)
    def test_actual_dialog_controls_keep_zoom_and_reset_in_sync(self):
        dialog=C.CropDialog(None,self.image());dialog.slider.setValue(250);self.assertEqual(dialog.canvas.zoom,2.5);self.assertEqual(dialog.value.text(),'250%');dialog.canvas.reset();self.assertEqual(dialog.slider.value(),100)
        dialog.show();QtWidgets.QApplication.processEvents();self.assertFalse(dialog.grab().isNull());dialog.close()
if __name__=='__main__':unittest.main()
