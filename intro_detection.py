#!/usr/bin/env python3
from __future__ import annotations
import configparser,re,time
from pathlib import Path
import resolve_lifecycle as life
import timeline_audio

APP=Path(__file__).resolve().parent
CONFIG=APP/'config.ini'
SET_RE=re.compile(r'^set[\s_-]*\d{1,2}$',re.I)


def _settings():
 p=configparser.ConfigParser();p.read(CONFIG,encoding='utf-8')
 return (p.getboolean('Timeline','AutoDetectIntro',fallback=True),max(1,p.getint('Timeline','IntroMaxEndSeconds',fallback=60)))

def has_set_folders(shoot):return any(x.is_dir() and SET_RE.match(x.name.strip()) for x in shoot.iterdir())
def _fps(timeline):
 try:
  value=timeline.GetSetting('timelineFrameRate')
  if value:return float(str(value).replace(',','.'))
 except Exception:pass
 life.log('INTRO_FPS_FALLBACK',fps=25);return 25.0

def _items(timeline,track_type,index):
 try:return sorted(timeline.GetItemListInTrack(track_type,index) or [],key=lambda x:float(x.GetStart(False)))
 except Exception:return []

def is_prepared(timeline):
 clean=timeline_audio.find_clean_track(timeline)
 return bool(clean and _items(timeline,'audio',clean))

def _detect_bounds(mp,timeline,max_seconds):
 if not hasattr(timeline,'DetectSceneCuts') or not hasattr(timeline,'DuplicateTimeline'):
  life.log('INTRO_NOT_DETECTED',reason='scene_cut_api_unavailable');return None
 temp_name=f'__DRPM_SCENE_{int(time.time()*1000)}';temp=timeline.DuplicateTimeline(temp_name)
 if temp is None:
  life.log('INTRO_NOT_DETECTED',reason='duplicate_failed');return None
 try:
  if not temp.DetectSceneCuts():life.log('INTRO_NOT_DETECTED',reason='detect_scene_cuts_failed');return None
  video=_items(temp,'video',1)
  if len(video)<3:life.log('INTRO_NOT_DETECTED',reason='fewer_than_two_cuts',segments=len(video));return None
  first_cut=int(round(float(video[1].GetStart(False))));second_cut=int(round(float(video[2].GetStart(False))))
  start=int(timeline.GetStartFrame() or 0);limit=start+int(round(_fps(timeline)*max_seconds))
  if second_cut>limit:life.log('INTRO_REJECTED',reason='second_cut_after_limit',first_cut=first_cut,second_cut=second_cut,limit=limit);return None
  if second_cut<=first_cut:life.log('INTRO_REJECTED',reason='invalid_cut_order',first_cut=first_cut,second_cut=second_cut);return None
  life.log('INTRO_DETECTED',first_cut=first_cut,second_cut=second_cut,max_seconds=max_seconds);return first_cut,second_cut
 finally:
  try:mp.DeleteTimelines([temp])
  except Exception:life.log('INTRO_TEMP_DELETE_FAILED',timeline=temp_name)

def _clip_info(item,record_start,record_end,track_index,media_type):
 item_start=int(round(float(item.GetStart(False))));source_start=int(item.GetSourceStartFrame());offset=record_start-item_start
 return {'mediaPoolItem':item.GetMediaPoolItem(),'startFrame':source_start+offset,'endFrame':source_start+offset+(record_end-record_start)-1,'mediaType':media_type,'trackIndex':track_index,'recordFrame':record_start}
def _append(mp,info):
 if info['endFrame']<info['startFrame']:return True
 return bool(mp.AppendToTimeline([info]))

def _rebuild(mp,timeline,bounds):
 intro_start,intro_end=bounds;original_name=timeline.GetName();tmp_name=f'__DRPM_REBUILD_{int(time.time()*1000)}';rebuilt=mp.CreateEmptyTimeline(tmp_name)
 if rebuilt is None:raise RuntimeError('Nelze vytvořit dočasnou timeline pro audio routing znělky.')
 try:
  video_tracks=int(timeline.GetTrackCount('video') or 0);audio_tracks=int(timeline.GetTrackCount('audio') or 0);existing_clean=timeline_audio.find_clean_track(timeline)
  while int(rebuilt.GetTrackCount('video') or 0)<video_tracks:
   if not rebuilt.AddTrack('video'):raise RuntimeError('Nelze vytvořit video stopu při rekonstrukci timeline.')
  target_audio_count=audio_tracks if existing_clean else audio_tracks+1
  while int(rebuilt.GetTrackCount('audio') or 0)<target_audio_count:
   subtype='stereo'
   try:
    idx=min(max(1,int(rebuilt.GetTrackCount('audio') or 1)),max(1,audio_tracks));subtype=timeline.GetTrackSubType('audio',idx) or 'stereo'
   except Exception:pass
   if not rebuilt.AddTrack('audio',subtype):raise RuntimeError('Nelze vytvořit audio stopu při rekonstrukci timeline.')
  clean_track=existing_clean or target_audio_count
  try:
   _,_,clean_name=timeline_audio._settings()
   if clean_name:rebuilt.SetTrackName('audio',clean_track,clean_name)
  except Exception:pass
  for track in range(1,video_tracks+1):
   for item in _items(timeline,'video',track):
    start=int(round(float(item.GetStart(False))));end=int(round(float(item.GetEnd(False))))
    if not _append(mp,_clip_info(item,start,end,track,1)):raise RuntimeError('Nelze obnovit video při rekonstrukci timeline.')
  for track in range(1,audio_tracks+1):
   if track==existing_clean:continue
   for item in _items(timeline,'audio',track):
    start=int(round(float(item.GetStart(False))));end=int(round(float(item.GetEnd(False))));pieces=[]
    if start<intro_start:pieces.append((start,min(end,intro_start),track))
    a=max(start,intro_start);b=min(end,intro_end)
    if a<b:pieces.append((a,b,clean_track))
    if end>intro_end:pieces.append((max(start,intro_end),end,track))
    if not pieces:pieces=[(start,end,track)]
    for a,b,target in pieces:
     if a<b and not _append(mp,_clip_info(item,a,b,target,2)):raise RuntimeError('Nelze obnovit audio při rekonstrukci timeline.')
  backup_name=f'{original_name}__DRPM_BACKUP'
  if not timeline.SetName(backup_name):raise RuntimeError('Nelze dočasně přejmenovat původní timeline.')
  if not rebuilt.SetName(original_name):timeline.SetName(original_name);raise RuntimeError('Nelze pojmenovat rekonstruovanou timeline.')
  if not mp.DeleteTimelines([timeline]):life.log('INTRO_BACKUP_TIMELINE_RETAINED',timeline=backup_name)
  life.log('INTRO_AUDIO_ROUTED',start_frame=intro_start,end_frame=intro_end,clean_track=clean_track);print(f'[OK] Znělka detekována mezi 1. a 2. střihem; audio -> A{clean_track} bez Voice Isolation')
  return rebuilt
 except Exception:
  try:mp.DeleteTimelines([rebuilt])
  except Exception:pass
  raise

def configure(mp,timeline,shoot):
 enabled,max_seconds=_settings()
 if not enabled:return timeline
 if has_set_folders(shoot):life.log('INTRO_SKIP',reason='set_folders_present');print('[OK] Detekce znělky přeskočena: SHOOTING obsahuje SET');return timeline
 bounds=_detect_bounds(mp,timeline,max_seconds)
 if not bounds:print('[OK] Použitelná znělka do první minuty nebyla detekována.');return timeline
 try:return _rebuild(mp,timeline,bounds)
 except Exception as e:life.log('INTRO_ROUTING_FAILED',error=str(e));print(f'[WARN] Znělka byla nalezena, ale bezpečné audio routování selhalo: {e}');return timeline
