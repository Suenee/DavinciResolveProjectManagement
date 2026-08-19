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
 out=[]
 for p in projects(root):
  _,b,_=_series_parts(p.name)
  if b and b.casefold() not in {x.casefold() for x in out}:out.append(b)
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
 win=tk.Toplevel(parent);win.title('Nový projekt');win.resizable(False,False);result=[None];confirmed=[False];box=ttk.Frame(win,padding=18);box.grid();ttk.Label(box,text='Název projektu:').grid(row=0,column=0,sticky='w');var=tk.StringVar();entry=ttk.Entry(box,textvariable=var,width=54);entry.grid(row=1,column=0,columnspan=2,sticky='ew',pady=(4,2));suggest=tk.Listbox(box,height=4,width=54,exportselection=False);suggest.grid(row=2,column=0,columnspan=2,sticky='ew');msg=tk.Label(box,text='',fg='#c00000',anchor='w');msg.grid(row=3,column=0,columnspan=2,sticky='w',pady=(3,0));buttons=ttk.Frame(box);buttons.grid(row=4,column=0,columnspan=2,pady=(12,0));okb=ttk.Button(buttons,text='OK',width=14);okb.pack(side='left',padx=6);ttk.Button(buttons,text='Cancel',width=14,command=win.destroy).pack(side='left',padx=6)
 def refresh(*_):
  if confirmed[0]:confirmed[0]=False;msg.configure(text='')
  q=var.get().strip().casefold();suggest.delete(0,'end')
  if q:
   for b in [x for x in _bases(root) if q in x.casefold()][:8]:suggest.insert('end',b)
 def use_suggestion(*_):
  sel=suggest.curselection()
  if sel:var.set(suggest.get(sel[0]));entry.icursor('end');entry.focus_set()
 def submit(*_):
  value=var.get().strip()
  if not value:return
  if not confirmed[0]:
   proposed=propose_name(value,root);var.set(proposed);confirmed[0]=True;msg.configure(text='Souhlasí název projektu?');win.bell();entry.icursor('end');entry.focus_set();return
  date,_,_= _series_parts(value)
  if not date or not _valid_date(date):msg.configure(text='Název musí začínat validním datem RRRRMMDD.');win.bell();return
  if not unique_name(value,root):msg.configure(text='Název již existuje.');win.bell();return
  target=root/value
  try:(target/'SHOOTING').mkdir(parents=True,exist_ok=False)
  except Exception as e:msg.configure(text=f'Projekt nelze vytvořit: {e}');win.bell();return
  result[0]=target;win.destroy()
 var.trace_add('write',refresh);suggest.bind('<Double-1>',use_suggestion);okb.configure(command=submit);win.bind('<Return>',submit);win.bind('<Escape>',lambda e:win.destroy());ui_windows.center_and_place_above_resolve(win);entry.focus_set();win.grab_set();parent.wait_window(win);return result[0]
def _media_files(folder):return [p for p in folder.rglob('*') if p.is_file() and p.suffix.casefold() in MEDIA_EXT]
def _same_volume(a,b):return os.path.splitdrive(str(a.resolve()))[0].casefold()==os.path.splitdrive(str(b.resolve()))[0].casefold()
def _writable_target(root):
 try:root.mkdir(parents=True,exist_ok=True);probe=root/'.drpm_write_test.tmp';probe.write_bytes(b'1');probe.unlink();return True
 except Exception:return False
def import_external(parent,root):
 src_text=filedialog.askdirectory(parent=parent,title='Otevřít adresář s médii');
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
   if same:os.replace(source,dest)
   else:
    tmp=dest.with_name(dest.name+'.drpm-partial');shutil.copy2(source,tmp)
    if tmp.stat().st_size!=size:raise RuntimeError(f'Ověření velikosti selhalo: {source}')
    os.replace(tmp,dest)
    if dest.stat().st_size!=size:raise RuntimeError(f'Ověření cíle selhalo: {dest}')
    source.unlink()
   done+=size;bar['value']=done;win.update()
 except Exception as e:win.destroy();messagebox.showerror('Přesun médií',f'Přesun byl bezpečně zastaven.\n\n{e}',parent=parent);return None
 win.destroy();return {'project':target}
def settings(parent):
 p=_config();win=tk.Toplevel(parent);win.title('Nastavení');win.resizable(False,False);frm=ttk.Frame(win,padding=18);frm.grid();row=[0];values={}
 def label(text,tip=None):ttk.Label(frm,text=text+':').grid(row=row[0],column=0,sticky='w',padx=(0,10),pady=3)
 def text(sec,key,title,width=43):
  label(title);v=tk.StringVar(value=p.get(sec,key,fallback=''));ttk.Entry(frm,textvariable=v,width=width).grid(row=row[0],column=1,columnspan=2,sticky='ew',pady=3);values[(sec,key)]=v;row[0]+=1
 def folder(sec,key,title):
  label(title);v=tk.StringVar(value=p.get(sec,key,fallback=''));e=ttk.Entry(frm,textvariable=v,width=38,state='readonly');e.grid(row=row[0],column=1,sticky='ew',pady=3);ttk.Button(frm,text='…',width=3,command=lambda:pick_folder(v)).grid(row=row[0],column=2,padx=(4,0));values[(sec,key)]=v;row[0]+=1
 def number(sec,key,title,lo,hi):
  label(title);v=tk.StringVar(value=p.get(sec,key,fallback=str(lo)));sp=ttk.Spinbox(frm,from_=lo,to=hi,textvariable=v,width=40,validate='key',validatecommand=(win.register(lambda x:x=='' or (x.isdigit() and int(x)<=hi)),'%P'));sp.grid(row=row[0],column=1,columnspan=2,sticky='ew',pady=3);values[(sec,key)]=v;row[0]+=1
 def pick_folder(v):
  x=filedialog.askdirectory(parent=win,initialdir=v.get() if Path(v.get()).is_dir() else None)
  if x:v.set(x)
 folder('Paths','ProjectRoot','Projektový kořen');text('DaVinciResolve','ResolveProjectFolder','Resolve Project Library')
 label('Resolve EXE');rv=tk.StringVar(value=p.get('DaVinciResolve','ResolveExe',fallback=''));ttk.Entry(frm,textvariable=rv,state='readonly',width=38).grid(row=row[0],column=1,sticky='ew');values[('DaVinciResolve','ResolveExe')]=rv
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
 label('Vytvořit čistou audio stopu');bv=tk.BooleanVar(value=p.getboolean('Timeline','CreateCleanAudioTrack',fallback=True));ttk.Checkbutton(frm,variable=bv).grid(row=row[0],column=1,sticky='w');values[('Timeline','CreateCleanAudioTrack')]=bv;row[0]+=1;text('Timeline','CleanAudioTrackName','Název čisté audio stopy');folder('IntroDetection','Folder','Adresář znělek');number('IntroDetection','SearchWindowSeconds','Okno hledání znělky (min)',1,5);number('IntroDetection','MinConfidence','Min. confidence (%)',0,100)
 label('Logging');lv=tk.StringVar(value=p.get('Logging','Mode',fallback='single'));ttk.Combobox(frm,textvariable=lv,values=('off','single','all'),state='readonly',width=40).grid(row=row[0],column=1,columnspan=2,sticky='ew');values[('Logging','Mode')]=lv;row[0]+=1
 def save():
  root=Path(values[('Paths','ProjectRoot')].get())
  intro=Path(values[('IntroDetection','Folder')].get())
  if not root.is_dir():messagebox.showerror('Nastavení','Projektový kořen musí být existující adresář.',parent=win);return
  if not intro.is_dir():messagebox.showerror('Nastavení','Adresář znělek musí existovat.',parent=win);return
  for (sec,key),v in values.items():
   if not p.has_section(sec):p.add_section(sec)
   val=v.get()
   if (sec,key)==('IntroDetection','SearchWindowSeconds'):val=str(int(val)*60)
   if (sec,key)==('IntroDetection','MinConfidence'):val=str(int(val)/100)
   p.set(sec,key,str(val).lower() if isinstance(val,bool) else str(val))
  with CONFIG.open('w',encoding='utf-8') as f:p.write(f)
  win.destroy()
 b=ttk.Frame(frm);b.grid(row=row[0],column=0,columnspan=3,pady=(12,0));ttk.Button(b,text='OK',width=14,command=save).pack(side='left',padx=6);ttk.Button(b,text='Cancel',width=14,command=win.destroy).pack(side='left',padx=6);ui_windows.center_and_place_above_resolve(win);win.grab_set()
def choose_project(candidates,query='',root_path=None):
 root_path=root_path or project_root();all_projects=list(candidates) if candidates is not None else projects(root_path);result=[None];root=tk.Tk();root.title('Projekty');root.resizable(False,False);menu=tk.Menu(root);pm=tk.Menu(menu,tearoff=False);menu.add_cascade(label='Projekt',menu=pm);root.config(menu=menu);outer=ttk.Frame(root,padding=(18,12,18,14));outer.pack();search_var=tk.StringVar(value=query or '');search=ttk.Entry(outer,textvariable=search_var,width=64);search.pack(fill='x',pady=(0,8));frame=ttk.Frame(outer);frame.pack();tree=ttk.Treeview(frame,columns=('name','created'),show='headings',height=12,selectmode='browse');dw=tkfont.nametofont('TkDefaultFont').measure('18.08.2026 23:59:59')+24;tree.column('name',width=410,anchor='w');tree.column('created',width=dw,anchor='e',stretch=False);tree.heading('name',text='Projekt');tree.heading('created',text='Vytvořeno');scroll=ttk.Scrollbar(frame,orient='vertical',command=tree.yview);tree.configure(yscrollcommand=scroll.set);tree.pack(side='left');scroll.pack(side='right',fill='y');displayed=[];info=tk.StringVar();ttk.Label(outer,textvariable=info).pack(anchor='w',pady=(5,0))
 def rebuild(*_):
  q=search_var.get().strip().casefold();ordered=[p for p in all_projects if not q or q in p.name.casefold()];ordered.sort(key=created,reverse=True);displayed[:]=ordered;tree.delete(*tree.get_children())
  for i,p in enumerate(ordered):tree.insert('','end',iid=str(i),values=(p.name,datetime.fromtimestamp(created(p)).strftime('%d.%m.%Y %H:%M:%S')))
  if ordered:tree.selection_set('0');tree.focus('0');tree.see('0');info.set('')
  else:info.set('Nenalezen žádný projekt.')
 def ok(*_):
  sel=tree.selection()
  if sel:result[0]=displayed[int(sel[0])];root.destroy()
 def new():
  x=ask_new_project(root,root_path)
  if x:result[0]=x;root.destroy()
 def open_any():
  x=import_external(root,root_path)
  if x and x.get('project'):result[0]=x['project'];root.destroy()
 pm.add_command(label='Nový...',command=new);pm.add_command(label='Otevřít...',command=open_any);pm.add_command(label='Nastavení...',command=lambda:settings(root));pm.add_separator();pm.add_command(label='Konec',command=root.destroy);search_var.trace_add('write',rebuild);tree.bind('<Double-1>',ok);root.bind('<Return>',ok);root.bind('<Escape>',lambda e:root.destroy());rebuild();ui_windows.center_and_place_above_resolve(root);search.focus_set();root.mainloop();return result[0]
