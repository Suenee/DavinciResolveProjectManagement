#!/usr/bin/env python3
from __future__ import annotations
import argparse,configparser,itertools,os,re,shutil,statistics,sys,threading,time,tkinter as tk
from pathlib import Path
from tkinter import ttk
from tkinter import font as tkfont
from datetime import datetime
import resolve_lifecycle as life
APP=Path(__file__).resolve().parent; CONFIG=APP/'config.ini'; EXAMPLE=APP/'config.example.ini'; HISTORY=APP/'runtime'/'startup_history.ini'; DATE=re.compile(r'^\d{8}\s+'); OPTIONAL=('IMAGES','PHOTOS','AUDIO')
class ConsoleProgress:
 def __init__(self):self.stop_event=None;self.thread=None;self.started=0
 def start(self,message):
  self.stop();self.started=time.time();self.stop_event=threading.Event()
  def run():
   spin=itertools.cycle('|/-\\')
   while not self.stop_event.wait(.12):sys.stdout.write(f'\r[{next(spin)}] {message}  {int(time.time()-self.started)} s   ');sys.stdout.flush()
  self.thread=threading.Thread(target=run,daemon=True);self.thread.start()
 def stop(self,done=None):
  if self.stop_event:
   self.stop_event.set();self.thread.join(.5) if self.thread else None;elapsed=int(time.time()-self.started);sys.stdout.write('\r'+' '*110+'\r');sys.stdout.flush();print(f'[OK] {done} ({elapsed} s)') if done else None
  self.stop_event=None;self.thread=None
 def bar(self,message,current,total):
  width=24;ratio=current/total if total else 1;filled=min(width,int(width*ratio));sys.stdout.write(f"\r[{'█'*filled+'░'*(width-filled)}] {ratio*100:3.0f}%  {message}  {current}/{total}   ");sys.stdout.flush()
 def bar_done(self):sys.stdout.write('\n');sys.stdout.flush()
PROGRESS=ConsoleProgress()
def cfg():
 if not CONFIG.exists():shutil.copy2(EXAMPLE,CONFIG)
 p=configparser.ConfigParser();p.read(CONFIG,encoding='utf-8');return Path(p.get('Paths','ProjectRoot')),p.get('DaVinciResolve','ResolveProjectFolder',fallback='').strip(),p.getint('DaVinciResolve','StartupTimeout',fallback=180),p.getint('DaVinciResolve','AliveTimeout',fallback=900)
def nodate(name):return DATE.sub('',name,count=1).strip()
def created(p):
 try:return p.stat().st_ctime
 except OSError:return 0
def center(root):root.update_idletasks();w=root.winfo_width();h=root.winfo_height();root.geometry(f'{w}x{h}+{max(0,(root.winfo_screenwidth()-w)//2)}+{max(0,(root.winfo_screenheight()-h)//2)}')
def choose(candidates,query):
 candidates=list(candidates);result=[None];root=tk.Tk();root.title('Vyber projekt');root.resizable(False,False);outer=ttk.Frame(root,padding=(20,16,20,14));outer.pack();ttk.Label(outer,text=f'Pro „{query}“ jsem našel více možností:').pack(anchor='w',pady=(0,10));frame=ttk.Frame(outer);frame.pack()
 tree=ttk.Treeview(frame,columns=('name','created'),show='headings',height=min(max(len(candidates),5),10),selectmode='browse')
 default_font=tkfont.nametofont('TkDefaultFont'); date_sample='18.08.2026 23:59:59'; date_width=default_font.measure(date_sample)+24; total_width=520; name_width=max(260,total_width-date_width)
 tree.column('name',width=name_width,anchor='w',stretch=True);tree.column('created',width=date_width,anchor='e',stretch=False)
 sort_state={'column':'created','reverse':True}
 def rebuild(column=None,reverse=None):
  selected_path=None;sel=tree.selection()
  if sel:
   try:selected_path=Path(tree.item(sel[0],'values')[2])
   except:pass
  if column is not None:
   sort_state['column']=column;sort_state['reverse']=reverse if reverse is not None else not(sort_state['column']==column and sort_state['reverse'])
  key=(lambda p:p.name.casefold()) if sort_state['column']=='name' else created
  ordered=sorted(candidates,key=key,reverse=sort_state['reverse']);tree.delete(*tree.get_children())
  for i,p in enumerate(ordered):
   stamp=datetime.fromtimestamp(created(p)).strftime('%d.%m.%Y %H:%M:%S');iid=str(i);tree.insert('','end',iid=iid,values=(p.name,stamp,str(p)))
   if selected_path and p==selected_path:tree.selection_set(iid);tree.focus(iid)
  if not tree.selection() and ordered:tree.selection_set('0');tree.focus('0')
  tree.heading('name',text='Projekt',anchor='w',command=lambda:sort_by('name'))
  tree.heading('created',text='Vytvořeno',anchor='e',command=lambda:sort_by('created'))
 def sort_by(column):
  reverse=not sort_state['reverse'] if sort_state['column']==column else (True if column=='created' else False);sort_state['column']=column;sort_state['reverse']=reverse;rebuild()
 tree.configure(columns=('name','created'));scroll=ttk.Scrollbar(frame,orient='vertical',command=tree.yview);tree.configure(yscrollcommand=scroll.set);tree.pack(side='left');scroll.pack(side='right',fill='y');rebuild()
 def ok(*_):
  s=tree.selection()
  if s:
   name=tree.item(s[0],'values')[0];result[0]=next((p for p in candidates if p.name==name),None)
  root.destroy()
 def cancel(*_):root.destroy()
 b=ttk.Frame(outer);b.pack(pady=(14,0));ttk.Button(b,text='OK',command=ok,width=13).pack(side='left',padx=6);ttk.Button(b,text='Cancel',command=cancel,width=13).pack(side='left',padx=6);tree.bind('<Double-1>',ok);root.bind('<Return>',ok);root.bind('<Escape>',cancel);root.protocol('WM_DELETE_WINDOW',cancel);center(root);tree.focus_set();root.mainloop();return result[0]
def ask_sync(count):
 result=[False];root=tk.Tk();root.title('Aktualizace projektu');outer=ttk.Frame(root,padding=24);outer.pack();ttk.Label(outer,text=f'Nalezeno {count} nových souborů.\nChcete je do projektu doplnit?').pack(pady=(0,14))
 def yes(*_):result[0]=True;root.destroy()
 def no(*_):root.destroy()
 b=ttk.Frame(outer);b.pack();ttk.Button(b,text='Ano',command=yes,width=13).pack(side='left',padx=6);ttk.Button(b,text='Ne',command=no,width=13).pack(side='left',padx=6);root.bind('<Return>',yes);root.bind('<Escape>',no);center(root);root.mainloop();return result[0]
def resolve_project(root,query):
 q=query.strip().casefold();c=[x for x in root.iterdir() if x.is_dir()];exact=[x for x in c if x.name.casefold()==q]
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
  if stale.get('owned') and stale.get('mode')=='headless' and life.pid_running(stale.get('pid')):
   print('[WARN] Nalezena naše headless instance bez scripting API. Provádím recovery...');life.log('STALE_OWNED_RECOVERY',pid=stale.get('pid'));life.force_stop_owned();time.sleep(4)
  else:raise RuntimeError('Resolve.exe běží, ale scripting API není dostupné a není bezpečné jej automaticky ukončit.')
 for attempt in (1,2):
  est=estimate(timeout);start=time.time();pid=life.start_headless(name);life.log('API_WAIT_BEGIN',attempt=attempt,pid=pid,estimate=est)
  while time.time()-start<timeout:
   elapsed=time.time()-start
   if elapsed>=est*.95:est=max(est,elapsed/.92)
   pct=min(95,int(elapsed/est*100));w=24;f=int(w*pct/100);sys.stdout.write(f"\r[{'█'*f+'░'*(w-f)}] {pct:3d}%  Spouštím DaVinci Resolve... {int(elapsed)} s   ");sys.stdout.flush()
   if not life.pid_running(pid) and elapsed>5:life.log('HEADLESS_DIED',attempt=attempt,pid=pid,elapsed=elapsed);break
   r=connect()
   if r:
    actual=time.time()-start;save_sample(actual);life.log('API_READY',attempt=attempt,pid=pid,seconds=actual);sys.stdout.write('\r'+' '*110+'\r');print(f'[OK] DaVinci Resolve připraven (100 %, {actual:.1f} s)');return r
   time.sleep(.5)
  sys.stdout.write('\r'+' '*110+'\r');life.log('API_WAIT_FAILED',attempt=attempt,pid=pid);life.force_stop_owned()
  if attempt==1:print('[WARN] Start se nepodařil. Čistím runtime a zkouším znovu...');time.sleep(5)
 raise RuntimeError(f'Resolve se nepřihlásil k API ani po recovery (timeout {timeout} s na pokus).')
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
  life.put(stage=f'Importuji {d.name}…');x=mp.ImportMedia([str(p) for p in sel]);n+=len(x) if x else 0;counter[0]+=len(sel);PROGRESS.bar(f'Import médií: {d.name}',counter[0],total);PROGRESS.bar_done()
 for c in [x for x in d.iterdir() if x.is_dir()]:
  if any(norm(p) in missing for p in allfiles(c)):n+=sync(mp,b,c,missing,counter,total)
 return n
def finish(r,keep,alive):
 s=life.state()
 if not(s.get('owned') and life.pid_running(s.get('pid'))):return
 if keep=='none':time.sleep(3);life.stop_owned(r)
 elif keep=='alive':life.launch_keeper();print(f'[OK] Resolve zůstává připravený --alive ({alive} s).')
 else:print('[OK] Resolve zůstává připravený --persistent.')
def build(query,keep):
 root,folder,timeout,alive=cfg();src=resolve_project(root,query);name=src.name;life.begin_log_session('run',name);life.log('PROJECT_RESOLVED',query=query,name=name)
 shoot=next((x for x in src.iterdir() if x.is_dir() and x.name.casefold()=='shooting'),src/'SHOOTING')
 if not shoot.is_dir():raise RuntimeError(f'Chybí SHOOTING: {shoot}')
 dirs=[shoot]+[d for dn in OPTIONAL for d in src.iterdir() if d.is_dir() and d.name.casefold()==dn.casefold()];fs={norm(p):p for d in dirs for p in allfiles(d)};r=ensure(name,timeout);life.put(busy=True,project=name,stage='Kontroluji projekt…',keep_mode=keep,alive_timeout=alive)
 try:
  pm=r.GetProjectManager();pm.GotoRootFolder()
  if folder and not pm.OpenFolder(folder):raise RuntimeError(f'Project Library folder nenalezen: {folder}')
  projects=pm.GetProjectListInCurrentFolder() or [];existing=next((x for x in projects if x.casefold()==name.casefold()),None)
  if existing:
   pr=pm.LoadProject(existing);mp=pr.GetMediaPool();master=mp.GetRootFolder();have=set();present(master,have);missing=set(fs)-have;life.log('PROJECT_EXISTS',name=existing,new_files=len(missing))
   if not missing:print('[OK] Projekt je aktuální. Žádná nová média.');return finish(r,keep,alive)
   print(f'[INFO] Nalezeno {len(missing)} nových souborů.')
   if not ask_sync(len(missing)):print('[OK] Projekt ponechán beze změny.');return finish(r,keep,alive)
   counter=[0];imported=sum(sync(mp,master,d,missing,counter,len(missing)) for d in dirs if any(norm(p) in missing for p in allfiles(d)));pm.SaveProject();life.log('SYNC_DONE',imported=imported);print(f'[OK] Doplněno médií: {imported}')
  else:
   pr=pm.CreateProject(name);mp=pr.GetMediaPool();master=mp.GetRootFolder();missing=set(fs);counter=[0];imported=sum(sync(mp,master,d,missing,counter,len(missing)) for d in dirs);tb=getbin(mp,master,'TIMELINES');mp.SetCurrentFolder(tb);tn=nodate(name) or name;mp.CreateEmptyTimeline(tn);pm.SaveProject();life.log('PROJECT_CREATED',name=name,imported=imported,timeline=tn);print(f'[OK] Projekt vytvořen: {name} | Timeline: {tn} | Média: {imported}')
 finally:life.put(busy=False,stage='Hotovo')
 finish(r,keep,alive)
def main():
 p=argparse.ArgumentParser();p.add_argument('project');g=p.add_mutually_exclusive_group();g.add_argument('--alive',action='store_true');g.add_argument('--persistent',action='store_true');a=p.parse_args();keep='persistent' if a.persistent else 'alive' if a.alive else 'none'
 try:build(a.project,keep);return 0
 except Exception as e:
  PROGRESS.stop()
  try:life.log('ERROR',message=str(e))
  except:pass
  print('ERROR:',e,file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
