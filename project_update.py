#!/usr/bin/env python3
from __future__ import annotations
import re,traceback,time,threading
import managed_builder as m
import resolve_lifecycle as life
import timeline_audio
import intro_match_routing
import verified_import
import timeline_assets
import silence_trim
import project_profiles
from i18n import _
from project_paths import first_available_named_path

_CREATOR=None
_INTRO_SELECTOR=None
_TITLE_SELECTOR=None
_SILENCE_SELECTOR=None

def set_timeline_creator(func):
 global _CREATOR;_CREATOR=func
def set_intro_selector(func):
 global _INTRO_SELECTOR;_INTRO_SELECTOR=func
def set_title_selector(func):
 global _TITLE_SELECTOR;_TITLE_SELECTOR=func
def set_silence_selector(func):
 global _SILENCE_SELECTOR;_SILENCE_SELECTOR=func

def _diagnosed_api_call(label,func,**context):
 """Log elapsed time independently while a native Resolve API call may block."""
 started=time.monotonic();done=threading.Event()
 life.log(label+'_CALL',**context)
 def heartbeat():
  # Dense early samples make project-creation races visible; then back off.
  checkpoints=(1,2,5,10,20,30,60,120,300)
  previous=0
  for checkpoint in checkpoints:
   if done.wait(max(0,checkpoint-previous)):return
   previous=checkpoint
   life.log(label+'_WAIT',elapsed_seconds=round(time.monotonic()-started,3),**context)
  while not done.wait(300):
   life.log(label+'_WAIT',elapsed_seconds=round(time.monotonic()-started,3),**context)
 t=threading.Thread(target=heartbeat,name='ResolveApiDiagnostic-'+label,daemon=True);t.start()
 try:
  result=func()
  life.log(label+'_RETURN',elapsed_seconds=round(time.monotonic()-started,3),returned=result is not None,**context)
  return result
 except Exception as exc:
  life.log(label+'_ERROR',elapsed_seconds=round(time.monotonic()-started,3),error=repr(exc),**context)
  raise
 finally:done.set()

def _intro_root():
 p=m.configparser.ConfigParser(interpolation=None);p.optionxform=str;p.read(m.CONFIG,encoding='utf-8')
 root=first_available_named_path(p,'IntroPaths')
 if root is None:
  folder=p.get('IntroDetection','Folder',fallback='').strip()
  root=m.Path(folder) if folder else None
 return root

def _select_intro(project_name,intro_mode):
 mode=str(intro_mode or '0').strip()
 if mode.casefold() in ('0','false','off','none',''):return None
 root=_intro_root()
 if root is None:return None
 if mode.casefold()!='ask':
  chosen=root/mode
  life.log('INTRO_PROFILE_SELECTED',project=project_name,file=str(chosen),exists=chosen.is_file())
  return chosen
 intros=sorted([x for x in root.iterdir() if x.is_file() and x.suffix.casefold() in ('.mp4','.mov','.mxf','.avi','.mkv')],key=lambda x:x.name.casefold(),reverse=True) if root.is_dir() else []
 if _INTRO_SELECTOR is None:return None
 chosen=_INTRO_SELECTOR(project_name,intros)
 if chosen is False:raise m.WorkflowBack()
 life.log('INTRO_MANUAL_SELECTION',project=project_name,file=str(chosen) if chosen else None)
 return m.Path(chosen) if chosen else None

def _timeline_names(project):
 try:return [t.GetName() for t in (project.GetTimelineByIndex(i) for i in range(1,(project.GetTimelineCount() or 0)+1)) if t]
 except:return []
def _select_timeline(project,name):
 names=_timeline_names(project);life.log('TIMELINE_CANDIDATES',project=name,candidates=names)
 if name in names:
  for i in range(1,(project.GetTimelineCount() or 0)+1):
   t=project.GetTimelineByIndex(i)
   if t and t.GetName()==name:return t
 return project.GetCurrentTimeline()
def _stage(phase):
 m.PROGRESS.set_percent(phase,{'RESOLVE':8,'PROJECT_MANAGER':16,'PROJECT_CREATE':22,'MEDIA_POOL':24,'MEDIA_IMPORT':30,'TIMELINE':62,'AUDIO':76,'DELIVER':86,'SAVE':94,'DONE':100}.get(phase,0))
def _project_folder(pm,folder):
 if not folder:return
 root=pm.GetRootFolder();pm.SetCurrentFolder(root)
 for part in re.split(r'[\\/]+',folder):
  if not part:continue
  found=None
  for child in pm.GetFolderListInCurrentFolder() or []:
   try:n=child.GetName()
   except:n=str(child)
   if n.casefold()==part.casefold():found=child;break
  if found is None:
   try:found=pm.AddSubFolder(pm.GetCurrentFolder(),part)
   except:found=None
  if found is None:raise RuntimeError(f'Nelze vytvořit/najít Resolve Project Library folder: {part}')
  pm.SetCurrentFolder(found)
def build(query):
 phase='INIT';name=str(query)
 try:
  root,folder,timeout,alive,deliver_preset,deliver_folder=m.cfg();src=m.resolve_project(root,query);name=src.name;life.begin_log_session('run',name);life.log('PROJECT_RESOLVED',query=query,name=name)
  profile=project_profiles.resolve(name)
  while True:
   selected_title=timeline_assets.choose_title(name,_TITLE_SELECTOR) if profile.title_image else None
   if selected_title is False:return
   try:selected_intro=_select_intro(name,profile.intro)
   except m.WorkflowBack:continue
   break
  selected_credits=timeline_assets.find_credits() if profile.end_credits else None;asset_cfg=timeline_assets.config()
  phase='RESOLVE';_stage(phase);r=m.ensure(name,timeout)
  phase='PROJECT_MANAGER';_stage(phase);pm=r.GetProjectManager();_project_folder(pm,folder)
  existing=False;pr=None
  projects=pm.GetProjectListInCurrentFolder() or []
  existing_name=next((x for x in projects if x.casefold()==name.casefold()),None)
  if existing_name:pr=pm.LoadProject(existing_name);existing=pr is not None
  life.log('PROJECT_EXISTENCE',name=name,existing=existing)
  silence_requested=False
  if not existing and profile.silence_trim=='1':
   silence_requested=True;life.log('SILENCE_TRIM_PROFILE_CHOICE',project=name,mode='1',selected=True)
  elif not existing and profile.silence_trim=='ask' and _SILENCE_SELECTOR is not None:
   silence_choice=_SILENCE_SELECTOR(name)
   if silence_choice is None:life.log('SILENCE_TRIM_BACK_REQUESTED',project=name);raise m.WorkflowCancelled(_('Selection cancelled.'))
   silence_requested=bool(silence_choice);life.log('SILENCE_TRIM_PROFILE_CHOICE',project=name,mode='ask',selected=silence_requested)
  elif not existing:life.log('SILENCE_TRIM_PROFILE_CHOICE',project=name,mode=profile.silence_trim,selected=False)
  if not existing:
   phase='PROJECT_CREATE';_stage(phase);life.log('PROJECT_CREATE_CALL',name=name);pr=pm.CreateProject(name);life.log('PROJECT_CREATE_RETURN',name=name,returned=pr is not None)
   if pr is None:
    life.log('PROJECT_CREATE_RELOAD_BEGIN',name=name);projects=pm.GetProjectListInCurrentFolder() or [];created_name=next((x for x in projects if x.casefold()==name.casefold()),None)
    if created_name:pr=pm.LoadProject(created_name)
    life.log('PROJECT_CREATE_RELOAD_END',name=name,found=bool(created_name),loaded=pr is not None)
   if pr is None:raise RuntimeError(f'Nelze vytvořit ani znovu načíst projekt: {name}')
   life.log('PROJECT_OBJECT_OK',name=name)
   phase='MEDIA_POOL';_stage(phase)
   # Diagnostic only: do not change workflow or impose a timeout yet.
   try:current=pm.GetCurrentProject();current_name=current.GetName() if current is not None else None
   except Exception as exc:current=None;current_name=None;life.log('PROJECT_CURRENT_DIAGNOSTIC_ERROR',name=name,error=repr(exc))
   life.log('PROJECT_CURRENT_DIAGNOSTIC',expected=name,current=current_name,same_object=current is pr if current is not None else None)
   mp=_diagnosed_api_call('MEDIA_POOL_GET',pr.GetMediaPool,name=name,current_project=current_name)
   if mp is None:raise RuntimeError(f'Projekt nemá dostupný Media Pool: {name}')
   life.log('MEDIA_POOL_OK',name=name);life.log('ROOT_FOLDER_GET',name=name);master=mp.GetRootFolder()
   if master is None:raise RuntimeError(f'Projekt nemá dostupný kořen Media Poolu: {name}')
   life.log('ROOT_FOLDER_OK',name=name)
   images_bin=m.getbin(mp,master,'IMAGES');intro_bin=m.getbin(mp,master,'INTRO')
   timeline_title=None;timeline_credits=None
   for kind,path in (('title',selected_title),('credits',selected_credits)):
    if not path:continue
    if not path.is_file():life.log('IMAGE_ASSET_SKIPPED',kind=kind,reason='file_missing',file=str(path));continue
    life.log('IMAGE_IMPORT_CALL',kind=kind,bin='IMAGES',file=str(path));mp.SetCurrentFolder(images_bin);image_result=mp.ImportMedia([str(path)]);life.log('IMAGE_IMPORT_RETURN',kind=kind,file=str(path),accepted=len(image_result) if image_result else 0)
    if image_result:
     if kind=='title':timeline_title=path
     else:timeline_credits=path
    else:life.log('IMAGE_ASSET_SKIPPED',kind=kind,reason='resolve_rejected',file=str(path))
   timeline_intro=None
   if selected_intro:
    if selected_intro.is_file():
     life.log('INTRO_IMPORT_CALL',bin='INTRO',file=str(selected_intro));mp.SetCurrentFolder(intro_bin);intro_result=mp.ImportMedia([str(selected_intro)]);life.log('INTRO_IMPORT_RETURN',file=str(selected_intro),accepted=len(intro_result) if intro_result else 0)
     if intro_result:timeline_intro=selected_intro
    else:life.log('INTRO_ASSET_SKIPPED',reason='file_missing',file=str(selected_intro))
   phase='MEDIA_IMPORT';_stage(phase);shoot=src/'SHOOTING';m.sync_source(mp,master,shoot)
   phase='TIMELINE';_stage(phase)
   trim_ranges=None
   if silence_requested:
    trim_ranges=silence_trim.analyze_shooting(shoot);life.log('SILENCE_TRIM_ANALYSIS_COMPLETE',project=name,clips=len(trim_ranges))
   if _CREATOR:timeline=_CREATOR(mp,master,shoot,name,timeline_intro,timeline_title,timeline_credits,asset_cfg['title_seconds'],asset_cfg['credits_seconds'],trim_ranges)
   else:timeline=m.create_initial_timeline(mp,master,shoot,name,timeline_intro,timeline_title,timeline_credits,asset_cfg['title_seconds'],asset_cfg['credits_seconds'],25,trim_ranges)
   if timeline is None:raise RuntimeError(f'Nelze vytvořit timeline: {name}')
   project_timeline=timeline
  else:
   project_timeline=_select_timeline(pr,name)
   if project_timeline is None:raise RuntimeError(f'Projekt nemá timeline: {name}')
  phase='AUDIO';_stage(phase);timeline_audio.ensure_audio_layout(pr,project_timeline)
  phase='DELIVER';_stage(phase);m.apply_deliver(pr,src,deliver_preset,deliver_folder)
  phase='SAVE';_stage(phase);pm.SaveProject();phase='DONE';_stage(phase);life.log('PROJECT_UPDATE_DONE',name=name)
  return pr
 except m.WorkflowBack:life.log('WORKFLOW_BACK_AT_NONWIZARD_STAGE',phase=phase);return
 except m.WorkflowCancelled:life.log('WORKFLOW_CANCELLED',phase=phase);raise
 except Exception as e:life.log('PROJECT_UPDATE_ERROR',phase=phase,error=repr(e),traceback=traceback.format_exc());raise
