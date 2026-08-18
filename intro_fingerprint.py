#!/usr/bin/env python3
from __future__ import annotations
import configparser,hashlib,json,os,shutil,subprocess,tempfile
from pathlib import Path
import numpy as np
import resolve_lifecycle as life

APP=Path(__file__).resolve().parent
CONFIG=APP/'config.ini'
CACHE=APP/'runtime'/'intro_fingerprints'
SUPPORTED={'.mp4','.mov','.mkv','.avi','.m4v','.wav','.mp3','.m4a','.aac','.flac'}


def settings():
 p=configparser.ConfigParser();p.read(CONFIG,encoding='utf-8')
 folder=Path(p.get('IntroDetection','Folder',fallback=r'D:\WORK\INTRO')).expanduser()
 search=max(10,p.getint('IntroDetection','SearchWindowSeconds',fallback=120))
 confidence=max(0.0,min(1.0,p.getfloat('IntroDetection','MinConfidence',fallback=0.78)))
 sample_rate=max(2000,p.getint('IntroDetection','SampleRate',fallback=8000))
 hop_ms=max(10,p.getint('IntroDetection','EnvelopeHopMs',fallback=20))
 return folder,search,confidence,sample_rate,hop_ms


def list_intros():
 folder,*_=settings()
 if not folder.is_dir():return []
 return sorted([p for p in folder.iterdir() if p.is_file() and p.suffix.casefold() in SUPPORTED],key=lambda p:p.name.casefold())


def _ffmpeg():
 for name in ('ffmpeg.exe','ffmpeg'):
  p=shutil.which(name)
  if p:return p
 candidates=[
  Path(os.environ.get('LOCALAPPDATA',''))/'Microsoft'/'WinGet'/'Links'/'ffmpeg.exe',
  Path(os.environ.get('ProgramFiles',''))/'ffmpeg'/'bin'/'ffmpeg.exe'
 ]
 for p in candidates:
  if p.is_file():return str(p)
 raise RuntimeError('FFmpeg nebyl nalezen. Spusť upgrade.cmd.')


def _pcm(path,max_seconds=None,sample_rate=8000):
 cmd=[_ffmpeg(),'-hide_banner','-loglevel','error','-i',str(path),'-vn','-ac','1','-ar',str(sample_rate)]
 if max_seconds is not None:cmd+=['-t',str(max_seconds)]
 cmd+=['-f','s16le','pipe:1']
 r=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
 if r.returncode!=0:raise RuntimeError(f'FFmpeg audio decode selhal pro {path.name}: {r.stderr.decode("utf-8","replace").strip()}')
 if not r.stdout:raise RuntimeError(f'Soubor neobsahuje použitelné audio: {path.name}')
 return np.frombuffer(r.stdout,dtype='<i2').astype(np.float32)/32768.0


def _envelope(samples,sample_rate,hop_ms):
 hop=max(1,int(round(sample_rate*hop_ms/1000.0)))
 n=(len(samples)//hop)*hop
 if n<hop*4:raise RuntimeError('Audio je příliš krátké pro fingerprint.')
 x=samples[:n].reshape(-1,hop)
 rms=np.sqrt(np.mean(x*x,axis=1)+1e-12)
 env=np.log1p(rms*1000.0).astype(np.float32)
 env-=float(np.mean(env));std=float(np.std(env))
 if std<1e-6:raise RuntimeError('Audio nemá dostatečnou dynamiku pro fingerprint.')
 env/=std
 return env


def _cache_key(path,sample_rate,hop_ms):
 st=path.stat();raw=f'{path.resolve()}|{st.st_size}|{st.st_mtime_ns}|{sample_rate}|{hop_ms}'.encode('utf-8','surrogatepass')
 return hashlib.sha256(raw).hexdigest()


def reference_fingerprint(path):
 _,_,_,sr,hop=settings();path=Path(path);CACHE.mkdir(parents=True,exist_ok=True);key=_cache_key(path,sr,hop);npz=CACHE/f'{key}.npz'
 if npz.is_file():
  d=np.load(npz);return d['env'].astype(np.float32),float(d['duration'])
 samples=_pcm(path,None,sr);duration=len(samples)/float(sr);env=_envelope(samples,sr,hop)
 np.savez_compressed(npz,env=env,duration=np.array(duration,dtype=np.float64))
 life.log('INTRO_FINGERPRINT_CACHED',file=str(path),duration=duration,points=len(env))
 return env,duration


def _normalized_correlation(target,ref):
 n=len(ref)
 if len(target)<n:return None,None
 raw=np.correlate(target,ref,mode='valid').astype(np.float64)
 c=np.concatenate(([0.0],np.cumsum(target,dtype=np.float64)))
 c2=np.concatenate(([0.0],np.cumsum(target*target,dtype=np.float64)))
 sums=c[n:]-c[:-n];sums2=c2[n:]-c2[:-n]
 var=np.maximum(sums2-(sums*sums)/n,1e-12)
 ref0=ref.astype(np.float64)-float(np.mean(ref));refnorm=float(np.sqrt(np.sum(ref0*ref0)))
 # ref is already nearly zero mean, correct raw for any residual target/ref means.
 raw_centered=raw-(sums*float(np.sum(ref))/n)
 score=raw_centered/(np.sqrt(var)*max(refnorm,1e-12))
 idx=int(np.argmax(score));return idx,float(score[idx])


def match(reference,target_media):
 folder,search,min_conf,sr,hop=settings();reference=Path(reference);target_media=Path(target_media)
 ref,duration=reference_fingerprint(reference)
 target_samples=_pcm(target_media,search,sr);target=_envelope(target_samples,sr,hop)
 idx,score=_normalized_correlation(target,ref)
 if idx is None:
  life.log('INTRO_MATCH_REJECTED',reason='target_shorter_than_reference',reference=str(reference),target=str(target_media));return None
 start=idx*hop/1000.0;end=start+duration
 life.log('INTRO_MATCH',reference=str(reference),target=str(target_media),start_seconds=start,end_seconds=end,confidence=score,min_confidence=min_conf)
 if score<min_conf:return None
 return {'start_seconds':start,'end_seconds':end,'confidence':score,'reference':reference,'target':target_media}
