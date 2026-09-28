#!/usr/bin/env python3
from __future__ import annotations
import re,traceback
import managed_builder as m
import resolve_lifecycle as life
import timeline_audio
import intro_match_routing
import verified_import
import timeline_assets
from i18n import _

_CREATOR=None
_INTRO_SELECTOR=None
_TITLE_SELECTOR=None

def set_timeline_creator(func):
 global _CREATOR;_CREATOR=func

def set_intro_selector(func):
 global _INTRO_SELECTOR;_INTRO_SELECTOR=func

def set_title_selector(func):
 global _TITLE_SELECTOR;_TITLE_SELECTOR=func

def _select_intro(project_name):
 p=m.configparser.ConfigParser(interpolation=None);p.optionxform=str;p.read(m.CONFIG,encoding='utf-8')
 folder=p.get('IntroDetection','Folder',fallback='').strip()
 if not folder:return None
 root=m.Path(folder)
 if p.has_section('IntroMapping'):
  for filename,pattern in p.items('IntroMapping'):
   try:matched=re.search(pattern,project_name,re.I) is not None
   except re.error as exc:
    life.log('INTRO_MAPPING_INVALID',file=filename,pattern=pattern,error=str(exc));continue
   life.log('INTRO_MAPPING_TEST',project=project_name,file=filename,pattern=pattern,matched=matched)
   if matched:
    chosen=root/filename;life.log('INTRO_MAPPING_MATCH',project=project_name,file=str(chosen),exists=chosen.is_file());return chosen
 intros=sorted([x for x in root.iterdir() if x.is_file() and x.suffix.casefold() in ('.mp4','.mov','.mxf','.avi','.mkv')],key=lambda x:x.name.casefold()) if root.is_dir() else []
 life.log('INTRO_MAPPING_NO_MATCH',project=project_name,folder=str(root),choices=[x.name for x in intros])
 if _INTRO_SELECTOR is None:return None
 chosen=_INTRO_SELECTOR(project_name,intros)
 life.log('INTRO_MANUAL_SELECTION',project=project_name,file=str(chosen) if chosen else None)
 return m.Path(chosen) if chosen else None

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
def _stage(name):
 life.put(stage=name);life.log('WORKFLOW_STAGE',stage=name)
 labels={'RESOLVE_CONNECT':_('Connecting to DaVinci Resolve…'),'PROJECT_OPEN':_('Opening Project Library…'),'PROJECT_CREATE':_('Creating project…'),'MEDIA_POOL':_('Preparing Media Pool…'),'MEDIA_IMPORT':_('Importing media…'),'MEDIA_VERIFY':_('Verifying media…'),'TIMELINE':_('Creating timeline…'),'VOICE_ISOLATION':_('Setting Voice Isolation…'),'INTRO_MATCH':_('Processing intro…'),'DELIVERY':_('Setting DELIVERY…'),'SAVE':_('Saving project…'),'FINAL_UI':_('Preparing EDIT page…'),'COMPLETE':_('Done')}
 pct={'RESOLVE_CONNECT':5,'PROJECT_OPEN':12,'PROJECT_CREATE':18,'MEDIA_POOL':24,'MEDIA_IMPORT':30,'MEDIA_VERIFY':72,'TIMELINE':78,'VOICE_ISOLATION':84,'INTRO_MATCH':87,'DELIVERY':90,'SAVE':94,'FINAL_UI':97,'COMPLETE':100}
 m.PROGRESS.stage(labels.get(name,name),pct.get(name))
def _frames_to_timecode(frame,fps):
 fps_i=max(1,int(round(float(fps))));frame=max(0,int(frame));hours=frame//(fps_i*3600);frame%=fps_i*3600;minutes=frame//(fps_i*60);frame%=fps_i*60;seconds=frame//fps_i;frames=frame%fps_i
 return f'{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}'
def _finish_resolve_ui(resolve,project,timeline,shooting_frame=None,fps=25):
 _stage('FINAL_UI')
 if timeline is None:timeline=project.GetCurrentTimeline()
 current_ok=bool(project.SetCurrentTimeline(timeline)) if timeline is not None else False
 page_ok=bool(resolve.OpenPage('edit'))
 if shooting_frame is not None:
  start_frame=int(timeline.GetStartFrame() or 0);start_tc_frames=shooting_frame-start_frame;target_tc=_frames_to_timecode(start_tc_frames,fps)
 else:target_tc=timeline.GetStartTimecode() if timeline is not None else None
 playhead_ok=bool(timeline.SetCurrentTimecode(target_tc)) if timeline is not None and target_tc else False
 life.log('FINAL_UI_RESULT',current_timeline=current_ok,edit_page=page_ok,shooting_frame=shooting_frame,target_timecode=target_tc,playhead_shooting_start=playhead_ok)
 return current_ok and page_ok and playhead_ok
def _create_timeline(mp,master,shoot,name,voice,intro_reference=None,intro_first=None,title_path=None,credits_path=None,title_seconds=20,credits_seconds=25,fps=25):
 if _CREATOR is None:raise RuntimeError('Timeline creator není inicializován.')
 _stage('TIMELINE');created=_CREATOR(mp,master,shoot,name,intro_first,title_path,credits_path,title_seconds,credits_seconds,fps)
 if isinstance(created,tuple):timeline,shooting_frame=created
 else:timeline,shooting_frame=created,None
 if voice:_stage('VOICE_ISOLATION');timeline=timeline_audio.configure(timeline)
 if voice and intro_reference:_stage('INTRO_MATCH');timeline=intro_match_routing.apply(mp,timeline,intro_reference)
 return timeline,shooting_frame

def _verify_media(mp,master,dirs,fs):
 _stage('MEDIA_VERIFY');retried,remaining=verified_import.verify_and_retry(mp,master,dirs,fs)
 if remaining:
  preview='\n'.join(remaining[:10]);more=f'\n... +{len(remaining)-10} dalších' if len(remaining)>10 else ''
  raise RuntimeError(f'DaVinci Resolve nepřijal {len(remaining)} mediálních souborů ani po opakovaném importu:\n{preview}{more}')
 if retried:print(f'[OK] Opakovaným importem doplněno médií: {retried}')

def build(query,keep):
 phase='INIT'
 root,folder,timeout,alive,deliver_preset,deliver_folder=m.cfg();src=m.resolve_project(root,query);name=src.name;life.begin_log_session('run',name);life.log('PROJECT_RESOLVED',query=query,name=name)
 selected_title=timeline_assets.choose_title(name,_TITLE_SELECTOR)
 selected_intro=_select_intro(name)
 selected_credits=timeline_assets.find_credits();asset_cfg=timeline_assets.config()
 m.PROGRESS.start(_('Preparing project {name}').format(name=name))
 shoot=next((x for x in src.iterdir() if x.is_dir() and x.name.casefold()=='shooting'),src/'SHOOTING')
 if not shoot.is_dir():raise RuntimeError(f'Chybí SHOOTING: {shoot}')
 dirs=[shoot]+[d for dn in m.OPTIONAL for d in src.iterdir() if d.is_dir() and d.name.casefold()==dn.casefold()];fs={m.norm(p):p for d in dirs for p in m.allfiles(d)}
 try:
  phase='RESOLVE_CONNECT';_stage(phase);r=m.ensure(name,timeout);life.put(busy=True,project=name,keep_mode=keep,alive_timeout=alive)
  phase='PROJECT_OPEN';_stage(phase);pm=r.GetProjectManager();pm.GotoRootFolder()
  if folder and not pm.OpenFolder(folder):raise RuntimeError(f'Project Library folder nenalezen: {folder}')
  projects=pm.GetProjectListInCurrentFolder() or [];existing=next((x for x in projects if x.casefold()==name.casefold()),None)
  if not existing:
   phase='PROJECT_CREATE';_stage(phase)
   life.log('PROJECT_CREATE_CALL',name=name)
   pr=pm.CreateProject(name)
   life.log('PROJECT_CREATE_RETURN',name=name,returned=pr is not None)
   if pr is None:
    # Some Resolve builds may create the project but fail to return a usable object.
    # Re-query the current library before declaring creation failed.
    life.log('PROJECT_CREATE_RELOAD_BEGIN',name=name)
    projects=pm.GetProjectListInCurrentFolder() or []
    created_name=next((x for x in projects if x.casefold()==name.casefold()),None)
    if created_name:pr=pm.LoadProject(created_name)
    life.log('PROJECT_CREATE_RELOAD_END',name=name,found=bool(created_name),loaded=pr is not None)
   if pr is None:raise RuntimeError(f'Nelze vytvořit ani znovu načíst projekt: {name}')
   life.log('PROJECT_OBJECT_OK',name=name)
   phase='MEDIA_POOL';_stage(phase);life.log('MEDIA_POOL_GET',name=name);mp=pr.GetMediaPool()
   if mp is None:raise RuntimeError(f'Projekt nemá dostupný Media Pool: {name}')
   life.log('MEDIA_POOL_OK',name=name);life.log('ROOT_FOLDER_GET',name=name);master=mp.GetRootFolder()
   if master is None:raise RuntimeError(f'Projekt nemá dostupný kořen Media Poolu: {name}')
   life.log('ROOT_FOLDER_OK',name=name)
   # These standard bins are part of every newly initialized project even when empty.
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
    if not selected_intro.is_file():
     life.log('INTRO_SKIPPED',reason='file_missing',file=str(selected_intro))
    else:
     life.log('INTRO_IMPORT_CALL',bin='INTRO',file=str(selected_intro));mp.SetCurrentFolder(intro_bin);intro_result=mp.ImportMedia([str(selected_intro)]);life.log('INTRO_IMPORT_RETURN',bin='INTRO',file=str(selected_intro),accepted=len(intro_result) if intro_result else 0)
     if intro_result:timeline_intro=selected_intro
     else:life.log('INTRO_SKIPPED',reason='resolve_rejected',file=str(selected_intro))
   missing=set(fs);counter=[0]
   phase='MEDIA_IMPORT';_stage(phase);life.log('MEDIA_SYNC_BEGIN',expected=len(fs),directories=[str(d) for d in dirs]);imported=sum(m.sync(mp,master,d,missing,counter,len(missing)) for d in dirs);life.log('MEDIA_SYNC_END',expected=len(fs),accepted=imported)
   phase='MEDIA_VERIFY';_verify_media(mp,master,dirs,fs)
   fps_raw=pr.GetSetting('timelineFrameRate') or pr.GetSetting('timelinePlaybackFrameRate') or '25'
   try:fps=float(str(fps_raw).replace(',','.'))
   except ValueError:fps=25.0
   tn=m.nodate(name) or name;phase='TIMELINE';created_timeline,shooting_frame=_create_timeline(mp,master,shoot,tn,True,intro_first=timeline_intro,title_path=timeline_title,credits_path=timeline_credits,title_seconds=asset_cfg['title_seconds'],credits_seconds=asset_cfg['credits_seconds'],fps=fps)
   phase='DELIVERY';_stage(phase);m.apply_deliver(pr,src,deliver_preset,deliver_folder)
   phase='SAVE';_stage(phase)
   if not pm.SaveProject():raise RuntimeError('SaveProject() selhal.')
   _finish_resolve_ui(r,pr,created_timeline,shooting_frame,fps)
   life.log('PROJECT_CREATED',name=name,imported=imported,timeline=tn);print(f'[OK] Projekt vytvořen: {name} | Timeline: {tn} | Média: {imported}')
  else:
   phase='PROJECT_LOAD';_stage(phase);pr=pm.LoadProject(existing)
   if pr is None:raise RuntimeError(f'Existující projekt nelze otevřít: {existing}')
   mp=pr.GetMediaPool();master=mp.GetRootFolder();have=set();m.present(master,have);missing=set(fs)-have;base=m.nodate(name) or name;st=_status(pr,base,missing,src,deliver_folder,shoot);incomplete=bool(missing) or not st['timeline'] or not st['voice'] or not st['deliver'];life.log('PROJECT_EXISTS',name=existing,incomplete=incomplete,expected_media=len(fs),present_media=len(have),**st)
   actions=ask(existing,st)
   if actions is None:print('[OK] Aktualizace projektu zrušena.');return m.finish(r,keep,alive)
   changed=False
   if actions['repository']:
    if missing:
     phase='MEDIA_IMPORT';_stage(phase);counter=[0];imported=sum(m.sync(mp,master,d,missing,counter,len(missing)) for d in dirs if any(m.norm(p) in missing for p in m.allfiles(d)));_verify_media(mp,master,dirs,fs);life.log('SYNC_DONE',imported=imported);print(f'[OK] Doplněno médií: {imported}');changed=True
    else:print('[OK] Repozitář je aktuální.')
   if actions['timeline']:
    tn=_unique_timeline_name(pr,base);phase='TIMELINE';created_timeline,shooting_frame=_create_timeline(mp,master,shoot,tn,actions['voice'],actions.get('intro_reference'));life.log('TIMELINE_UPDATE_CREATED',timeline=tn,voice=actions['voice'],intro_reference=actions.get('intro_reference'));print(f'[OK] Vytvořena timeline: {tn}');changed=True
   if actions['deliver']:
    phase='DELIVERY';_stage(phase);m.apply_deliver(pr,src,deliver_preset,deliver_folder);changed=True
   if changed:
    phase='SAVE';_stage(phase)
    if not pm.SaveProject():raise RuntimeError('SaveProject() selhal.')
    _finish_resolve_ui(r,pr,locals().get('created_timeline') or pr.GetCurrentTimeline(),locals().get('shooting_frame'),float(pr.GetSetting('timelineFrameRate') or 25))
   else:print('[OK] Nebyla vybrána žádná změna.')
  phase='COMPLETE';_stage(phase)
 except m.WorkflowCancelled:
  life.log('WORKFLOW_CANCELLED',phase=phase);return
 except Exception as exc:
  life.log('WORKFLOW_ERROR',phase=phase,error=repr(exc),traceback=traceback.format_exc());raise
 finally:
  life.put(busy=False,stage=_('Done'));m.PROGRESS.stop(_('Done'),success=not m.PROGRESS.cancel_requested)
 if 'r' in locals():m.finish(r,keep,alive)
