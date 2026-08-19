#!/usr/bin/env python3
from __future__ import annotations
import configparser, os, re, shutil, tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont
import ui_windows

APP=Path(__file__).resolve().parent
CONFIG=APP/'config.ini'
DATE_RE=re.compile(r'^(\d{8})\s+(.+?)(?:\s+(\d+))?$')
MEDIA_EXT={'.mp4','.mov','.mxf','.avi','.mkv','.mts','.m2ts','.wav','.mp3','.aac','.flac','.jpg','.jpeg','.png','.tif','.tiff','.bmp','.webp'}


def _config():
 p=configparser.ConfigParser();p.read(CONFIG,encoding='utf-8');return p

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
 m=DATE_RE.match(name.strip())
 if not m:return None,name.strip(),None
 return m.group(1),m.group(2).strip(),int(m.group(3)) if m.group(3) else None

def propose_name(raw,root):
 raw=' '.join(raw.strip().split())
 if not raw:return ''
 date,base,num=_series_parts(raw)
 if date and not _valid_date(date):date=None;base=raw;num=None
 if not date:date=datetime.now().strftime('%Y%m%d');base=raw
 existing=projects(root);max_num=0
 for p in existing:
  _,b,n=_series_parts(p.name)
  if b.casefold()==base.casefold() and n is not None:max_num=max(max_num,n)
 if num is None and max_num:num=max_num+1
 return f'{date} {base}'+(f' {num}' if num is not None else '')

def unique_name(name,root):return not any(p.name.casefold()==name.casefold() for p in projects(root))

def ask_new_project(parent,root):
 win=tk.Toplevel(parent);win.title('Nový projekt');win.resizable(False,False);result=[None];confirmed=[False]
 box=ttk.Frame(win,padding=18);box.pack();ttk.Label(box,text='Název projektu:').pack(anchor='w');var=tk.StringVar();entry=tk.Entry(box,textvariable=var,width=54);entry.pack(fill='x',pady=(4,3));msg=tk.Label(box,text='',fg='#c00000');msg.pack(anchor='w')
 def submit(*_):
  value=var.get().strip()
  if not value:return
  proposed=propose_name(value,root)
  if not confirmed[0] or proposed!=value:
   var.set(proposed);confirmed[0]=True;entry.configure(highlightthickness=2,highlightbackground='#c00000',highlightcolor='#c00000');msg.configure(text='Souhlasí název projektu?');win.bell();entry.icursor('end');entry.focus_set();return
  date,_,_=_series_parts(value)
  if not date or not _valid_date(date):msg.configure(text='Název musí začínat validním datem RRRRMMDD.');win.bell();return
  if not unique_name(value,root):msg.configure(text='Název již existuje.');win.bell();return
  target=root/value
  try:(target/'SHOOTING').mkdir(parents=True,exist_ok=False)
  except Exception as e:msg.configure(text=f'Projekt nelze vytvořit: {e}');win.bell();return
  result[0]=target;win.destroy()
 def changed(*_):
  if confirmed[0]:confirmed[0]=False;entry.configure(highlightthickness=1,highlightbackground='SystemButtonFace');msg.configure(text='')
 var.trace_add('write',changed);buttons=ttk.Frame(box);buttons.pack(pady=(12,0));ttk.Button(buttons,text='OK',width=12,command=submit).pack(side='left',padx=5);ttk.Button(buttons,text='Cancel',width=12,command=win.destroy).pack(side='left',padx=5)
 win.bind('<Return>',submit);win.bind('<Escape>',lambda e:win.destroy());ui_windows.center_and_place_above_resolve(win);entry.focus_set();win.grab_set();parent.wait_window(win);return result[0]

def _media_files(folder):return [p for p in folder.rglob('*') if p.is_file() and p.suffix.casefold() in MEDIA_EXT]
def _same_volume(a,b):return os.path.splitdrive(str(a.resolve()))[0].casefold()==os.path.splitdrive(str(b.resolve()))[0].casefold()
def _writable_target(root):
 try:
  root.mkdir(parents=True,exist_ok=True);probe=root/'.drpm_write_test.tmp';probe.write_bytes(b'1');probe.unlink();return True
 except Exception:return False

def import_external(parent,root):
 src_text=filedialog.askdirectory(parent=parent,title='Otevřít adresář s médii');
 if not src_text:return None
 src=Path(src_text);files=_media_files(src)
 if not files:messagebox.showerror('Otevřít','Ve vybraném adresáři nebyly nalezeny podporované mediální soubory.',parent=parent);return None
 move=messagebox.askyesnocancel('Otevřít',f'Nalezeno {len(files)} mediálních souborů.\n\nPřesunout je do standardního projektového adresáře?',parent=parent)
 if move is None:return None
 if not move:
  name=ask_new_project(parent,root)
  if name:
   try:(name/'SHOOTING').rmdir();name.rmdir()
   except Exception:pass
   return {'external':src,'name':name.name if name else src.name}
  return None
 target=ask_new_project(parent,root)
 if not target:return None
 if not _writable_target(target):messagebox.showerror('Otevřít','Cílový adresář není dostupný pro zápis.',parent=parent);return None
 shoot=target/'SHOOTING';same=_same_volume(src,shoot);total=sum(p.stat().st_size for p in files)
 if not same:
  free=shutil.disk_usage(shoot).free;reserve=max(64*1024*1024,int(total*.02))
  if free<total+reserve:messagebox.showerror('Otevřít',f'Na cílovém disku není dostatek volného místa.\nPotřeba: {total+reserve:,} B\nVolno: {free:,} B',parent=parent);return None
 win=tk.Toplevel(parent);win.title('Přesun médií');win.resizable(False,False);frm=ttk.Frame(win,padding=18);frm.pack();label=ttk.Label(frm,text='Připravuji přesun…');label.pack(anchor='w');bar=ttk.Progressbar(frm,length=430,maximum=max(total,1));bar.pack(pady=(8,0));ui_windows.center_and_place_above_resolve(win);win.update();done=0
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
 except Exception as e:
  win.destroy();messagebox.showerror('Přesun médií',f'Přesun byl bezpečně zastaven.\n\n{e}',parent=parent);return None
 win.destroy();return {'project':target}

def settings(parent):
 p=_config();win=tk.Toplevel(parent);win.title('Nastavení');win.resizable(False,False);frm=ttk.Frame(win,padding=18);frm.pack();fields=[]
 visible=[('Paths','ProjectRoot','Projektový kořen'),('DaVinciResolve','ResolveProjectFolder','Resolve Project Library'),('DaVinciResolve','ResolveExe','Resolve EXE'),('DaVinciResolve','StartupTimeout','Startup timeout'),('DaVinciResolve','AliveTimeout','Alive timeout'),('Deliver','Preset','DELIVERY preset'),('Deliver','Folder','DELIVERY adresář'),('Timeline','VoiceIsolationAmount','Voice Isolation'),('Timeline','CreateCleanAudioTrack','Vytvořit čistou audio stopu'),('Timeline','CleanAudioTrackName','Název čisté audio stopy'),('IntroDetection','Folder','Adresář znělek'),('IntroDetection','SearchWindowSeconds','Okno hledání znělky'),('IntroDetection','MinConfidence','Min. confidence'),('Logging','Mode','Logging')]
 for r,(sec,key,label) in enumerate(visible):
  ttk.Label(frm,text=label+':').grid(row=r,column=0,sticky='w',padx=(0,10),pady=3);v=tk.StringVar(value=p.get(sec,key,fallback=''));ttk.Entry(frm,textvariable=v,width=48).grid(row=r,column=1,pady=3);fields.append((sec,key,v))
 def save():
  for sec,key,v in fields:
   if not p.has_section(sec):p.add_section(sec)
   p.set(sec,key,v.get())
  with CONFIG.open('w',encoding='utf-8') as f:p.write(f)
  win.destroy()
 b=ttk.Frame(frm);b.grid(row=len(visible),column=0,columnspan=2,pady=(12,0));ttk.Button(b,text='OK',width=12,command=save).pack(side='left',padx=5);ttk.Button(b,text='Cancel',width=12,command=win.destroy).pack(side='left',padx=5);ui_windows.center_and_place_above_resolve(win);win.grab_set()

def choose_project(candidates,query='',root_path=None):
 root_path=root_path or project_root();all_projects=list(candidates) if candidates is not None else projects(root_path);result=[None];root=tk.Tk();root.title('Projekty');root.resizable(False,False)
 menu=tk.Menu(root);pm=tk.Menu(menu,tearoff=False);menu.add_cascade(label='Projekt',menu=pm);root.config(menu=menu)
 outer=ttk.Frame(root,padding=(18,12,18,14));outer.pack();search_var=tk.StringVar(value=query or '');search=ttk.Entry(outer,textvariable=search_var,width=64);search.pack(fill='x',pady=(0,8));frame=ttk.Frame(outer);frame.pack();tree=ttk.Treeview(frame,columns=('name','created'),show='headings',height=12,selectmode='browse');font=tkfont.nametofont('TkDefaultFont');dw=font.measure('18.08.2026 23:59:59')+24;tree.column('name',width=410,anchor='w');tree.column('created',width=dw,anchor='e',stretch=False);tree.heading('name',text='Projekt');tree.heading('created',text='Vytvořeno');scroll=ttk.Scrollbar(frame,orient='vertical',command=tree.yview);tree.configure(yscrollcommand=scroll.set);tree.pack(side='left');scroll.pack(side='right',fill='y');displayed=[];info=tk.StringVar();ttk.Label(outer,textvariable=info).pack(anchor='w',pady=(5,0))
 def rebuild(*_):
  q=search_var.get().strip().casefold();ordered=[p for p in all_projects if not q or q in p.name.casefold()];ordered.sort(key=created,reverse=True);displayed[:]=ordered;tree.delete(*tree.get_children())
  for i,p in enumerate(ordered):tree.insert('','end',iid=str(i),values=(p.name,datetime.fromtimestamp(created(p)).strftime('%d.%m.%Y %H:%M:%S')))
  if ordered:tree.selection_set('0');tree.focus('0');tree.see('0');info.set('')
  else:info.set('Nenalezen žádný projekt.')
 def ok(*_):
  sel=tree.selection()
  if sel:result[0]=displayed[int(sel[0])];root.destroy()
 def new():
  p=ask_new_project(root,root_path)
  if p:result[0]=p;root.destroy()
 def open_any():
  r=import_external(root,root_path)
  if r and r.get('project'):result[0]=r['project'];root.destroy()
 pm.add_command(label='Nový...',command=new);pm.add_command(label='Otevřít...',command=open_any);pm.add_command(label='Nastavení...',command=lambda:settings(root));pm.add_separator();pm.add_command(label='Konec',command=root.destroy)
 search_var.trace_add('write',rebuild);search.bind('<Down>',lambda e:(tree.focus_set(),tree.selection_set(tree.get_children()[0]) if tree.get_children() else None));tree.bind('<Double-1>',ok);root.bind('<Return>',ok);root.bind('<Escape>',lambda e:root.destroy());rebuild();ui_windows.center_and_place_above_resolve(root);search.focus_set();root.mainloop();return result[0]
