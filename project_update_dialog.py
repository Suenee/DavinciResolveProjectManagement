#!/usr/bin/env python3
from __future__ import annotations
import tkinter as tk
from tkinter import ttk,filedialog
import managed_builder as m
import intro_fingerprint
from i18n import _

GREEN='#148a21'
RED='#d91e18'


class ToolTip:
 def __init__(self,widget,text):
  self.widget=widget;self.text=text;self.tip=None
  widget.bind('<Enter>',self.show);widget.bind('<Leave>',self.hide)
 def show(self,*_):
  if self.tip:return
  x=self.widget.winfo_rootx()+20;y=self.widget.winfo_rooty()+22
  self.tip=tk.Toplevel(self.widget);self.tip.wm_overrideredirect(True);self.tip.wm_geometry(f'{x:+d}{y:+d}')
  ttk.Label(self.tip,text=self.text,padding=(7,4)).pack()
 def hide(self,*_):
  if self.tip:self.tip.destroy();self.tip=None


def ask(project_name,status):
 result=[None]
 root=tk.Tk();root.title(_('Project update — DavinciResolveProjectManagement 1.23'));root.resizable(False,False)
 bg=root.cget('bg')
 outer=tk.Frame(root,bg=bg,padx=20,pady=12);outer.grid(row=0,column=0)
 title_font=('Segoe UI',11,'bold');head_font=('Segoe UI',9,'bold');status_font=('Segoe UI Symbol',13,'bold');number_font=('Segoe UI',10,'bold')

 tk.Label(outer,text=project_name,font=title_font,bg=bg).grid(row=0,column=0,columnspan=3,pady=(0,9))
 tk.Label(outer,text=_('Action'),font=head_font,bg=bg).grid(row=1,column=1,sticky='w',padx=(4,24),pady=(0,2))
 tk.Label(outer,text=_('Status'),font=head_font,bg=bg,width=5,anchor='center').grid(row=1,column=2,pady=(0,2))

 intros=intro_fingerprint.list_intros();intro_names=[p.name for p in intros]
 repo=tk.BooleanVar(value=status['missing']>0);timeline=tk.BooleanVar(value=not status['timeline']);voice=tk.BooleanVar(value=True);intro=tk.BooleanVar(value=False);deliver=tk.BooleanVar(value=not status['deliver']);intro_name=tk.StringVar(value=intro_names[0] if intro_names else '')
 vars={'repository':repo,'timeline':timeline,'voice':voice,'intro':intro,'deliver':deliver};widgets={}

 def status_label(r,ready=None,number=None,tooltip=None):
  if number is not None:lab=tk.Label(outer,text=str(number),font=number_font,bg=bg,fg=GREEN if number==0 else RED,width=5,anchor='center')
  else:lab=tk.Label(outer,text='✓' if ready else '✕',font=status_font,bg=bg,fg=GREEN if ready else RED,width=5,anchor='center')
  lab.grid(row=r,column=2,sticky='nsew',pady=0)
  if tooltip:ToolTip(lab,tooltip)

 def row(r,key,text,indent,ready=None,number=None,tooltip=None):
  cb=ttk.Checkbutton(outer,variable=vars[key],text=text);cb.grid(row=r,column=1,sticky='w',padx=(indent,24),pady=0);widgets[key]=cb;status_label(r,ready=ready,number=number,tooltip=tooltip)

 row(2,'repository',_('Update repository'),0,number=status['missing'],tooltip=_('Number of files present on disk but missing from the Media Pool.'))
 row(3,'timeline',_('Create timeline'),0,ready=status['timeline'])
 row(4,'voice',_('Enable Voice Isolation'),24,ready=status['voice'])
 row(5,'intro',_('Cut intro'),48,ready=False,tooltip=_('The intro is detected by audio fingerprint in the first 2 minutes of the timeline.'))
 combo=ttk.Combobox(outer,textvariable=intro_name,values=intro_names,state='readonly',width=28)
 combo.grid(row=6,column=1,sticky='w',padx=(72,24),pady=(1,2))
 row(7,'deliver',_('Set DELIVERY'),0,ready=status['deliver'])

 def deps(*_):
  timeline_on=timeline.get();voice_on=voice.get();available=bool(intros)
  widgets['voice'].configure(state='normal' if timeline_on else 'disabled')
  widgets['intro'].configure(state='normal' if timeline_on and voice_on and available else 'disabled')
  combo.configure(state='readonly' if timeline_on and voice_on and intro.get() and available else 'disabled')
  if not (timeline_on and voice_on and available):intro.set(False)
 timeline.trace_add('write',deps);voice.trace_add('write',deps);intro.trace_add('write',deps);deps()

 if not intros:ToolTip(widgets['intro'],_('No supported intro was found in IntroDetection.Folder.'))
 buttons=ttk.Frame(outer);buttons.grid(row=8,column=0,columnspan=3,pady=(9,0))
 def ok(*_):
  chosen=None
  if intro.get() and intro_name.get():chosen=next((str(p) for p in intros if p.name==intro_name.get()),None)
  result[0]={k:v.get() for k,v in vars.items()};result[0]['intro_reference']=chosen;root.destroy()
 def cancel(*_):result[0]=None;root.destroy()
 ttk.Button(buttons,text='OK',command=ok,width=12).pack(side='left',padx=6);ttk.Button(buttons,text=_('Cancel'),command=cancel,width=12).pack(side='left',padx=6)
 root.bind('<Return>',ok);root.bind('<Escape>',cancel);root.protocol('WM_DELETE_WINDOW',cancel);m.center(root);root.focus_force();root.mainloop();return result[0]


def choose_intro(project_name,intros):
 result=[None]
 root=tk.Tk();root.title(_('Intro selection — DavinciResolveProjectManagement 1.23'));root.resizable(False,False)
 frame=ttk.Frame(root,padding=16);frame.grid(row=0,column=0)
 ttk.Label(frame,text=project_name,font=('Segoe UI',10,'bold')).grid(row=0,column=0,sticky='w',pady=(0,8))
 ttk.Label(frame,text=_('The project name does not match any rule. Select an intro:')).grid(row=1,column=0,sticky='w',pady=(0,6))
 names=[_('No intro')]+[p.name for p in intros];value=tk.StringVar(value=names[0])
 combo=ttk.Combobox(frame,textvariable=value,values=names,state='readonly',width=38);combo.grid(row=2,column=0,sticky='ew',pady=(0,10))
 buttons=ttk.Frame(frame);buttons.grid(row=3,column=0)
 def ok(*_):
  selected=value.get();result[0]=next((str(p) for p in intros if p.name==selected),None);root.destroy()
 ttk.Button(buttons,text='OK',command=ok,width=12).pack()
 root.bind('<Return>',ok);root.protocol('WM_DELETE_WINDOW',ok);m.center(root);root.focus_force();root.mainloop();return result[0]


def choose_title(project_name,candidates,titles_template):
 result=[None];root=tk.Tk();root.title(_('Title image selection — DavinciResolveProjectManagement 1.23'));root.resizable(False,False)
 frame=ttk.Frame(root,padding=16);frame.grid(row=0,column=0)
 ttk.Label(frame,text=project_name,font=('Segoe UI',10,'bold')).grid(row=0,column=0,columnspan=2,sticky='w',pady=(0,8))
 ttk.Label(frame,text=_('Select title image:')).grid(row=1,column=0,columnspan=2,sticky='w',pady=(0,6))
 labels=[p.name for p in candidates];value=tk.StringVar(value=labels[0] if labels else 'Skip')
 combo=ttk.Combobox(frame,textvariable=value,values=labels+['Skip'],state='readonly',width=58);combo.grid(row=2,column=0,columnspan=2,sticky='ew',pady=(0,10))
 def browse():
  path=filedialog.askopenfilename(parent=root,title=_('Select title image'),filetypes=[(_('Images'),'*.jpg *.jpeg *.png *.webp *.tif *.tiff *.bmp'),(_('All files'),'*.*')])
  if path:result[0]=path;root.destroy()
 def ok(*_):
  selected=value.get();result[0]=next((str(p) for p in candidates if p.name==selected),None);root.destroy()
 ttk.Button(frame,text=_('Choose file…'),command=browse,width=16).grid(row=3,column=0,padx=(0,6))
 ttk.Button(frame,text='OK / Skip',command=ok,width=16).grid(row=3,column=1,padx=(6,0))
 root.bind('<Return>',ok);root.protocol('WM_DELETE_WINDOW',ok);m.center(root);root.focus_force();root.mainloop();return result[0]
