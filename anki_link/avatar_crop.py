"""Local square crop editor. Only its accepted 256px output can be uploaded."""
from pathlib import Path
import uuid
from aqt.qt import (QDialog,QDialogButtonBox,QVBoxLayout,QHBoxLayout,QWidget,QLabel,
                    QPushButton,QSlider,QImage,QPainter,QPen,QColor,QPointF,QRectF,QSize,Qt)

class CropCanvas(QWidget):
    def __init__(self,image,parent=None):
        super().__init__(parent);self.image=image;self.zoom=1.;self.center=QPointF(image.width()/2,image.height()/2);self.drag=None;self.zoom_changed=None
        self.setMinimumSize(280,280);self.setFocusPolicy(Qt.FocusPolicy.StrongFocus);self.setCursor(Qt.CursorShape.OpenHandCursor);self.setAccessibleName('Picture crop. Drag to reposition; use the zoom slider to resize.')
    def sizeHint(self):return QSize(360,360)
    def frame(self):
        edge=max(1,min(self.width(),self.height())-16)
        return QRectF((self.width()-edge)/2,(self.height()-edge)/2,edge,edge)
    def source_rect(self):
        span=min(self.image.width(),self.image.height())/self.zoom;half=span/2
        x=max(half,min(self.image.width()-half,self.center.x()));y=max(half,min(self.image.height()-half,self.center.y()));self.center=QPointF(x,y)
        return QRectF(x-half,y-half,span,span)
    def set_zoom(self,value):
        self.zoom=max(1.,min(4.,float(value)));self.source_rect();self.update()
        if self.zoom_changed:self.zoom_changed(self.zoom)
    def reset(self):self.center=QPointF(self.image.width()/2,self.image.height()/2);self.set_zoom(1)
    def move_crop(self,dx,dy):
        scale=self.source_rect().width()/self.frame().width();self.center-=QPointF(dx*scale,dy*scale);self.source_rect();self.update()
    def paintEvent(self,event):
        painter=QPainter(self);painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform);frame=self.frame()
        painter.fillRect(frame,self.palette().alternateBase());painter.drawImage(frame,self.image,self.source_rect())
        painter.setPen(QPen(QColor(255,255,255,65),1))
        for index in (1,2):
            x=frame.left()+frame.width()*index/3;y=frame.top()+frame.height()*index/3
            painter.drawLine(QPointF(x,frame.top()),QPointF(x,frame.bottom()));painter.drawLine(QPointF(frame.left(),y),QPointF(frame.right(),y))
        painter.setPen(QPen(self.palette().mid().color(),1));painter.drawRect(frame);painter.end()
    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton and self.frame().contains(event.position()):self.drag=event.position();self.setCursor(Qt.CursorShape.ClosedHandCursor);self.setFocus();event.accept()
        else:super().mousePressEvent(event)
    def mouseMoveEvent(self,event):
        if self.drag is not None:
            delta=event.position()-self.drag;self.drag=event.position();self.move_crop(delta.x(),delta.y());event.accept()
        else:super().mouseMoveEvent(event)
    def mouseReleaseEvent(self,event):
        if self.drag is not None:self.drag=None;self.setCursor(Qt.CursorShape.OpenHandCursor);event.accept()
        else:super().mouseReleaseEvent(event)
    def wheelEvent(self,event):
        delta=event.angleDelta().y()
        if delta:self.set_zoom(self.zoom*(1.12 if delta>0 else 1/1.12))
        event.accept()
    def keyPressEvent(self,event):
        arrows={Qt.Key.Key_Left:(12,0),Qt.Key.Key_Right:(-12,0),Qt.Key.Key_Up:(0,12),Qt.Key.Key_Down:(0,-12)}
        if event.key() in arrows:self.move_crop(*arrows[event.key()]);event.accept()
        elif event.key()==Qt.Key.Key_Home:self.reset();event.accept()
        else:super().keyPressEvent(event)
    def cropped_image(self):
        out=QImage(256,256,QImage.Format.Format_ARGB32_Premultiplied);out.fill(Qt.GlobalColor.transparent)
        painter=QPainter(out);painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform);painter.drawImage(QRectF(0,0,256,256),self.image,self.source_rect());painter.end();return out

class CropDialog(QDialog):
    def __init__(self,parent,image,title='Crop profile picture'):
        super().__init__(parent);self.setWindowTitle(title);self.resize(440,510)
        layout=QVBoxLayout(self);layout.setContentsMargins(20,16,20,18);layout.setSpacing(14)
        self.canvas=CropCanvas(image,self);layout.addWidget(self.canvas,1)
        row=QHBoxLayout();row.setSpacing(12);row.addWidget(QLabel('Zoom'))
        self.slider=QSlider(Qt.Orientation.Horizontal);self.slider.setRange(100,400);self.slider.setValue(100);self.slider.setAccessibleName('Crop zoom');row.addWidget(self.slider,1)
        self.value=QLabel('100%');self.value.setMinimumWidth(42);row.addWidget(self.value);layout.addLayout(row)
        self.slider.valueChanged.connect(lambda value:self.canvas.set_zoom(value/100))
        def zoom_changed(value):
            self.slider.blockSignals(True);self.slider.setValue(round(value*100));self.slider.blockSignals(False);self.value.setText(str(round(value*100))+'%')
        self.canvas.zoom_changed=zoom_changed
        footer=QHBoxLayout();reset=QPushButton('Reset');reset.clicked.connect(self.canvas.reset);footer.addWidget(reset);footer.addStretch()
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok);buttons.button(QDialogButtonBox.StandardButton.Ok).setText('Use picture');buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);footer.addWidget(buttons);layout.addLayout(footer)

def crop_avatar(parent,path,directory,title='Crop profile picture'):
    image=QImage(str(path))
    if image.isNull():raise ValueError('The picture could not be opened for cropping.')
    dialog=CropDialog(parent,image,title)
    if dialog.exec()!=QDialog.DialogCode.Accepted:return None
    target=Path(directory)/(uuid.uuid4().hex+'.png')
    if not dialog.canvas.cropped_image().save(str(target),'PNG'):raise ValueError('The cropped picture could not be saved.')
    return target
