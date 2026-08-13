#!/usr/bin/env python3
from __future__ import annotations
import subprocess, sys, time, tkinter as tk
from pathlib import Path
APP=Path(__file__).resolve().parent
sys.path.insert(0,str(APP))
import importlib.util
spec=importlib.util.spec_from_file_location('life',APP/'resolve_lifecycle'); life=importlib.util.module_from_spec(spec); spec.loader.exec_module(life)

def show_wait(message,stage):
 root=tk.Tk(); root.title('DaVinci Resolve'); root.resizable(False,False)
 tk.Label(root,text=message,font=('Segoe UI',14,'bold')).pack(padx=30,pady=(20,5))
 tk.Label(root,text='🐌  ·  ·  ·  💨',font=('Segoe UI Emoji',18)).pack(pady=4)
 status=tk.StringVar(value=stage); tk.Label(root,textvariable=status,font=('Segoe UI',10)).pack(padx=30,pady=(4,8))
 bar=tk.Canvas(root,width=360,height=12,highlightthickness=0); bar.pack(padx=25,pady=(0,20)); rect=bar.create_rectangle(0,0,70,12,fill='#808080',outline='')
 pos=[0]
 def tick():
  pos[0]=(pos[0]+9)%290; bar.coords(rect,pos[0],0,pos[0]+70,12); root.after(60,tick)
 tick(); root.update(); return root,status

def main():
 s=life.state()
 if s.get('owned') and s.get('mode')=='headless' and life.pid_running(s.get('pid')):
  if s.get('busy'):
   root,status=show_wait('Makám za tebe…',s.get('stage') or s.get('project') or 'Pracuji na projektu')
   while True:
    root.update(); s=life.state()
    if not s.get('busy'):break
    time.sleep(.25)
  else:
   root,status=show_wait('Už běžím…','Přepínám DaVinci Resolve do grafického režimu')
  status.set('Ukončuji headless režim…'); root.update(); life.stop_owned(); status.set('Spouštím DaVinci Resolve…'); root.update(); life.start_gui(); time.sleep(2); root.destroy(); return 0
 if life.any_resolve():
  print('DaVinci Resolve is already running.'); return 0
 life.start_gui(); return 0
if __name__=='__main__':raise SystemExit(main())
