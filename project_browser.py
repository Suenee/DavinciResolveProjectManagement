#!/usr/bin/env python3
from __future__ import annotations
import configparser, os, re, shutil, tkinter as tk, traceback
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont
import ui_windows
import resolve_lifecycle as life
import i18n
from i18n import _
from project_paths import active_root, configured_roots, named_paths

APP=Path(__file__).resolve().parent; CONFIG=APP/'config.ini'
DATE_RE=re.compile(r'^(\d{8})\s+(.+?)(?:\s+(\d+))?$'); MEDIA_EXT={'.mp4','.mov','.mxf','.avi','.mkv','.mts','.m2ts','.wav','.mp3','.aac','.flac','.jpg','.jpeg','.png','.tif','.tiff','.bmp','.webp'}
INVALID_NAME=re.compile(r'[<>:"/\\|?*]')
def _config():
 p=configparser.ConfigParser(interpolation=None);p.optionxform=str;p.read(CONFIG,encoding='utf-8');return p
def project_root():return active_root(_config())
def created(p):
 try:return p.stat().st_ctime
 except OSError:return 0
def projects(root):
 try:return [p for p in root.iterdir() if p.is_dir()]
 except OSError:return []
def _valid_date(text):
 try:datetime.strptime(text,'%Y%m%d');return True
 except ValueError:return False
def _series_parts(name):
 m=DATE_RE.match(name.strip());return (m.group(1),m.group(2).strip(),int(m.group(3)) if m.group(3) else None) if m else (None,name.strip(),None)
def _bases(root):
 out=[];seen=set()
 for p in projects(root):
  _,b,_=_series_parts(p.name);k=b.casefold()
  if b and k not in seen:seen.add(k);out.append(b)
 return sorted(out,key=str.casefold)
def _next_series(base,root):
 nums=[]
 for p in projects(root):
  _,b,n=_series_parts(p.name)
  if b.casefold()==base.casefold() and n is not None:nums.append(n)
 return max(nums,default=0)+1
def propose_name(raw,root):
 raw=' '.join(raw.strip().split())
 if not raw:return ''
 date,base,num=_series_parts(raw)
 if not date:date=datetime.now().strftime('%Y%m%d');base=raw
 if num is None:num=_next_series(base,root)
 return f'{date} {base} {num}'
def unique_name(name,root):return not any(p.name.casefold()==name.casefold() for p in projects(root))
def ask_new_project(parent,root):
 win=tk.Toplevel(parent);win.title(_('New project — DavinciResolveProjectManagement 1.26'));win.resizable(False,False);result=[None];confirmed=[False];popup=[None];box=ttk.Frame(win,padding=18);box.grid();ttk.Label(box,text=_('Project name:')).grid(row=0,column=0,sticky='w');var=tk.StringVar();entry=ttk.Entry(box,textvariable=var,width=54);entry.grid(row=1,column=0,columnspan=2,sticky='ew',pady=(4,2));msg=tk.Label(box,text='',fg='#c00000',anchor='w',height=1);msg.grid(row=2,column=0,columnspan=2,sticky='w',pady=(3,0));buttons=ttk.Frame(box);buttons.grid(row=3,column=0,columnspan=2,pady=(12,0));okb=ttk.Button(buttons,text='OK',width=14);okb.pack(side='left',padx=6);ttk.Button(buttons,text=_('Cancel'),width=14,command=win.destroy).pack(side='left',padx=6)
 def hide_popup():
  if popup[0] is not None:
   try:popup[0].destroy()
   except:pass
   popup[0]=None
 def show_popup(items):
  hide_popup()
  if not items:return
  win.update_idletasks();x=entry.winfo_rootx();y=entry.winfo_rooty()+entry.winfo_height();w=entry.winfo_width();pop=tk.Toplevel(win);popup[0]=pop;pop.overrideredirect(True);pop.transient(win);lst=tk.Listbox(pop,height=min(6,len(items)),exportselection=False,activestyle='dotbox')
  for item in items:lst.insert('end',item)
  lst.pack(fill='both',expand=True);pop.geometry(f'{w}x{min(6,len(items))*22+4}+{x}+{y}');pop.lift()
  def use(*_):
   s=lst.curselection()
   if s:var.set(lst.get(s[0]));hide_popup();entry.focus_set();entry.icursor('end')
  lst.bind('<Double-1>',use);lst.bind('<Return>',use)
 def refresh(*_):
  if confirmed[0]:confirmed[0]=False;msg.configure(text='')
  q=var.get().strip().casefold()
  if not q or DATE_RE.match(var.get().strip()):hide_popup();return
  show_popup([x for x in _bases(root) if q in x.casefold()][:8])
 def submit(*_):
  hide_popup();value=var.get().strip()
  if not value:return
  if not confirmed[0]:
   var.set(propose_name(value,root));confirmed[0]=True;msg.configure(text=_('Is the project name correct?'));win.bell();entry.icursor('end');entry.focus_set();return
  date,_,_=_series_parts(value)
  if not date or not _valid_date(date):msg.configure(text=_('The name must start with a valid YYYYMMDD date.'));win.bell();return
  if not unique_name(value,root):msg.configure(text=_('The project name already exists.'));win.bell();return
  target=root/value
  try:(target/'SHOOTING').mkdir(parents=True,exist_ok=False)
  except Exception as e:msg.configure(text=_('Cannot create project: {error}').format(error=e));win.bell();return
  result[0]=target;win.destroy()
 var.trace_add('write',refresh);okb.configure(command=submit);win.bind('<Return>',submit);win.bind('<Escape>',lambda e:win.destroy());win.protocol('WM_DELETE_WINDOW',win.destroy);ui_windows.center_and_place_above_resolve(win);entry.focus_set();win.grab_set();parent.wait_window(win);return result[0]
def _media_files(folder):return [p for p in folder.rglob('*') if p.is_file() and p.suffix.casefold() in MEDIA_EXT]
def _same_volume(a,b):return os.path.splitdrive(str(a.resolve()))[0].casefold()==os.path.splitdrive(str(b.resolve()))[0].casefold()
def _writable_target(root):
 try:root.mkdir(parents=True,exist_ok=True);probe=root/'.drpm_write_test.tmp';probe.write_bytes(b'1');probe.unlink();return True
 except Exception:return False
def import_external(parent,root):
 src_text=filedialog.askdirectory(parent=parent,title=_('Open media folder'))
 if not src_text:return None
 src=Path(src_text);files=_media_files(src)
 if not files:messagebox.showerror(_('Open'),_('No supported media files were found in the selected folder.'),parent=parent);return None
 move=messagebox.askyesnocancel(_('Open'),_('Found {count} media files.\n\nMove them to the standard project folder?').format(count=len(files)),parent=parent)
 if move is None:return None
 if not move:return {'external':src,'name':src.name}
 target=ask_new_project(parent,root)
 if not target:return None
 if not _writable_target(target):messagebox.showerror(_('Open'),_('The destination folder is not writable.'),parent=parent);return None
 shoot=target/'SHOOTING';same=_same_volume(src,shoot);total=sum(p.stat().st_size for p in files)
 if not same:
  free=shutil.disk_usage(shoot).free;reserve=max(64*1024*1024,int(total*.02))
  if free<total+reserve:messagebox.showerror(_('Open'),_('There is not enough free space on the destination drive.'),parent=parent);return None
 win=tk.Toplevel(parent);win.title(_('Move media'));frm=ttk.Frame(win,padding=18);frm.pack();label=ttk.Label(frm,text=_('Preparing move…'));label.pack(anchor='w');bar=ttk.Progressbar(frm,length=430,maximum=max(total,1));bar.pack(pady=(8,0));ui_windows.center_and_place_above_resolve(win);win.update();done=0
 try:
  for source in files:
   rel=source.relative_to(src);dest=shoot/rel;dest.parent.mkdir(parents=True,exist_ok=True);size=source.stat().st_size;label.configure(text=str(rel));win.update()
   if same:
    if dest.exists():raise RuntimeError(_('Destination file already exists: {path}').format(path=dest))
    os.replace(source,dest)
   else:
    tmp=dest.with_name(dest.name+'.drpm-partial');shutil.copy2(source,tmp)
    if tmp.stat().st_size!=size:raise RuntimeError(f'Ověření velikosti selhalo: {source}')
    os.replace(tmp,dest)
    if dest.stat().st_size!=size:raise RuntimeError(f'Ověření cíle selhalo: {dest}')
    source.unlink()
   done+=size;bar['value']=done;win.update()
 except Exception as e:win.destroy();messagebox.showerror(_('Move media'),_('The move was safely stopped.\n\n{error}').format(error=e),parent=parent);return None
 win.destroy();return {'project':target}
def _safe_relative_name(value):
 value=value.strip()
 return bool(value) and not Path(value).is_absolute() and '..' not in Path(value).parts and INVALID_NAME.search(value) is None
def settings(parent,on_saved=None):
 p=_config();win=tk.Toplevel(parent);win.title(_('Settings — DavinciResolveProjectManagement 1.26'));win.resizable(False,False)
 outer=ttk.Frame(win,padding=12);outer.grid();values={};widgets={}
 left=ttk.Frame(outer);right=ttk.Frame(outer);left.grid(row=0,column=0,sticky='n',padx=(0,6));right.grid(row=0,column=1,sticky='n',padx=(6,0))
 lang_codes=i18n.available_languages();lang_labels={'auto':_('Automatic (Windows)'),'cs':_('Czech'),'en':_('English')};current_lang=p.get('General','Language',fallback='auto').casefold();language_var=tk.StringVar(value=lang_labels.get(current_lang,_('Automatic (Windows)')))
 def group(parent,title):g=ttk.LabelFrame(parent,text=title,padding=9);g.pack(fill='x',pady=(0,8));g.columnconfigure(1,weight=1);return g
 def text(g,row,sec,key,title,width=31):
  ttk.Label(g,text=title+':').grid(row=row,column=0,sticky='w',padx=(0,8),pady=2);v=tk.StringVar(value=p.get(sec,key,fallback=''));e=ttk.Entry(g,textvariable=v,width=width);e.grid(row=row,column=1,columnspan=2,sticky='ew',pady=2);values[(sec,key)]=v;widgets[(sec,key)]=e
 def number(g,row,sec,key,title,lo,hi,display=None,increment=1):
  ttk.Label(g,text=title+':').grid(row=row,column=0,sticky='w',padx=(0,8),pady=2);raw=p.get(sec,key,fallback=str(lo));v=tk.StringVar(value=str(display(raw) if display else raw));e=ttk.Spinbox(g,from_=lo,to=hi,increment=increment,textvariable=v,width=12);e.grid(row=row,column=1,columnspan=2,sticky='ew',pady=2);values[(sec,key)]=v;widgets[(sec,key)]=e
 def folder(g,row,sec,key,title,year_template=False):
  ttk.Label(g,text=title+':').grid(row=row,column=0,sticky='w',padx=(0,8),pady=2);v=tk.StringVar(value=p.get(sec,key,fallback=''));e=ttk.Entry(g,textvariable=v,width=28);e.grid(row=row,column=1,sticky='ew',pady=2);values[(sec,key)]=v;widgets[(sec,key)]=e
  def pick():
   raw=v.get();initial=raw.replace('%Y',str(datetime.now().year)) if year_template else raw;x=filedialog.askdirectory(parent=win,initialdir=initial if Path(initial).is_dir() else None)
   if x:v.set(str(Path(x).parent/'%Y') if year_template and Path(x).name.isdigit() else x)
  ttk.Button(g,text='…',width=3,command=pick).grid(row=row,column=2,padx=(4,0))
 gg=group(left,_('Language'));ttk.Label(gg,text=_('UI Language:')).grid(row=0,column=0,sticky='w',padx=(0,8));ttk.Combobox(gg,textvariable=language_var,values=[lang_labels[x] for x in lang_codes],state='readonly',width=22).grid(row=0,column=1,sticky='ew')
 gp=group(left,_('Project'))
 path_rows=[]
 def add_path_row(key='',path=''):
  row=len(path_rows);kv=tk.StringVar(value=key);pv=tk.StringVar(value=str(path))
  ttk.Entry(gp,textvariable=kv,width=12).grid(row=row,column=0,sticky='ew',padx=(0,4),pady=2)
  ttk.Entry(gp,textvariable=pv,width=28).grid(row=row,column=1,sticky='ew',pady=2)
  def pick():
   x=filedialog.askdirectory(parent=win,initialdir=pv.get() if Path(pv.get()).is_dir() else None)
   if x:pv.set(x)
  ttk.Button(gp,text='…',width=3,command=pick).grid(row=row,column=2,padx=(4,0))
  path_rows.append((kv,pv))
 for key,path in configured_roots(p):add_path_row(key,path)
 if not path_rows:add_path_row('Main','')
 text(gp,len(path_rows),'DaVinciResolve','ResolveProjectFolder','Resolve Project Library')
 ttk.Label(gp,text='Resolve EXE:').grid(row=2,column=0,sticky='w',padx=(0,8),pady=2);rv=tk.StringVar(value=p.get('DaVinciResolve','ResolveExe',fallback=''));rexe=ttk.Entry(gp,textvariable=rv,width=28);rexe.grid(row=2,column=1,sticky='ew');values[('DaVinciResolve','ResolveExe')]=rv;widgets[('DaVinciResolve','ResolveExe')]=rexe
 def resolve_pick():
  found=filedialog.askopenfilename(parent=win,title=_('Select Resolve.exe'),filetypes=[('DaVinci Resolve','Resolve.exe'),('Executable','*.exe')])
  if found and Path(found).name.casefold()=='resolve.exe':rv.set(found)
 ttk.Button(gp,text='…',width=3,command=resolve_pick).grid(row=2,column=2,padx=(4,0))
 gd=group(left,'DaVinci Resolve');number(gd,0,'DaVinciResolve','StartupTimeout','Startup timeout (s)',10,600);number(gd,1,'DaVinciResolve','AliveTimeout','Alive timeout (s)',0,86400)
 gdel=group(left,'DELIVERY');text(gdel,0,'Deliver','Preset','Preset');text(gdel,1,'Deliver','Folder',_('Folder'))
 gl=group(left,_('Logging'));lv=tk.StringVar(value=p.get('Logging','Mode',fallback='single'));ttk.Label(gl,text=_('Mode:')).grid(row=0,column=0,sticky='w',padx=(0,8));ttk.Combobox(gl,textvariable=lv,values=('off','single','all'),state='readonly',width=22).grid(row=0,column=1,sticky='ew');values[('Logging','Mode')]=lv
 gt=group(right,'Timeline');number(gt,0,'Timeline','VoiceIsolationAmount','Voice Isolation (%)',0,100);bv=tk.BooleanVar(value=p.getboolean('Timeline','CreateCleanAudioTrack',fallback=True));ttk.Label(gt,text=_('Clean audio track:')).grid(row=1,column=0,sticky='w');ttk.Checkbutton(gt,variable=bv).grid(row=1,column=1,sticky='w');values[('Timeline','CreateCleanAudioTrack')]=bv;text(gt,2,'Timeline','CleanAudioTrackName',_('Audio track name'))
 ga=group(right,_('Title image / End credits'));folder(ga,0,'TimelineAssets','TitlesRoot','Titles',True);number(ga,1,'TimelineAssets','TitleDurationSeconds',_('Title duration (s)'),1,600);number(ga,2,'TimelineAssets','TitleCandidateCount',_('TOP candidates'),1,20);number(ga,3,'TimelineAssets','TitleAutoMatchScore','Auto match (%)',0,100,lambda x:round(float(x)*100) if float(x)<=1 else round(float(x)));number(ga,4,'TimelineAssets','YearBoundaryToleranceDays',_('Year boundary (days)'),0,60);text(ga,5,'TimelineAssets','EndCreditsFile',_('End credits file'));number(ga,6,'TimelineAssets','EndCreditsDurationSeconds',_('End credits duration (s)'),1,600)
 gi=group(right,_('Intro'));intro_paths=', '.join(f'{key}: {path}' for key,path in named_paths(p,'IntroPaths')) or '-';ttk.Label(gi,text=_('Intro paths:')).grid(row=0,column=0,sticky='nw',padx=(0,8),pady=2);ttk.Label(gi,text=intro_paths,wraplength=260,justify='left').grid(row=0,column=1,columnspan=2,sticky='w',pady=2);number(gi,1,'IntroDetection','SearchWindowSeconds',_('Search window (min)'),1,5,lambda x:max(1,min(5,round(float(x)/60))));number(gi,2,'IntroDetection','MinConfidence',_('Min. confidence (%)'),0,100,lambda x:round(float(x)*100) if float(x)<=1 else round(float(x)))
 gs=group(right,_('Silence Trim'));sv=tk.BooleanVar(value=p.getboolean('SilenceTrim','Enabled',fallback=True));ttk.Label(gs,text=_('Enabled:')).grid(row=0,column=0,sticky='w');ttk.Checkbutton(gs,variable=sv).grid(row=0,column=1,sticky='w');values[('SilenceTrim','Enabled')]=sv
 number(gs,1,'SilenceTrim','SearchSeconds',_('Detection range (s)'),5,120)
 number(gs,2,'SilenceTrim','ThresholdDb',_('Silence level (dBFS)'),-60,-20)
 number(gs,3,'SilenceTrim','MinimumSoundSeconds',_('Minimum sound (s)'),0.05,2.0,increment=0.05)
 number(gs,4,'SilenceTrim','KeepBeforeSeconds',_('Space before speech (s)'),0.0,5.0,increment=0.05)
 number(gs,5,'SilenceTrim','KeepAfterSeconds',_('Space after speech (s)'),0.0,5.0,increment=0.05)
 def dependencies(*_):
  widgets[('Timeline','CleanAudioTrackName')].configure(state='normal' if bv.get() else 'disabled')
  for key in ('SearchSeconds','ThresholdDb','MinimumSoundSeconds','KeepBeforeSeconds','KeepAfterSeconds'):
   widgets[('SilenceTrim',key)].configure(state='normal' if sv.get() else 'disabled')
 bv.trace_add('write',dependencies);sv.trace_add('write',dependencies);dependencies()
 def save():
  chosen_lang=next((code for code,label in lang_labels.items() if label==language_var.get()),'auto')
  if not p.has_section('General'):p.add_section('General')
  p.set('General','Language',chosen_lang)
  roots=[];keys=set()
  for kv,pv in path_rows:
   key=kv.get().strip();raw=pv.get().strip()
   if not key and not raw:continue
   if not key or not raw or key.casefold() in keys:messagebox.showerror(_('Settings'),_('Project path names must be unique and both name and path are required.'),parent=win);return
   keys.add(key.casefold());roots.append((key,raw))
  if not roots or not any(Path(raw).is_dir() for _,raw in roots):messagebox.showerror(_('Settings'),_('At least one configured project path must exist.'),parent=win);return
  resolve_exe=rv.get().strip();titles=values[('TimelineAssets','TitlesRoot')].get().strip()
  if '%Y' not in titles:messagebox.showerror(_('Settings'),_('Titles must contain the %Y placeholder.'),parent=win);return
  if resolve_exe and (not Path(resolve_exe).is_file() or Path(resolve_exe).name.casefold()!='resolve.exe'):messagebox.showerror(_('Settings'),_('Resolve EXE must point to Resolve.exe.'),parent=win);return
  try:
   sr=float(values[('SilenceTrim','SearchSeconds')].get());st=float(values[('SilenceTrim','ThresholdDb')].get());ms=float(values[('SilenceTrim','MinimumSoundSeconds')].get());kb=float(values[('SilenceTrim','KeepBeforeSeconds')].get());ka=float(values[('SilenceTrim','KeepAfterSeconds')].get())
   if not (5<=sr<=120 and -60<=st<=-20 and .05<=ms<=2 and 0<=kb<=5 and 0<=ka<=5):raise ValueError
  except ValueError:messagebox.showerror(_('Settings'),_('Silence Trim values are outside the allowed range.'),parent=win);return
  if not _safe_relative_name(values[('DaVinciResolve','ResolveProjectFolder')].get()) or not _safe_relative_name(values[('Deliver','Folder')].get()):messagebox.showerror(_('Settings'),_('Project Library and DELIVERY must be valid relative names.'),parent=win);return
  if p.has_section('Paths'):p.remove_section('Paths')
  p.add_section('Paths')
  for key,raw in roots:p.set('Paths',key,raw)
  for (sec,key),v in values.items():
   if not p.has_section(sec):p.add_section(sec)
   val=v.get()
   if (sec,key)==('IntroDetection','SearchWindowSeconds'):val=str(int(val)*60)
   elif (sec,key) in (('IntroDetection','MinConfidence'),('TimelineAssets','TitleAutoMatchScore')):val=f'{int(val)/100:.2f}'
   elif isinstance(v,tk.BooleanVar):val='true' if bool(val) else 'false'
   p.set(sec,key,str(val))
  with CONFIG.open('w',encoding='utf-8') as f:p.write(f)
  old_resolved=i18n.resolve_language();new_resolved=i18n.set_language(chosen_lang)
  if on_saved:on_saved(old_resolved!=new_resolved)
  win.destroy()
 buttons=ttk.Frame(outer);buttons.grid(row=1,column=0,columnspan=2,pady=(4,0));ttk.Button(buttons,text='OK',width=14,command=save).pack(side='left',padx=6);ttk.Button(buttons,text=_('Cancel'),width=14,command=win.destroy).pack(side='left',padx=6)
 ui_windows.prepare_dialog(win,parent);ui_windows.center_and_place_above_resolve(win);win.grab_set()
def choose_project(candidates,query='',root_path=None):
 current_root=[root_path or project_root()];all_projects=[list(candidates) if candidates is not None else projects(current_root[0])];result=[None];exit_requested=[False];root=tk.Tk();root.title(_('Projects — DavinciResolveProjectManagement 1.26'));root.resizable(False,False);menu=tk.Menu(root);pm=tk.Menu(menu,tearoff=False);menu.add_cascade(label=_('Project'),menu=pm);root.config(menu=menu);outer=ttk.Frame(root,padding=(18,12,18,14));outer.pack();search_var=tk.StringVar(value=query or '');search=ttk.Entry(outer,textvariable=search_var,width=64);search.pack(fill='x',pady=(0,8));frame=ttk.Frame(outer);frame.pack();tree=ttk.Treeview(frame,columns=('name','created'),show='headings',height=12,selectmode='browse');dw=tkfont.nametofont('TkDefaultFont').measure('18.08.2026 23:59:59')+24;tree.column('name',width=410,anchor='w');tree.column('created',width=dw,anchor='e',stretch=False);tree.heading('name',text=_('Project'));tree.heading('created',text=_('Created'));scroll=ttk.Scrollbar(frame,orient='vertical',command=tree.yview);tree.configure(yscrollcommand=scroll.set);tree.pack(side='left');scroll.pack(side='right',fill='y');displayed=[];info=tk.StringVar();ttk.Label(outer,textvariable=info).pack(anchor='w',pady=(5,0))
 def rebuild(*_):
  q=search_var.get().strip().casefold();ordered=[p for p in all_projects[0] if not q or q in p.name.casefold()];ordered.sort(key=created,reverse=True);displayed[:]=ordered;tree.delete(*tree.get_children())
  for i,pth in enumerate(ordered):tree.insert('','end',iid=str(i),values=(pth.name,datetime.fromtimestamp(created(pth)).strftime('%d.%m.%Y %H:%M:%S')))
  if ordered:tree.selection_set('0');tree.focus('0');tree.see('0');info.set('')
  else:info.set(_('No project found.'))
 def reload_config(language_changed=False):
  current_root[0]=project_root();all_projects[0]=projects(current_root[0])
  if language_changed:
   root.title(_('Projects — DavinciResolveProjectManagement 1.26'));menu.entryconfigure(0,label=_('Project'))
   pm.entryconfigure(0,label=_('New...'));pm.entryconfigure(1,label=_('Open...'));pm.entryconfigure(2,label=_('Settings...'));pm.entryconfigure(4,label=_('Exit'))
   tree.heading('name',text=_('Project'));tree.heading('created',text=_('Created'))
   life.log('UI_LANGUAGE_APPLIED',language=i18n.resolve_language())
  rebuild()
 def ok(*_):
  sel=tree.selection()
  if sel:result[0]=displayed[int(sel[0])];root.destroy()
 def new():
  x=ask_new_project(root,current_root[0])
  if x:result[0]=x;root.destroy()
 def open_any():
  x=import_external(root,current_root[0])
  if x and x.get('project'):result[0]=x['project'];root.destroy()
 def open_settings():
  try:
   life.log('SETTINGS_OPEN_CALL');settings(root,reload_config);life.log('SETTINGS_OPEN_RETURN')
  except Exception as e:
   life.log('SETTINGS_OPEN_ERROR',error=repr(e),traceback=traceback.format_exc())
   messagebox.showerror(_('Settings'),_('Settings cannot be opened.\n\n{error}').format(error=e),parent=root)
 def exit_app(*_):
  exit_requested[0]=True
  life.log('APPLICATION_EXIT_REQUESTED')
  try:
   state=life.state()
   if state.get('owned') and life.pid_running(state.get('pid')):life.force_stop_owned()
  except Exception as e:life.log('APPLICATION_EXIT_CLEANUP_ERROR',error=repr(e))
  root.destroy()
 pm.add_command(label=_('New...'),command=new);pm.add_command(label=_('Open...'),command=open_any);pm.add_command(label=_('Settings...'),command=open_settings);pm.add_separator();pm.add_command(label=_('Exit'),command=exit_app);search_var.trace_add('write',rebuild);tree.bind('<Double-1>',ok);root.bind('<Return>',ok);root.bind('<Escape>',exit_app);root.protocol('WM_DELETE_WINDOW',exit_app);rebuild();ui_windows.center_and_place_above_resolve(root);search.focus_set();root.mainloop();return result[0]
