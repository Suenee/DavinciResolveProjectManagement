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
 def __init__(self):self.stop_event=None;self.thread=None;self.started=0
 def start(self,message):self.started=time.time()
 def stop(self,done=None):pass
 def bar(self,message,current,total):
  ratio=current/total if total else 1;sys.stdout.write(f'\r{ratio*100:3.0f}% {message} {current}/{total}   ');sys.stdout.flush()
 def bar_done(self):sys.stdout.write('\n');sys.stdout.flush()
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
   elapsed=time.time()-start;pct=min(95,int(elapsed/max(est,1)*100));sys.stdout.write(f'\r{pct:3d}% Spouštím DaVinci Resolve... {int(elapsed)} s   ');sys.stdout.flush()
   r=connect()
   if r:save_sample(time.time()-start);sys.stdout.write('\r'+' '*100+'\r');return r
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
 for s in subs(parent):
  if (s.GetName() or '').casefold()==name.casefold():return s
 b=mp.AddSubFolder(parent,name)
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
 b=getbin(mp,parent,d.name);mp.SetCurrentFolder(b);sel=[p for p in direct(d) if norm(p) in missing];n=0
 if sel:
  x=mp.ImportMedia([str(p) for p in sel]);n+=len(x) if x else 0;counter[0]+=len(sel);PROGRESS.bar(f'Import médií: {d.name}',counter[0],total);PROGRESS.bar_done()
 for c in sorted([x for x in d.iterdir() if x.is_dir()],key=lambda p:p.name.casefold()):
  if any(norm(p) in missing for p in allfiles(c)):n+=sync(mp,b,c,missing,counter,total)
 return n
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
def create_initial_timeline(mp,master,shoot,timeline_name):
 shoot_bin=getbin(mp,master,shoot.name);clip_map={};collect_clip_items(shoot_bin,clip_map);ordered_files=shooting_order(shoot);ordered_clips=[clip_map[norm(p)] for p in ordered_files if norm(p) in clip_map];timeline_bin=getbin(mp,master,'TIMELINES');mp.SetCurrentFolder(timeline_bin);timeline=mp.CreateTimelineFromClips(timeline_name,ordered_clips) if ordered_clips else mp.CreateEmptyTimeline(timeline_name)
 if timeline is None:raise RuntimeError(f'Nelze vytvořit timeline: {timeline_name}')
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
