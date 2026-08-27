#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import managed_builder as m
import resolve_lifecycle as life


def _retry_dir(mp,parent,source_dir,missing):
    if not missing:return 0
    b=m.getbin(mp,parent,source_dir.name)
    mp.SetCurrentFolder(b)
    imported=0
    for path in m.direct(source_dir):
        key=m.norm(path)
        if key not in missing:continue
        life.put(stage=f'Opakuji import: {path.name}')
        result=mp.ImportMedia([str(path)]) or []
        if result:
            imported+=1
            missing.discard(key)
            life.log('MEDIA_RETRY_OK',file=str(path))
        else:
            life.log('MEDIA_RETRY_FAILED',file=str(path))
    for child in sorted([x for x in source_dir.iterdir() if x.is_dir()],key=lambda p:p.name.casefold()):
        if any(m.norm(p) in missing for p in m.allfiles(child)):
            imported+=_retry_dir(mp,b,child,missing)
    return imported


def verify_and_retry(mp,master,dirs,expected):
    have=set();m.present(master,have)
    missing=set(expected)-have
    if not missing:return 0,[]
    life.log('MEDIA_VERIFY_MISSING',count=len(missing),files=[str(expected[x]) for x in sorted(missing)])
    retried=0
    for d in dirs:
        if any(m.norm(p) in missing for p in m.allfiles(d)):
            retried+=_retry_dir(mp,master,d,missing)
    have=set();m.present(master,have)
    remaining=set(expected)-have
    files=[str(expected[x]) for x in sorted(remaining)]
    life.log('MEDIA_VERIFY_DONE',retried=retried,remaining=len(files),files=files)
    return retried,files
