#!/usr/bin/env python3
from __future__ import annotations
import tkinter as tk
from tkinter import ttk
import managed_builder as m

GREEN='#148a21'
RED='#d91e18'


class ToolTip:
 def __init__(self,widget,text):
  self.widget=widget;self.text=text;self.tip=None
  widget.bind('<Enter>',self.show);widget.bind('<Leave>',self.hide)
 def show(self,*_):
  if self.tip:return
  x=self.widget.winfo_rootx()+20;y=self.widget.winfo_rooty()+22
  self.tip=tk.Toplevel(self.widget);self.tip.wm_overrideredirect(True);self.tip.wm_geometry(f'+{x}+{y}')
  ttk.Label(self.tip,text=self.text,padding=(7,4)).pack()
 def hide(self,*_):
  if self.tip:self.tip.destroy();self.tip=None


def ask(project_name,status):
 result=[None]
 root=tk.Tk();root.title('Aktualizace projektu');root.resizable(False,False)
 bg=root.cget('bg')
 outer=tk.Frame(root,bg=bg,padx=20,pady=12);outer.grid(row=0,column=0)
 title_font=('Segoe UI',11,'bold')
 head_font=('Segoe UI',9,'bold')
 status_font=('Segoe UI Symbol',13,'bold')
 number_font=('Segoe UI',10,'bold')

 tk.Label(outer,text=project_name,font=title_font,bg=bg).grid(row=0,column=0,columnspan=3,pady=(0,9))
 tk.Label(outer,text='Akce',font=head_font,bg=bg).grid(row=1,column=1,sticky='w',padx=(4,24),pady=(0,2))
 tk.Label(outer,text='Stav',font=head_font,bg=bg,width=5,anchor='center').grid(row=1,column=2,pady=(0,2))

 repo=tk.BooleanVar(value=status['missing']>0)
 timeline=tk.BooleanVar(value=not status['timeline'])
 voice=tk.BooleanVar(value=True)
 intro=tk.BooleanVar(value=not status['has_set'])
 deliver=tk.BooleanVar(value=not status['deliver'])
 vars={'repository':repo,'timeline':timeline,'voice':voice,'intro':intro,'deliver':deliver}
 widgets={}

 def status_label(r,ready=None,number=None,tooltip=None):
  if number is not None:
   lab=tk.Label(outer,text=str(number),font=number_font,bg=bg,fg=GREEN if number==0 else RED,width=5,anchor='center')
  else:
   lab=tk.Label(outer,text='✓' if ready else '✕',font=status_font,bg=bg,fg=GREEN if ready else RED,width=5,anchor='center')
  lab.grid(row=r,column=2,sticky='nsew',pady=0)
  if tooltip:ToolTip(lab,tooltip)

 def row(r,key,text,indent,ready=None,number=None,tooltip=None):
  cb=ttk.Checkbutton(outer,variable=vars[key],text=text)
  cb.grid(row=r,column=1,sticky='w',padx=(indent,24),pady=0)
  widgets[key]=cb
  status_label(r,ready=ready,number=number,tooltip=tooltip)

 row(2,'repository','Aktualizovat repozitář',0,number=status['missing'],tooltip='Počet souborů, které jsou na disku, ale nejsou v Media Poolu.')
 row(3,'timeline','Vytvořit timeline',0,ready=status['timeline'])
 row(4,'voice','Aktivovat Voice Isolation',24,ready=status['voice'])
 row(5,'intro','Vystřihnout znělku',48,ready=status['intro'],tooltip='Automatická detekce znělky je dostupná pouze pro SHOOTING bez SET xx.' if status['has_set'] else None)
 row(6,'deliver','Nastavit DELIVERY',0,ready=status['deliver'])

 def deps(*_):
  widgets['voice'].configure(state='normal' if timeline.get() else 'disabled')
  widgets['intro'].configure(state='normal' if timeline.get() and voice.get() and not status['has_set'] else 'disabled')
 timeline.trace_add('write',deps);voice.trace_add('write',deps);deps()

 buttons=ttk.Frame(outer);buttons.grid(row=7,column=0,columnspan=3,pady=(9,0))
 def ok(*_):result[0]={k:v.get() for k,v in vars.items()};root.destroy()
 def cancel(*_):result[0]=None;root.destroy()
 ttk.Button(buttons,text='OK',command=ok,width=12).pack(side='left',padx=6)
 ttk.Button(buttons,text='Cancel',command=cancel,width=12).pack(side='left',padx=6)

 root.bind('<Return>',ok);root.bind('<Escape>',cancel);root.protocol('WM_DELETE_WINDOW',cancel)
 m.center(root)
 root.focus_force()
 root.mainloop()
 return result[0]
