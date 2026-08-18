#!/usr/bin/env python3
from __future__ import annotations
import os,re,tkinter as tk
from pathlib import Path
from tkinter import ttk
import managed_builder as m
import resolve_lifecycle as life
import timeline_audio

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
  settings=project.GetRenderSettings() or {}
  target=settings.get('TargetDir') or settings.get('targetDir') or ''
  return bool(target) and m.norm(target)==expected
 except Exception:return False

def _status(project,base,missing,src,deliver_folder,shoot):
 timelines=_matching_timelines(project,base)
 timeline_ready=bool(timelines)
 voice_ready=any(timeline_audio.is_prepared(t) for t in timelines)
 return {'missing':len(missing),'timeline':timeline_ready,'voice':voice_ready,
         'deliver':_deliver_ready(project,src,deliver_folder)}

class ToolTip:
 def __init__(self,widget,text):self.widget=widget;self.text=text;self.tip=None;widget.bind('<Enter>',self.show);widget.bind('<Leave>',self.hide)
 def show(self,*_):
  if self.tip:return
  x=self.widget.winfo_rootx()+20;y=self.widget.winfo_rooty()+22;self.tip=tk.Toplevel(self.widget);self.tip.wm_overrideredirect(True);self.tip.wm_geometry(f'{x:+d}{y:+d}')
  ttk.Label(self.tip,text=self.text,padding=(7,4)).pack()
 def hide(self,*_):
  if self.tip:self.tip.destroy();self.tip=None

def ask(project_name,status):
 result=[None];root=tk.Tk();root.title('Aktualizace projektu');root.resizable(False,False)
 outer=ttk.Frame(root,padding=(22,18,22,16));outer.grid(row=0,column=0);ttk.Label(outer,text=f'Projekt {project_name} již existuje. Chceš jej aktualizovat?').grid(row=0,column=0,columnspan=3,sticky='w',pady=(0,14))
 ttk.Label(outer,text='Akce').grid(row=1,column=1,sticky='w',padx=(4,25));ttk.Label(outer,text='Stav').grid(row=1,column=2,sticky='e')
 repo=tk.BooleanVar(value=status['missing']>0);timeline=tk.BooleanVar(value=not status['timeline']);voice=tk.BooleanVar(value=True);deliver=tk.BooleanVar(value=not status['deliver'])
 vars={'repository':repo,'timeline':timeline,'voice':voice,'deliver':deliver};widgets={}
 def row(r,key,text,indent,status_text,tooltip=None):
  cb=ttk.Checkbutton(outer,variable=vars[key],text=text);cb.grid(row=r,column=1,sticky='w',padx=(indent,25),pady=3);widgets[key]=cb
  lab=ttk.Label(outer,text=status_text,anchor='e',width=4);lab.grid(row=r,column=2,sticky='e',pady=3)
  if tooltip:ToolTip(lab,tooltip)
 row(2,'repository','Aktualizovat repozitář',0,str(status['missing']),'Počet souborů, které jsou na disku, ale nejsou v Media Poolu.')
 row(3,'timeline','Vytvořit timeline',0,'✓' if status['timeline'] else '✕')
 row(4,'voice','Aktivovat Voice Isolation',24,'✓' if status['voice'] else '✕')
 row(5,'deliver','Nastavit DELIVERY',0,'✓' if status['deliver'] else '✕')
 def deps(*_):widgets['voice'].configure(state='normal' if timeline.get() else 'disabled')
 timeline.trace_add('write',deps);deps()
 buttons=ttk.Frame(outer);buttons.grid(row=6,column=0,columnspan=3,pady=(16,0))
 def ok(*_):result[0]={k:v.get() for k,v in vars.items()};root.destroy()
 def cancel(*_):result[0]=None;root.destroy()
 ttk.Button(buttons,text='OK',command=ok,width=13).pack(side='left',padx=6);ttk.Button(buttons,text='Cancel',command=cancel,width=13).pack(side='left',padx=6)
 root.bind('<Return>',ok);root.bind('<Escape>',cancel);root.protocol('WM_DELETE_WINDOW',cancel);m.center(root);root.mainloop();return result[0]

def _create_timeline(mp,master,shoot,name,voice):
 if _CREATOR is None:raise RuntimeError('Timeline creator není inicializován.')
 timeline=_CREATOR(mp,master,shoot,name)
 if voice:timeline=timeline_audio.configure(timeline)
 return timeline

def build(query,keep):
 root,folder,timeout,alive,deliver_preset,deliver_folder=m.cfg();src=m.resolve_project(root,query);name=src.name;life.begin_log_session('run',name);life.log('PROJECT_RESOLVED',query=query,name=name)
 shoot=next((x for x in src.iterdir() if x.is_dir() and x.name.casefold()=='shooting'),src/'SHOOTING')
 if not shoot.is_dir():raise RuntimeError(f'Chybí SHOOTING: {shoot}')
 dirs=[shoot]+[d for dn in m.OPTIONAL for d in src.iterdir() if d.is_dir() and d.name.casefold()==dn.casefold()];fs={m.norm(p):p for d in dirs for p in m.allfiles(d)};r=m.ensure(name,timeout);life.put(busy=True,project=name,stage='Kontroluji projekt…',keep_mode=keep,alive_timeout=alive)
 try:
  pm=r.GetProjectManager();pm.GotoRootFolder()
  if folder and not pm.OpenFolder(folder):raise RuntimeError(f'Project Library folder nenalezen: {folder}')
  projects=pm.GetProjectListInCurrentFolder() or [];existing=next((x for x in projects if x.casefold()==name.casefold()),None)
  if not existing:
   pr=pm.CreateProject(name)
   if pr is None:raise RuntimeError(f'Nelze vytvořit projekt: {name}')
   mp=pr.GetMediaPool();master=mp.GetRootFolder();missing=set(fs);counter=[0];imported=sum(m.sync(mp,master,d,missing,counter,len(missing)) for d in dirs);tn=m.nodate(name) or name
   _create_timeline(mp,master,shoot,tn,True);m.apply_deliver(pr,src,deliver_preset,deliver_folder)
   if not pm.SaveProject():raise RuntimeError('SaveProject() selhal.')
   life.log('PROJECT_CREATED',name=name,imported=imported,timeline=tn);print(f'[OK] Projekt vytvořen: {name} | Timeline: {tn} | Média: {imported}')
  else:
   pr=pm.LoadProject(existing)
   if pr is None:raise RuntimeError(f'Existující projekt nelze otevřít: {existing}')
   mp=pr.GetMediaPool();master=mp.GetRootFolder();have=set();m.present(master,have);missing=set(fs)-have;base=m.nodate(name) or name;st=_status(pr,base,missing,src,deliver_folder,shoot);life.log('PROJECT_EXISTS',name=existing,**st)
   actions=ask(existing,st)
   if actions is None:print('[OK] Aktualizace projektu zrušena.');return m.finish(r,keep,alive)
   changed=False
   if actions['repository']:
    if missing:
     counter=[0];imported=sum(m.sync(mp,master,d,missing,counter,len(missing)) for d in dirs if any(m.norm(p) in missing for p in m.allfiles(d)));life.log('SYNC_DONE',imported=imported);print(f'[OK] Doplněno médií: {imported}');changed=changed or imported>0
    else:print('[OK] Repozitář je aktuální.')
   if actions['timeline']:
    tn=_unique_timeline_name(pr,base);_create_timeline(mp,master,shoot,tn,actions['voice']);life.log('TIMELINE_UPDATE_CREATED',timeline=tn,voice=actions['voice']);print(f'[OK] Vytvořena timeline: {tn}');changed=True
   if actions['deliver']:
    m.apply_deliver(pr,src,deliver_preset,deliver_folder);changed=True
   if changed and not pm.SaveProject():raise RuntimeError('SaveProject() selhal.')
   if not changed:print('[OK] Nebyla vybrána žádná změna.')
 finally:life.put(busy=False,stage='Hotovo')
 m.finish(r,keep,alive)
