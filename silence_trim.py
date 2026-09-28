#!/usr/bin/env python3
from __future__ import annotations
import array,configparser,math,shutil,subprocess
from pathlib import Path
import managed_builder as m
import resolve_lifecycle as life

def config():
 p=configparser.ConfigParser(interpolation=None);p.read(m.CONFIG,encoding='utf-8')
 return {'enabled':p.getboolean('SilenceTrim','Enabled',fallback=True),
         'search_seconds':p.getfloat('SilenceTrim','SearchSeconds',fallback=30.0),
         'threshold_db':p.getfloat('SilenceTrim','ThresholdDb',fallback=-40.0),
         'minimum_sound':p.getfloat('SilenceTrim','MinimumSoundSeconds',fallback=0.20),
         'keep_before':p.getfloat('SilenceTrim','KeepBeforeSeconds',fallback=0.75),
         'keep_after':p.getfloat('SilenceTrim','KeepAfterSeconds',fallback=1.00)}

def _tool(name):
 p=shutil.which(name)
 if p:return p
 ff=shutil.which('ffmpeg.exe') or shutil.which('ffmpeg')
 if ff:
  sibling=Path(ff).with_name(name+'.exe')
  if sibling.is_file():return str(sibling)
 return None

def _duration(path):
 probe=_tool('ffprobe')
 if not probe:return None
 cp=subprocess.run([probe,'-v','error','-show_entries','format=duration','-of','default=nk=1:nw=1',str(path)],capture_output=True,text=True,timeout=30,check=False)
 if cp.returncode:return None
 try:return float(cp.stdout.strip())
 except ValueError:return None

def _pcm(path,start,duration,rate=8000):
 ff=_tool('ffmpeg')
 if not ff:return []
 cmd=[ff,'-v','error']
 if start is not None:cmd += ['-ss',f'{max(0,start):.6f}']
 cmd += ['-i',str(path),'-t',f'{max(0,duration):.6f}','-vn','-ac','1','-ar',str(rate),'-f','s16le','pipe:1']
 cp=subprocess.run(cmd,capture_output=True,timeout=max(30,int(duration)+20),check=False)
 if cp.returncode or not cp.stdout:return []
 a=array.array('h');a.frombytes(cp.stdout)
 if __import__('sys').byteorder!='little':a.byteswap()
 return a

def _active_windows(samples,threshold_db,rate=8000,hop_ms=20):
 hop=max(1,int(rate*hop_ms/1000));limit=32768.0*(10.0**(threshold_db/20.0));out=[]
 for i in range(0,len(samples),hop):
  block=samples[i:i+hop]
  if not block:break
  rms=math.sqrt(sum(float(x)*float(x) for x in block)/len(block))
  out.append(rms>=limit)
 return out,hop/rate

def _first_stable(flags,needed):
 run=0
 for i,on in enumerate(flags):
  run=run+1 if on else 0
  if run>=needed:return i-run+1
 return None

def _last_stable(flags,needed):
 run=0
 for i in range(len(flags)-1,-1,-1):
  run=run+1 if flags[i] else 0
  if run>=needed:return i+run
 return None

def analyze(path,cfg=None):
 cfg=cfg or config();path=Path(path);duration=_duration(path)
 if not duration or duration<=0:return {'start':0.0,'end':0.0,'duration':duration,'reason':'duration_unavailable'}
 window=min(cfg['search_seconds'],duration);rate=8000
 lead=_pcm(path,0,window,rate);tail_start=max(0.0,duration-window);tail=_pcm(path,tail_start,window,rate)
 if not lead or not tail:return {'start':0.0,'end':0.0,'duration':duration,'reason':'audio_unavailable'}
 lf,step=_active_windows(lead,cfg['threshold_db'],rate);tf,_=_active_windows(tail,cfg['threshold_db'],rate)
 needed=max(1,int(math.ceil(cfg['minimum_sound']/step)))
 first=_first_stable(lf,needed);last=_last_stable(tf,needed)
 if first is None or last is None:return {'start':0.0,'end':0.0,'duration':duration,'reason':'stable_sound_not_found'}
 speech_start=first*step;speech_end=min(duration,tail_start+last*step)
 cut_start=max(0.0,speech_start-cfg['keep_before'])
 cut_end=max(0.0,duration-(speech_end+cfg['keep_after']))
 if cut_start+cut_end>=duration-0.1:return {'start':0.0,'end':0.0,'duration':duration,'reason':'unsafe_range'}
 return {'start':cut_start,'end':cut_end,'duration':duration,'speech_start':speech_start,'speech_end':speech_end,'reason':'ok'}

def analyze_files(paths,progress=None):
 cfg=config();result={};items=list(paths)
 for i,path in enumerate(items,1):
  if progress:progress(path,i,len(items))
  try:r=analyze(path,cfg)
  except Exception as e:r={'start':0.0,'end':0.0,'duration':None,'reason':'error','error':repr(e)}
  result[m.norm(path)]=r
  life.log('SILENCE_TRIM_ANALYSIS',file=str(path),threshold_db=cfg['threshold_db'],search_seconds=cfg['search_seconds'],minimum_sound=cfg['minimum_sound'],keep_before=cfg['keep_before'],keep_after=cfg['keep_after'],**r)
 return result
