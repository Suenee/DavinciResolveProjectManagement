#!/usr/bin/env python3
from __future__ import annotations
import configparser, os, re, shutil, tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont
import ui_windows

APP=Path(__file__).resolve().parent; CONFIG=APP/'config.ini'
DATE_RE=re.compile(r'^(\d{8})\s+(.+?)(?:\s+(\d+))?$'); MEDIA_EXT={'.mp4','.mov','.mxf','.avi','.mkv','.mts','.m2ts','.wav','.mp3','.aac','.flac','.jpg','.jpeg','.png','.tif','.tiff','.bmp','.webp'}
INVALID_NAME=re.compile(r'[<>:"/\\|?*]')
def _config():p=configparser.ConfigParser();p.read(CONFIG,encoding='utf-8');return p
def project_root():return Path(_config().get('Paths','ProjectRoot'))
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
 win=tk.Toplevel(parent);win.title('Nový projekt');win.resizable(False,False);result=[None];confirmed=[False];popup=[None];box=ttk.Frame(win,padding=18);box.grid();ttk.Label(box,text='Název projektu:').grid(row=0,column=0,sticky='w');var=tk.StringVar();entry=ttk.Entry(box,textvariable=var,width=54);entry.grid(row=1,column=0,columnspan=2,sticky='ew',pady=(4,2));msg=tk.Label(box,text='',fg='#c00000',anchor='w',height=1);msg.grid(row=2,column=0,columnspan=2,sticky='w',pady=(3,0));buttons=ttk.Frame(box);buttons.grid(row=3,column=0,columnspan=2,pady=(12,0));okb=ttk.Button(buttons,text='OK',width=14);okb.pack(side='left',padx=6);ttk.Button(buttons,text='Cancel',width=14,command=win.destroy).pack(side='left',padx=6)
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
   var.set(propose_name(value,root));confirmed[0]=True;msg.configure(text='Souhlasí název projektu?');win.bell();entry.icursor('end');entry.focus_set();return
  date,_,_=_series_parts(value)
  if not date or not _valid_date(date):msg.configure(text='Název musí začínat validním datem RRRRMMDD.');win.bell();return
  if not unique_name(value,root):msg.configure(text='Název již existuje.');win.bell();return
  target=root/value
  try:(target/'SHOOTING').mkdir(parents=True,exist_ok=False)
  except Exception as e:msg.configure(text=f'Projekt nelze vytvořit: {e}');win.bell();return
  result[0]=target;win.destroy()
 var.trace_add('write',refresh);okb.configure(command=submit);win.bind('<Return>',submit);win.bind('<Escape>',lambda e:win.destroy());win.protocol('WM_DELETE_WINDOW',win.destroy);ui_windows.center_and_place_above_resolve(win);entry.focus_set();win.grab_set();parent.wait_window(win);return result[0]
def _media_files(folder):return [p for p in folder.rglob('*') if p.is_file() and p.suffix.casefold() in MEDIA_EXT]
def _same_volume(a,b):return os.path.splitdrive(str(a.resolve()))[0].casefold()==os.path.splitdrive(str(b.resolve()))[0].casefold()
def _writable_target(root):
 try:root.mkdir(parents=True,exist_ok=True);probe=root/'.drpm_write_test.tmp';probe.write_bytes(b'1');probe.unlink();return True
 except Exception:return False
def import_external(parent,root):
 src_text=filedialog.askdirectory(parent=parent,title='Otevřít adresář s médii')
 if not src_text:return None
 src=Path(src_text);files=_media_files(src)
 if not files:messagebox.showerror('Otevřít','Ve vybraném adresáři nebyly nalezeny podporované mediální soubory.',parent=parent);return None
 move=messagebox.askyesnocancel('Otevřít',f'Nalezeno {len(files)} mediálních souborů.\n\nPřesunout je do standardního projektového adresáře?',parent=parent)
 if move is None:return None
 if not move:return {'external':src,'name':src.name}
 target=ask_new_project(parent,root)
 if not target:return None
 if not _writable_target(target):messagebox.showerror('Otevřít','Cílový adresář není dostupný pro zápis.',parent=parent);return None
 shoot=target/'SHOOTING';same=_same_volume(src,shoot);total=sum(p.stat().st_size for p in files)
 if not same:
  free=shutil.disk_usage(shoot).free;reserve=max(64*1024*1024,int(total*.02))
  if free<total+reserve:messagebox.showerror('Otevřít','Na cílovém disku není dostatek volného místa.',parent=parent);return None
 win=tk.Toplevel(parent);win.title('Přesun médií');frm=ttk.Frame(win,padding=18);frm.pack();label=ttk.Label(frm,text='Připravuji přesun…');label.pack(anchor='w');bar=ttk.Progressbar(frm,length=430,maximum=max(total,1));bar.pack(pady=(8,0));ui_windows.center_and_place_above_resolve(win);win.update();done=0
 try:
  for source in files:
   rel=source.relative_to(src);dest=shoot/rel;dest.parent.mkdir(parents=True,exist_ok=True);size=source.stat().st_size;label.configure(text=str(rel));win.update()
   if same:
    if dest.exists():raise RuntimeError(f'Cílový soubor již existuje: {dest}')
    os.replace(source,dest)
   else:
    tmp=dest.with_name(dest.name+'.drpm-partial');shutil.copy2(source,tmp)
    if tmp.stat().st_size!=size:raise RuntimeError(f'Ověření velikosti selhalo: {source}')
    os.replace(tmp,dest)
    if dest.stat().st_size!=size:raise RuntimeError(f'Ověření cíle selhalo: {dest}')
    source.unlink()
   done+=size;bar['value']=done;win.update()
 except Exception as e:win.destroy();messagebox.showerror('Přesun médií',f'Přesun byl bezpečně zastaven.\n\n{e}',parent=parent);return None
 win.destroy();return {'project':target}
def _safe_relative_name(value):
 value=value.strip()
 return bool(value) and not Path(value).is_absolute() and '..' not in Path(value).parts and INVALID_NAME.search(value) is None
def settings(parent,on_saved=None):
 p=_config();win=tk.Toplevel(parent);win.title('Nastavení');win.resizable(False,False);frm=ttk.Frame(win,padding=18);frm.grid();row=[0];values={};widgets={}
 def label(text):ttk.Label(frm,text=text+':').grid(row=row[0],column=0,sticky='w',padx=(0,10),pady=3)
 def text(sec,key,title):
  label(title);v=tk.StringVar(value=p.get(sec,key,fallback=''));e=ttk.Entry(frm,textvariable=v,width=43);e.grid(row=row[0],column=1,columnspan=2,sticky='ew',pady=3);values[(sec,key)]=v;widgets[(sec,key)]=e;row[0]+=1
 def folder(sec,key,title):
  label(title);v=tk.StringVar(value=p.get(sec,key,fallback=''));e=ttk.Entry(frm,textvariable=v,width=38,state='readonly');e.grid(row=row[0],column=1,sticky='ew',pady=3);ttk.Button(frm,text='…',width=3,command=lambda:pick_folder(v)).grid(row=row[0],column=2,padx=(4,0));values[(sec,key)]=v;widgets[(sec,key)]=e;row[0]+=1
 def number(sec,key,title,lo,hi,display=None):
  label(title);raw=p.get(sec,key,fallback=str(lo));initial=str(display(raw) if display else raw);v=tk.StringVar(value=initial);vcmd=(win.register(lambda x:x=='' or (x.isdigit() and lo<=int(x)<=hi)),'%P');e=ttk.Spinbox(frm,from_=lo,to=hi,textvariable=v,width=40,validate='key',validatecommand=vcmd);e.grid(row=row[0],column=1,columnspan=2,sticky='ew',pady=3);values[(sec,key)]=v;widgets[(sec,key)]=e;row[0]+=1
 def pick_folder(v):
  x=filedialog.askdirectory(parent=win,initialdir=v.get() if Path(v.get()).is_dir() else None)
  if x:v.set(x)
 folder('Paths','ProjectRoot','Projektový kořen');text('DaVinciResolve','ResolveProjectFolder','Resolve Project Library')
 label('Resolve EXE');rv=tk.StringVar(value=p.get('DaVinciResolve','ResolveExe',fallback=''));rexe=ttk.Entry(frm,textvariable=rv,state='readonly',width=38);rexe.grid(row=row[0],column=1,sticky='ew');values[('DaVinciResolve','ResolveExe')]=rv;widgets[('DaVinciResolve','ResolveExe')]=rexe
 def resolve_pick():
  auto=messagebox.askyesno('DaVinci Resolve','Najít DaVinci Resolve automaticky?\n\nAno = AUTO\nNe = ruční výběr',parent=win);found=''
  if auto:
   candidates=[Path(os.environ.get('PROGRAMFILES',r'C:\Program Files'))/'Blackmagic Design'/'DaVinci Resolve'/'Resolve.exe',Path(os.environ.get('PROGRAMFILES(X86)',r'C:\Program Files (x86)'))/'Blackmagic Design'/'DaVinci Resolve'/'Resolve.exe'];found=next((str(x) for x in candidates if x.is_file()),'')
   if not found:messagebox.showwarning('DaVinci Resolve','Automatické hledání Resolve.exe selhalo. Vyberte soubor ručně.',parent=win)
  if not found:found=filedialog.askopenfilename(parent=win,title='Vyber Resolve.exe',filetypes=[('DaVinci Resolve','Resolve.exe'),('Executable','*.exe')])
  if found:
   if Path(found).name.casefold()!='resolve.exe':messagebox.showerror('DaVinci Resolve','Vybraný soubor musí být Resolve.exe.',parent=win);return
   rv.set(found)
 ttk.Button(frm,text='…',width=3,command=resolve_pick).grid(row=row[0],column=2,padx=(4,0));row[0]+=1
 number('DaVinciResolve','StartupTimeout','Startup timeout (s)',10,600);number('DaVinciResolve','AliveTimeout','Alive timeout (s)',0,86400);text('Deliver','Preset','DELIVERY preset');text('Deliver','Folder','DELIVERY adresář');number('Timeline','VoiceIsolationAmount','Voice Isolation (%)',0,100)
 label('Vytvořit čistou audio stopu');bv=tk.BooleanVar(value=p.getboolean('Timeline','CreateCleanAudioTrack',fallback=True));cb=ttk.Checkbutton(frm,variable=bv);cb.grid(row=row[0],column=1,sticky='w');values[('Timeline','CreateCleanAudioTrack')]=bv;row[0]+=1;text('Timeline','CleanAudioTrackName','Název čisté audio stopy');folder('IntroDetection','Folder','Adresář znělek');number('IntroDetection','SearchWindowSeconds','Okno hledání znělky (min)',1,5,lambda x:max(1,min(5,round(float(x)/60))));number('IntroDetection','MinConfidence','Min. confidence (%)',0,100,lambda x:round(float(x)*100) if float(x)<=1 else round(float(x)))
 label('Logging');lv=tk.StringVar(value=p.get('Logging','Mode',fallback='single'));log=ttk.Combobox(frm,textvariable=lv,values=('off','single','all'),state='readonly',width=40);log.grid(row=row[0],column=1,columnspan=2,sticky='ew');values[('Logging','Mode')]=lv;row[0]+=1
 def dependencies(*_):widgets[('Timeline','CleanAudioTrackName')].configure(state='normal' if bv.get() else 'disabled')
 bv.trace_add('write',dependencies);dependencies()
 def save():
  root=Path(values[('Paths','ProjectRoot')].get());intro=Path(values[('IntroDetection','Folder')].get());resolve_exe=values[('DaVinciResolve','ResolveExe')].get().strip()
  if not root.is_dir():messagebox.showerror('Nastavení','Projektový kořen musí být existující adresář.',parent=win);return
  if not intro.is_dir():messagebox.showerror('Nastavení','Adresář znělek musí být existující adresář.',parent=win);return
  if resolve_exe and (not Path(resolve_exe).is_file() or Path(resolve_exe).name.casefold()!='resolve.exe'):messagebox.showerror('Nastavení','Resolve EXE musí ukazovat na existující Resolve.exe.',parent=win);return
  if not _safe_relative_name(values[('DaVinciResolve','ResolveProjectFolder')].get()):messagebox.showerror('Nastavení','Resolve Project Library musí být platný název, ne cesta.',parent=win);return
  if not _safe_relative_name(values[('Deliver','Folder')].get()):messagebox.showerror('Nastavení','DELIVERY adresář musí být platný relativní název.',parent=win);return
  if bv.get() and not values[('Timeline','CleanAudioTrackName')].get().strip():messagebox.showerror('Nastavení','Při zapnuté čisté audio stopě musí být zadán její název.',parent=win);return
  for (sec,key),v in values.items():
   if not p.has_section(sec):p.add_section(sec)
   val=v.get()
   if (sec,key)==('IntroDetection','SearchWindowSeconds'):val=str(int(val)*60)
   elif (sec,key)==('IntroDetection','MinConfidence'):val=f'{int(val)/100:.2f}'
   elif isinstance(v,tk.BooleanVar):val='true' if bool(val) else 'false'
   p.set(sec,key,str(val))
  with CONFIG.open('w',encoding='utf-8') as f:p.write(f)
  if on_saved:on_saved()
  win.destroy()
 b=ttk.Frame(frm);b.grid(row=row[0],column=0,columnspan=3,pady=(12,0));ttk.Button(b,text='OK',width=14,command=save).pack(side='left',padx=6);ttk.Button(b,text='Cancel',width=14,command=win.destroy).pack(side='left',padx=6);ui_windows.center_and_place_above_resolve(win);win.grab_set()
def choose_project(candidates,query='',root_path=None):
 current_root=[root_path or project_root()];all_projects=[list(candidates) if candidates is not None else projects(current_root[0])];result=[None];root=tk.Tk();root.title('Projekty');root.resizable(False,False);menu=tk.Menu(root);pm=tk.Menu(menu,tearoff=False);menu.add_cascade(label='Projekt',menu=pm);root.config(menu=menu);outer=ttk.Frame(root,padding=(18,12,18,14));outer.pack();search_var=tk.StringVar(value=query or '');search=ttk.Entry(outer,textvariable=search_var,width=64);search.pack(fill='x',pady=(0,8));frame=ttk.Frame(outer);frame.pack();tree=ttk.Treeview(frame,columns=('name','created'),show='headings',height=12,selectmode='browse');dw=tkfont.nametofont('TkDefaultFont').measure('18.08.2026 23:59:59')+24;tree.column('name',width=410,anchor='w');tree.column('created',width=dw,anchor='e',stretch=False);tree.heading('name',text='Projekt');tree.heading('created',text='Vytvořeno');scroll=ttk.Scrollbar(frame,orient='vertical',command=tree.yview);tree.configure(yscrollcommand=scroll.set);tree.pack(side='left');scroll.pack(side='right',fill='y');displayed=[];info=tk.StringVar();ttk.Label(outer,textvariable=info).pack(anchor='w',pady=(5,0))
 def rebuild(*_):
  q=search_var.get().strip().casefold();ordered=[p for p in all_projects[0] if not q or q in p.name.casefold()];ordered.sort(key=created,reverse=True);displayed[:]=ordered;tree.delete(*tree.get_children())
  for i,pth in enumerate(ordered):tree.insert('','end',iid=str(i),values=(pth.name,datetime.fromtimestamp(created(pth)).strftime('%d.%m.%Y %H:%M:%S')))
  if ordered:tree.selection_set('0');tree.focus('0');tree.see('0');info.set('')
  else:info.set('Nenalezen žádný projekt.')
 def reload_config():current_root[0]=project_root();all_projects[0]=projects(current_root[0]);rebuild()
 def ok(*_):
  sel=tree.selection()
  if sel:result[0]=displayed[int(sel[0])];root.destroy()
 def new():
  x=ask_new_project(root,current_root[0])
  if x:result[0]=x;root.destroy()
 def open_any():
  x=import_external(root,current_root[0])
  if x and x.get('project'):result[0]=x['project'];root.destroy()
 pm.add_command(label='Nový...',command=new);pm.add_command(label='Otevřít...',command=open_any);pm.add_command(label='Nastavení...',command=lambda:settings(root,reload_config));pm.add_separator();pm.add_command(label='Konec',command=root.destroy);search_var.trace_add('write',rebuild);tree.bind('<Double-1>',ok);root.bind('<Return>',ok);root.bind('<Escape>',lambda e:root.destroy());rebuild();ui_windows.center_and_place_above_resolve(root);search.focus_set();root.mainloop();return result[0]
