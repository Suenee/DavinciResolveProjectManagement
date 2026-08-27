#!/usr/bin/env python3
from __future__ import annotations
import re,traceback
import managed_builder as m
import resolve_lifecycle as life
import timeline_audio
import intro_match_routing
import verified_import

_CREATOR=None

def set_timeline_creator(func):
 global _CREATOR;_CREATOR=func

def _timeline_names(project):
 out=[]
 for i in range(1,int(project.GetTimelineCount() or 0)+1):
  t=project.GetTimelineByIndex(i)
  if t is not None:out.append(t)
 return out

def _matching_timelines(project,base):
 pat=re.compile(r'^'+re.escape(base)+r'(?: \((\d+)\))?$',re.I)
 return [t for t in _timeline_names(project) if pat.match((t.GetName() or '').strip())]

def _unique_timeline_name(project,base):
 used={(t.GetName() or '').casefold() for t in _timeline_names(project)}
 if base.casefold() not in used:return base
 n=2
 while f'{base} ({n})'.casefold() in used:n+=1
 return f'{base} ({n})'

def _deliver_ready(project,src,folder):
 expected=m.norm((src/folder).resolve())
 try:
  if not hasattr(project,'GetRenderSettings'):return False
  settings=project.GetRenderSettings() or {};target=settings.get('TargetDir') or settings.get('targetDir') or ''
  return bool(target) and m.norm(target)==expected
 except Exception:return False

def _status(project,base,missing,src,deliver_folder,shoot):
 timelines=_matching_timelines(project,base);return {'missing':len(missing),'timeline':bool(timelines),'voice':any(timeline_audio.is_prepared(t) for t in timelines),'deliver':_deliver_ready(project,src,deliver_folder)}
def ask(project_name,status):raise RuntimeError('Update dialog was not initialized.')
def _stage(name):life.put(stage=name);life.log('WORKFLOW_STAGE',stage=name)
def _create_timeline(mp,master,shoot,name,voice,intro_reference=None):
 if _CREATOR is None:raise RuntimeError('Timeline creator není inicializován.')
 _stage('TIMELINE');timeline=_CREATOR(mp,master,shoot,name)
 if voice:_stage('VOICE_ISOLATION');timeline=timeline_audio.configure(timeline)
 if voice and intro_reference:_stage('INTRO_MATCH');timeline=intro_match_routing.apply(mp,timeline,intro_reference)
 return timeline

def _verify_media(mp,master,dirs,fs):
 _stage('MEDIA_VERIFY');retried,remaining=verified_import.verify_and_retry(mp,master,dirs,fs)
 if remaining:
  preview='\n'.join(remaining[:10]);more=f'\n... +{len(remaining)-10} dalších' if len(remaining)>10 else ''
  raise RuntimeError(f'DaVinci Resolve nepřijal {len(remaining)} mediálních souborů ani po opakovaném importu:\n{preview}{more}')
 if retried:print(f'[OK] Opakovaným importem doplněno médií: {retried}')

def build(query,keep):
 phase='INIT'
 root,folder,timeout,alive,deliver_preset,deliver_folder=m.cfg();src=m.resolve_project(root,query);name=src.name;life.begin_log_session('run',name);life.log('PROJECT_RESOLVED',query=query,name=name)
 shoot=next((x for x in src.iterdir() if x.is_dir() and x.name.casefold()=='shooting'),src/'SHOOTING')
 if not shoot.is_dir():raise RuntimeError(f'Chybí SHOOTING: {shoot}')
 dirs=[shoot]+[d for dn in m.OPTIONAL for d in src.iterdir() if d.is_dir() and d.name.casefold()==dn.casefold()];fs={m.norm(p):p for d in dirs for p in m.allfiles(d)}
 try:
  phase='RESOLVE_CONNECT';_stage(phase);r=m.ensure(name,timeout);life.put(busy=True,project=name,keep_mode=keep,alive_timeout=alive)
  phase='PROJECT_OPEN';_stage(phase);pm=r.GetProjectManager();pm.GotoRootFolder()
  if folder and not pm.OpenFolder(folder):raise RuntimeError(f'Project Library folder nenalezen: {folder}')
  projects=pm.GetProjectListInCurrentFolder() or [];existing=next((x for x in projects if x.casefold()==name.casefold()),None)
  if not existing:
   phase='PROJECT_CREATE';_stage(phase);pr=pm.CreateProject(name)
   if pr is None:raise RuntimeError(f'Nelze vytvořit projekt: {name}')
   mp=pr.GetMediaPool();master=mp.GetRootFolder();missing=set(fs);counter=[0]
   phase='MEDIA_IMPORT';_stage(phase);imported=sum(m.sync(mp,master,d,missing,counter,len(missing)) for d in dirs)
   phase='MEDIA_VERIFY';_verify_media(mp,master,dirs,fs)
   tn=m.nodate(name) or name;phase='TIMELINE';_create_timeline(mp,master,shoot,tn,True)
   phase='DELIVERY';_stage(phase);m.apply_deliver(pr,src,deliver_preset,deliver_folder)
   phase='SAVE';_stage(phase)
   if not pm.SaveProject():raise RuntimeError('SaveProject() selhal.')
   life.log('PROJECT_CREATED',name=name,imported=imported,timeline=tn);print(f'[OK] Projekt vytvořen: {name} | Timeline: {tn} | Média: {imported}')
  else:
   phase='PROJECT_LOAD';_stage(phase);pr=pm.LoadProject(existing)
   if pr is None:raise RuntimeError(f'Existující projekt nelze otevřít: {existing}')
   mp=pr.GetMediaPool();master=mp.GetRootFolder();have=set();m.present(master,have);missing=set(fs)-have;base=m.nodate(name) or name;st=_status(pr,base,missing,src,deliver_folder,shoot);life.log('PROJECT_EXISTS',name=existing,**st)
   actions=ask(existing,st)
   if actions is None:print('[OK] Aktualizace projektu zrušena.');return m.finish(r,keep,alive)
   changed=False
   if actions['repository']:
    if missing:
     phase='MEDIA_IMPORT';_stage(phase);counter=[0];imported=sum(m.sync(mp,master,d,missing,counter,len(missing)) for d in dirs if any(m.norm(p) in missing for p in m.allfiles(d)));_verify_media(mp,master,dirs,fs);life.log('SYNC_DONE',imported=imported);print(f'[OK] Doplněno médií: {imported}');changed=True
    else:print('[OK] Repozitář je aktuální.')
   if actions['timeline']:
    tn=_unique_timeline_name(pr,base);phase='TIMELINE';_create_timeline(mp,master,shoot,tn,actions['voice'],actions.get('intro_reference'));life.log('TIMELINE_UPDATE_CREATED',timeline=tn,voice=actions['voice'],intro_reference=actions.get('intro_reference'));print(f'[OK] Vytvořena timeline: {tn}');changed=True
   if actions['deliver']:
    phase='DELIVERY';_stage(phase);m.apply_deliver(pr,src,deliver_preset,deliver_folder);changed=True
   if changed:
    phase='SAVE';_stage(phase)
    if not pm.SaveProject():raise RuntimeError('SaveProject() selhal.')
   else:print('[OK] Nebyla vybrána žádná změna.')
  phase='COMPLETE';_stage(phase)
 except Exception as exc:
  life.log('WORKFLOW_ERROR',phase=phase,error=repr(exc),traceback=traceback.format_exc())
  raise
 finally:
  life.put(busy=False,stage='Hotovo')
 if 'r' in locals():m.finish(r,keep,alive)
