#!/usr/bin/env python3
from __future__ import annotations
import configparser
from pathlib import Path
import resolve_lifecycle as life

APP=Path(__file__).resolve().parent
CONFIG=APP/'config.ini'


def _settings():
 p=configparser.ConfigParser();p.read(CONFIG,encoding='utf-8')
 amount=max(0,min(100,p.getint('Timeline','VoiceIsolationAmount',fallback=100)))
 create_clean=p.getboolean('Timeline','CreateCleanAudioTrack',fallback=True)
 clean_name=p.get('Timeline','CleanAudioTrackName',fallback='AUDIO').strip()
 return amount,create_clean,clean_name


def find_clean_track(timeline):
 _,_,clean_name=_settings();count=int(timeline.GetTrackCount('audio') or 0)
 for i in range(1,count+1):
  try:name=(timeline.GetTrackName('audio',i) or '').strip()
  except Exception:name=''
  if clean_name and name.casefold()==clean_name.casefold():return i
 return None


def is_prepared(timeline):
 if timeline is None or not hasattr(timeline,'GetVoiceIsolationState'):return False
 clean=find_clean_track(timeline)
 if clean is None:return False
 count=int(timeline.GetTrackCount('audio') or 0)
 try:
  clean_state=timeline.GetVoiceIsolationState(clean) or {}
  if bool(clean_state.get('isEnabled')):return False
  source=[i for i in range(1,count+1) if i!=clean]
  return bool(source) and all(bool((timeline.GetVoiceIsolationState(i) or {}).get('isEnabled')) for i in source)
 except Exception:return False


def configure(timeline,create_clean_override=None):
 if timeline is None:raise RuntimeError('Timeline pro audio konfiguraci neexistuje.')
 if not hasattr(timeline,'SetVoiceIsolationState'):raise RuntimeError('Tato verze DaVinci Resolve nepodporuje scripting API pro Voice Isolation.')
 amount,create_clean,clean_name=_settings()
 if create_clean_override is not None:create_clean=bool(create_clean_override)
 clean=find_clean_track(timeline);count=int(timeline.GetTrackCount('audio') or 0)
 source=[i for i in range(1,count+1) if i!=clean]
 for i in source:
  if not timeline.SetVoiceIsolationState(i,{'isEnabled':True,'amount':amount}):raise RuntimeError(f'Nelze zapnout Voice Isolation na audio stopě A{i}.')
 if create_clean and clean is None:
  subtype='stereo'
  if count>0:
   try:subtype=timeline.GetTrackSubType('audio',1) or 'stereo'
   except Exception:pass
  if not timeline.AddTrack('audio',subtype):raise RuntimeError('Nelze vytvořit prázdnou audio stopu bez Voice Isolation.')
  clean=int(timeline.GetTrackCount('audio') or 0)
  if clean<1:raise RuntimeError('Nová audio stopa nebyla po vytvoření nalezena.')
  if clean_name:
   try:timeline.SetTrackName('audio',clean,clean_name)
   except Exception:pass
 if clean is not None:
  if not timeline.SetVoiceIsolationState(clean,{'isEnabled':False,'amount':0}):raise RuntimeError(f'Nelze vypnout Voice Isolation na audio stopě A{clean}.')
 life.log('TIMELINE_AUDIO_CONFIGURED',source_tracks=source,voice_isolation_amount=amount,clean_track=clean)
 if source:print(f'[OK] Voice Isolation: {len(source)} zdrojových audio stop = ON ({amount} %)')
 else:print('[OK] Voice Isolation: žádná zdrojová audio stopa')
 if clean:print(f'[OK] Čistá audio stopa A{clean}: Voice Isolation = OFF')
 return timeline
