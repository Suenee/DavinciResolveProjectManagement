#!/usr/bin/env python3
from __future__ import annotations
import argparse,configparser,itertools,os,re,shutil,statistics,sys,threading,time,tkinter as tk
from pathlib import Path
from tkinter import ttk
from tkinter import font as tkfont
from datetime import datetime
import resolve_lifecycle as life

APP=Path(__file__).resolve().parent
CONFIG=APP/'config.ini'; EXAMPLE=APP/'config.example.ini'; HISTORY=APP/'runtime'/'startup_history.ini'
DATE=re.compile(r'^\d{8}\s+'); OPTIONAL=('IMAGES','PHOTOS','AUDIO')

class ConsoleProgress:
 def __init__(self):self.root=None;self.status=None;self.detail=None;self.progress=None;self.console_ok=True
 def _pump(self):
  if self.root is not None:
   try:self.root.update_idletasks();self.root.update()
   except tk.TclError:self.root=None
 def _write(self,text):
  if not self.console_ok:return False
  try:sys.stdout.write(text);sys.stdout.flush();return True
  except (OSError,ValueError):
   self.console_ok=False
   try:life.log('CONSOLE_PROGRESS_DISABLED',reason='stdout unavailable')
   except Exception:pass
   return False
 def start(self,message):
  try:
   self.root=tk.Tk();self.root.title('Průběh — DavinciResolveProjectManagement 1.21');self.root.resizable(False,False)
   box=ttk.Frame(self.root,padding=18);box.pack();self.status=tk.StringVar(value=message);self.detail=tk.StringVar(value='')
   ttk.Label(box,textvariable=self.status,font=('Segoe UI',11,'bold')).pack(anchor='w')
   ttk.Label(box,textvariable=self.detail).pack(anchor='w',pady=(5,8))
   self.progress=ttk.Progressbar(box,length=460,maximum=100,mode='determinate');self.progress.pack()
   center(self.root);self._pump();life.log('GUI_PROGRESS_OPEN')
  except Exception as e:life.log('GUI_PROGRESS_OPEN_ERROR',error=repr(e));self.root=None
 def stage(self,message,percent=None):
  if self.root is None:return
  self.status.set(message)
  if percent is not None:self.progress['value']=max(0,min(100,float(percent)))
  self._pump()
 def stop(self,done='Hotovo'):
  if self.root is None:return
  try:self.status.set(done or 'Hotovo');self.progress['value']=100;self._pump();self.root.destroy()
  except tk.TclError:pass
  self.root=None
 def bar(self,message,current,total):
  ratio=current/total if total else 1
  if self.root is not None:
   self.status.set(message);self.detail.set(f'{current} / {total}');self.progress['value']=max(0,min(100,ratio*100));self._pump()
  else:self._write(f'\r{ratio*100:3.0f}% {message} {current}/{total}   ')
 def bar_done(self):
  if self.root is None:self._write('\n')
 def set_percent(self,message,percent):
  self.stage(message,percent)
PROGRESS=ConsoleProgress()

def cfg():
 if not CONFIG.exists():shutil.copy2(EXAMPLE,CONFIG)
 p=configparser.ConfigParser();p.read(CONFIG,encoding='utf-8')
 return (Path(p.get('Paths','ProjectRoot')),p.get('DaVinciResolve','ResolveProjectFolder',fallback='').strip(),p.getint('DaVinciResolve','StartupTimeout',fallback=180),p.getint('DaVinciResolve','AliveTimeout',fallback=900),p.get('Deliver','Preset',fallback='').strip(),p.get('Deliver','Folder',fallback='DELIVERY').strip() or 'DELIVERY')
def nodate(name):return DATE.sub('',name,count=1).strip()
def created(p):
 try:return p.stat().st_ctime
 except OSError:return 0
def center(root):
 root.update_idletasks();w=root.winfo_width();h=root.winfo_height();root.geometry(f'{w}x{h}+{max(0,(root.winfo_screenwidth()-w)//2)}+{max(0,(root.winfo_screenheight()-h)//2)}')
def choose(candidates,query):return (list(candidates) or [None])[0]
def resolve_project(root,query):
 c=[x for x in root.iterdir() if x.is_dir()]
 if not query:
  s=choose(c,'')
  if s:return s
  raise RuntimeError('Výběr projektu byl zrušen.')
 q=query.strip().casefold();exact=[x for x in c if x.name.casefold()==q]
 if len(exact)==1:return exact[0]
 stripped=[x for x in c if nodate(x.name).casefold()==q]
 if len(stripped)==1:return stripped[0]
 m=stripped or [x for x in c if q in nodate(x.name).casefold() or q in x.name.casefold()]
 if len(m)==1:return m[0]
 if len(m)>1:
  s=choose(m,query)
  if s:return s
  raise RuntimeError('Výběr projektu byl zrušen.')
 raise RuntimeError(f'Nenalezen projekt odpovídající názvu: {query}')
def dvr():
 modules=Path(os.environ.get('PROGRAMDATA',r'C:\ProgramData'))/'Blackmagic Design'/'DaVinci Resolve'/'Support'/'Developer'/'Scripting'/'Modules';sys.path.insert(0,str(modules));import DaVinciResolveScript as d;return d
def connect():
 try:return dvr().scriptapp('Resolve')
 except:return None
def hsec():return 'Computer:'+os.environ.get('COMPUTERNAME','UNKNOWN')
def estimate(timeout):
 p=configparser.ConfigParser();p.read(HISTORY,encoding='utf-8')
 try:s=[float(x) for x in p.get(hsec(),'samples',fallback='').split(',') if x.strip()];return max(10,min(timeout,statistics.median(s[-9:]))) if s else min(timeout,60)
 except:return min(timeout,60)
def save_sample(sec):
 HISTORY.parent.mkdir(parents=True,exist_ok=True);p=configparser.ConfigParser();p.read(HISTORY,encoding='utf-8');s=hsec();p.add_section(s) if not p.has_section(s) else None
 try:a=[float(x) for x in p.get(s,'samples',fallback='').split(',') if x.strip()]
 except:a=[]
 a=(a+[round(sec,2)])[-12:];p.set(s,'samples',','.join(map(str,a)));p.set(s,'computer_name',os.environ.get('COMPUTERNAME','UNKNOWN'));p.set(s,'estimate_seconds',f'{statistics.median(a):.2f}')
 with HISTORY.open('w',encoding='utf-8') as f:p.write(f)
def ensure(name,timeout):
 r=connect()
 if r:return r
 stale=life.state()
 if life.any_resolve():
  if stale.get('owned') and stale.get('mode')=='headless' and life.pid_running(stale.get('pid')):life.force_stop_owned();time.sleep(4)
  else:raise RuntimeError('Resolve.exe běží, ale scripting API není dostupné a není bezpečné jej automaticky ukončit.')
 for attempt in (1,2):
  est=estimate(timeout);start=time.time();pid=life.start_headless(name)
  while time.time()-start<timeout:
   elapsed=time.time()-start;pct=min(95,int(elapsed/max(est,1)*100));PROGRESS.set_percent('Spouštím DaVinci Resolve…',pct)
   r=connect()
   if r:save_sample(time.time()-start);PROGRESS.set_percent('DaVinci Resolve připojen',100);return r
   if not life.pid_running(pid) and elapsed>5:break
   time.sleep(.5)
  life.force_stop_owned();time.sleep(5)
 raise RuntimeError('Resolve se nepřihlásil k API.')
def norm(p):return os.path.normcase(os.path.normpath(os.path.abspath(str(p))))
def allfiles(d):return [x.resolve() for x in d.rglob('*') if x.is_file()]
def direct(d):return [x.resolve() for x in d.iterdir() if x.is_file()]
def subs(folder):
 try:return folder.GetSubFolderList() or []
 except:return []
def getbin(mp,parent,name):
 parent_name=parent.GetName() if parent is not None else '<none>'
 life.log('MEDIA_BIN_LOOKUP',parent=parent_name,name=name)
 children=subs(parent)
 for s in children:
  if (s.GetName() or '').casefold()==name.casefold():
   life.log('MEDIA_BIN_REUSE',parent=parent_name,name=name);return s
 life.log('MEDIA_BIN_NOT_FOUND',parent=parent_name,name=name,children=len(children))
 life.log('MEDIA_BIN_CREATE_CALL',parent=parent_name,name=name)
 b=mp.AddSubFolder(parent,name)
 life.log('MEDIA_BIN_CREATE_RETURN',parent=parent_name,name=name,success=b is not None)
 if b is None:raise RuntimeError(f'Nelze vytvořit BIN {name}')
 return b
def present(folder,out):
 try:clips=folder.GetClipList() or []
 except:clips=[]
 for c in clips:
  try:p=c.GetClipProperty('File Path')
  except:p=''
  if p:out.add(norm(p))
 for s in subs(folder):present(s,out)
def sync(mp,parent,d,missing,counter,total):
 parent_name=parent.GetName() if parent is not None else '<none>'
 files=direct(d);life.log('MEDIA_DIR_BEGIN',source=str(d),parent=parent_name,bin=d.name,direct_files=len(files))
 b=getbin(mp,parent,d.name);life.log('MEDIA_SET_CURRENT_CALL',bin=d.name);current_ok=mp.SetCurrentFolder(b);life.log('MEDIA_SET_CURRENT_RETURN',bin=d.name,success=bool(current_ok));sel=[p for p in files if norm(p) in missing];n=0
 if sel:
  life.log('MEDIA_IMPORT_CALL',bin=d.name,requested=len(sel),files=[str(p) for p in sel])
  x=mp.ImportMedia([str(p) for p in sel]);accepted=len(x) if x else 0;n+=accepted;counter[0]+=len(sel)
  life.log('MEDIA_IMPORT_RETURN',bin=d.name,requested=len(sel),accepted=accepted)
  PROGRESS.bar(f'Import médií: {d.name}',counter[0],total);PROGRESS.bar_done()
 for c in sorted([x for x in d.iterdir() if x.is_dir()],key=lambda p:p.name.casefold()):
  if any(norm(p) in missing for p in allfiles(c)):n+=sync(mp,b,c,missing,counter,total)
 life.log('MEDIA_DIR_END',source=str(d),bin=d.name,accepted=n);return n
def shooting_order(folder):
 ordered=sorted(direct(folder),key=lambda p:(created(p),p.name.casefold()))
 for child in sorted([x for x in folder.iterdir() if x.is_dir()],key=lambda p:p.name.casefold()):ordered.extend(shooting_order(child))
 return ordered
def collect_clip_items(folder,out):
 try:clips=folder.GetClipList() or []
 except:clips=[]
 for clip in clips:
  try:path=clip.GetClipProperty('File Path')
  except:path=''
  if path:out[norm(path)]=clip
 for sub in subs(folder):collect_clip_items(sub,out)
def _append_still(mp,timeline,item,seconds,fps,label):
 frames=max(1,int(round(seconds*fps)))
 try:before=item.GetMarkInOut() or {}
 except Exception:before={}
 life.log('TIMELINE_STILL_MARK_CALL',kind=label,seconds=seconds,frames=frames,before=before)
 try:mark_ok=bool(item.SetMarkInOut(0,frames-1,'video'))
 except Exception as e:mark_ok=False;life.log('TIMELINE_STILL_MARK_ERROR',kind=label,error=repr(e))
 try:marked=item.GetMarkInOut() or {}
 except Exception:marked={}
 life.log('TIMELINE_STILL_MARK_RETURN',kind=label,success=mark_ok,marked=marked)
 life.log('TIMELINE_STILL_APPEND_CALL',kind=label,seconds=seconds,frames=frames,method='MediaPoolItem.SetMarkInOut + plain AppendToTimeline')
 result=mp.AppendToTimeline([item])
 timeline_item=(result[-1] if isinstance(result,(list,tuple)) and result else None)
 try:actual=int(round(float(timeline_item.GetDuration()))) if timeline_item is not None else None
 except Exception:actual=None
 try:item.ClearMarkInOut('video')
 except Exception:pass
 verified=(actual==frames)
 life.log('TIMELINE_STILL_APPEND_RETURN',kind=label,success=bool(result),requested_frames=frames,actual_frames=actual,verified=verified)
 if result and not verified:life.log('TIMELINE_STILL_DURATION_MISMATCH',kind=label,requested_frames=frames,actual_frames=actual)
 return bool(result)
def create_initial_timeline(mp,master,shoot,timeline_name,intro_path=None,title_path=None,credits_path=None,title_seconds=20,credits_seconds=25,fps=25):
 shoot_bin=getbin(mp,master,shoot.name);clip_map={};collect_clip_items(shoot_bin,clip_map);ordered_files=shooting_order(shoot)
 images_bin=getbin(mp,master,'IMAGES');image_map={};collect_clip_items(images_bin,image_map)
 intro_clip=None
 if intro_path:
  intro_bin=getbin(mp,master,'INTRO');intro_map={};collect_clip_items(intro_bin,intro_map);intro_clip=intro_map.get(norm(intro_path))
 timeline_bin=getbin(mp,master,'TIMELINES');mp.SetCurrentFolder(timeline_bin);timeline=mp.CreateEmptyTimeline(timeline_name)
 if timeline is None:raise RuntimeError(f'Nelze vytvořit timeline: {timeline_name}')
 if title_path:
  item=image_map.get(norm(title_path))
  if item and not _append_still(mp,timeline,item,title_seconds,fps,'title'):life.log('TIMELINE_TITLE_SKIPPED',reason='append_failed',file=str(title_path))
 if intro_clip:
  life.log('TIMELINE_INTRO_APPEND_CALL',file=str(intro_path));r=mp.AppendToTimeline([intro_clip]);life.log('TIMELINE_INTRO_APPEND_RETURN',success=bool(r))
 shooting=[clip_map[norm(p)] for p in ordered_files if norm(p) in clip_map]
 if shooting:life.log('TIMELINE_SHOOTING_APPEND_CALL',clips=len(shooting));r=mp.AppendToTimeline(shooting);life.log('TIMELINE_SHOOTING_APPEND_RETURN',success=bool(r))
 if credits_path:
  item=image_map.get(norm(credits_path))
  if item and not _append_still(mp,timeline,item,credits_seconds,fps,'credits'):life.log('TIMELINE_CREDITS_SKIPPED',reason='append_failed',file=str(credits_path))
 return timeline
def apply_deliver(project,src,preset,folder):
 if not preset:return None
 target=(src/folder).resolve();target.mkdir(parents=True,exist_ok=True)
 if not project.LoadRenderPreset(preset):raise RuntimeError(f'Nelze načíst render preset: {preset}')
 if not project.SetRenderSettings({'TargetDir':str(target)}):raise RuntimeError(f'Nelze nastavit Deliver TargetDir: {target}')
 return target
def finish(r,keep,alive):
 s=life.state()
 if not(s.get('owned') and life.pid_running(s.get('pid'))):return
 if keep=='none':time.sleep(3);life.stop_owned(r)
 elif keep=='alive':life.launch_keeper()
def main():
 p=argparse.ArgumentParser();p.add_argument('project',nargs='?',default='');g=p.add_mutually_exclusive_group();g.add_argument('--alive',action='store_true');g.add_argument('--persistent',action='store_true');a=p.parse_args();keep='persistent' if a.persistent else 'alive' if a.alive else 'none'
 try:build(a.project,keep);return 0
 except Exception as e:
  try:life.log('ERROR',message=str(e))
  except:pass
  print('ERROR:',e,file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
