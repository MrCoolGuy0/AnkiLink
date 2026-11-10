"""Sticker-sized static uploads and account-scoped own-sticker cache."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import uuid

def prepare_avatar(path,directory,edge=256):
    from aqt.qt import QImageReader,Qt
    reader=QImageReader(str(path));reader.setAutoTransform(True);size=reader.size()
    if size.isValid():reader.setScaledSize(size.scaled(edge,edge,Qt.AspectRatioMode.KeepAspectRatio))
    image=reader.read()
    if image.isNull():raise ValueError('The profile image could not be read.')
    image=image.scaled(edge,edge,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)
    for extension,format_ in (('webp','WEBP'),('png','PNG')):
        target=Path(directory)/(uuid.uuid4().hex+'.'+extension)
        if image.save(str(target),format_,90) and target.stat().st_size<=2*1024*1024:return target
        target.unlink(missing_ok=True)
    raise ValueError('The profile image could not be prepared.')

def prepare_sticker(path,directory):
    from aqt.qt import QImageReader,Qt
    path=Path(path);reader=QImageReader(str(path));reader.setAutoTransform(True)
    # Preserve animated GIF/WebP/APNG bytes and frame timing.
    if reader.supportsAnimation() and reader.imageCount()!=1:return path
    size=reader.size()
    if size.isValid() and max(size.width(),size.height())>512:
        reader.setScaledSize(size.scaled(512,512,Qt.AspectRatioMode.KeepAspectRatio))
    image=reader.read()
    if image.isNull():raise ValueError('The sticker image could not be read.')
    if max(image.width(),image.height())>512:image=image.scaled(512,512,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)
    for extension,format_,quality in (('webp','WEBP',90),('png','PNG',-1)):
        target=Path(directory)/(uuid.uuid4().hex+'.'+extension)
        if image.save(str(target),format_,quality):
            if max(size.width(),size.height())<=512 and target.stat().st_size>=path.stat().st_size:
                target.unlink();return path
            return target
        target.unlink(missing_ok=True)
    raise ValueError('The sticker image could not be prepared.')

def cache_path(folder,url,user_id,meta):
    key=hashlib.sha256(json.dumps([url,user_id,meta['id'],meta['sha256']]).encode()).hexdigest()
    return Path(folder)/'sticker-cache'/key

def cached_image(path,meta):
    try:
        with Path(path).open('rb') as stream:raw=stream.read(12*1024*1024+1)
        if len(raw)<=12*1024*1024 and hashlib.sha256(raw).hexdigest()==meta['sha256']:return raw
    except OSError:pass
    return None

def cache_image(path,raw,meta):
    if len(raw)>12*1024*1024 or hashlib.sha256(raw).hexdigest()!=meta['sha256']:return
    path=Path(path);temporary=path.with_name(path.name+'-'+uuid.uuid4().hex+'.tmp')
    try:
        path.parent.mkdir(exist_ok=True);temporary.write_bytes(raw);temporary.replace(path)
    except OSError:pass  # Optional cache must never fail an accepted send.
    finally:
        try:temporary.unlink(missing_ok=True)
        except OSError:pass
