#!/usr/bin/env python3
from __future__ import annotations
import time
from pathlib import Path
import intro_fingerprint
import resolve_lifecycle as life
import timeline_audio


def _items(timeline,track_type,index):
 try:return sorted(timeline.GetItemListInTrack(track_type,index) or [],key=lambda x:float(x.GetStart(False)))
 except Exception:return []


def _fps(timeline):
 for key in ('timelineFrameRate','timelinePlaybackFrameRate'):
  try:
   v=timeline.GetSetting(key)
   if v:return float(str(v).replace(',','.'))
  except Exception:pass
 life.log('INTRO_FPS_FALLBACK',fps=25);return 25.0


def _media_path(item):
 try:
  mp=item.GetMediaPoolItem()
  if mp is None:return None
  p=mp.GetClipProperty('File Path') or ''
  return Path(p) if p else None
 except Exception:return None


def _candidate_items(timeline,max_seconds):
 fps=_fps(timeline);start=float(timeline.GetStartFrame() or 0);limit=start+fps*max_seconds
 out=[]
 for item in _items(timeline,'video',1):
  try:
   if float(item.GetStart(False))>=limit:break
  except Exception:continue
  p=_media_path(item)
  if p and p.is_file():out.append((item,p))
 return out


def detect(timeline,reference):
 _,search,_,_,_=intro_fingerprint.settings();fps=_fps(timeline)
 for item,path in _candidate_items(timeline,search):
  try:match=intro_fingerprint.match(reference,path)
  except Exception as e:
   life.log('INTRO_CANDIDATE_SKIP',file=str(path),reason=str(e));continue
  if not match:continue
  try:source_start=float(item.GetSourceStartTime() or 0.0)
  except Exception:source_start=0.0
  item_start=float(item.GetStart(False))
  start_frame=int(round(item_start+(match['start_seconds']-source_start)*fps))
  end_frame=int(round(item_start+(match['end_seconds']-source_start)*fps))
  try:item_end=int(round(float(item.GetEnd(False))))
  except Exception:item_end=end_frame
  if end_frame<=start_frame or start_frame<item_start-1 or end_frame>item_end+1:
   life.log('INTRO_MATCH_REJECTED',reason='match_outside_timeline_item',file=str(path),start_frame=start_frame,end_frame=end_frame,item_start=item_start,item_end=item_end);continue
  match.update({'start_frame':start_frame,'end_frame':end_frame,'timeline_item':item})
  return match
 return None


def _clip_info(item,record_start,record_end,track_index,media_type):
 item_start=int(round(float(item.GetStart(False))));source_start=int(item.GetSourceStartFrame());offset=record_start-item_start
 return {'mediaPoolItem':item.GetMediaPoolItem(),'startFrame':source_start+offset,
         'endFrame':source_start+offset+(record_end-record_start)-1,
         'mediaType':media_type,'trackIndex':track_index,'recordFrame':record_start}


def _append(mp,info):
 if info['endFrame']<info['startFrame']:return True
 return bool(mp.AppendToTimeline([info]))


def _ensure_track_counts(rebuilt,timeline,video_tracks,audio_tracks):
 while int(rebuilt.GetTrackCount('video') or 0)<video_tracks:
  if not rebuilt.AddTrack('video'):raise RuntimeError('Nelze vytvořit video stopu při rekonstrukci timeline.')
 while int(rebuilt.GetTrackCount('audio') or 0)<audio_tracks:
  subtype='stereo'
  try:
   src=min(max(1,int(rebuilt.GetTrackCount('audio') or 1)),max(1,int(timeline.GetTrackCount('audio') or 1)))
   subtype=timeline.GetTrackSubType('audio',src) or 'stereo'
  except Exception:pass
  if not rebuilt.AddTrack('audio',subtype):raise RuntimeError('Nelze vytvořit audio stopu při rekonstrukci timeline.')


def _rebuild(mp,timeline,start_frame,end_frame):
 original_name=timeline.GetName();tmp_name=f'__DRPM_INTRO_{int(time.time()*1000)}';rebuilt=mp.CreateEmptyTimeline(tmp_name)
 if rebuilt is None:raise RuntimeError('Nelze vytvořit dočasnou timeline pro znělku.')
 try:
  video_tracks=int(timeline.GetTrackCount('video') or 0);audio_tracks=int(timeline.GetTrackCount('audio') or 0);clean=timeline_audio.find_clean_track(timeline)
  if clean is None:raise RuntimeError('Čistá AUDIO stopa nebyla nalezena.')
  _ensure_track_counts(rebuilt,timeline,video_tracks,audio_tracks)
  try:
   for i in range(1,audio_tracks+1):
    name=timeline.GetTrackName('audio',i) or ''
    if name:rebuilt.SetTrackName('audio',i,name)
  except Exception:pass

  # Video remains visually identical, but make an explicit edit at the end of the matched intro.
  for track in range(1,video_tracks+1):
   for item in _items(timeline,'video',track):
    a=int(round(float(item.GetStart(False))));b=int(round(float(item.GetEnd(False))))
    pieces=[(a,b)]
    if a<end_frame<b:pieces=[(a,end_frame),(end_frame,b)]
    for x,y in pieces:
     if x<y and not _append(mp,_clip_info(item,x,y,track,1)):raise RuntimeError('Nelze obnovit video při střihu znělky.')

  for track in range(1,audio_tracks+1):
   for item in _items(timeline,'audio',track):
    a=int(round(float(item.GetStart(False))));b=int(round(float(item.GetEnd(False))))
    if track==clean:
     pieces=[(a,b,clean)]
    else:
     pieces=[]
     if a<start_frame:pieces.append((a,min(b,start_frame),track))
     x=max(a,start_frame);y=min(b,end_frame)
     if x<y:pieces.append((x,y,clean))
     if b>end_frame:pieces.append((max(a,end_frame),b,track))
     if not pieces:pieces=[(a,b,track)]
    for x,y,target in pieces:
     if x<y and not _append(mp,_clip_info(item,x,y,target,2)):raise RuntimeError('Nelze obnovit audio při routování znělky.')

  backup=f'{original_name}__DRPM_BACKUP'
  if not timeline.SetName(backup):raise RuntimeError('Nelze dočasně přejmenovat původní timeline.')
  if not rebuilt.SetName(original_name):
   timeline.SetName(original_name);raise RuntimeError('Nelze pojmenovat rekonstruovanou timeline.')
  if not mp.DeleteTimelines([timeline]):life.log('INTRO_BACKUP_TIMELINE_RETAINED',timeline=backup)
  timeline_audio.configure(rebuilt)
  return rebuilt
 except Exception:
  try:mp.DeleteTimelines([rebuilt])
  except Exception:pass
  raise


def apply(mp,timeline,reference):
 if timeline is None:return timeline
 reference=Path(reference)
 if not reference.is_file():raise RuntimeError(f'Referenční znělka neexistuje: {reference}')
 match=detect(timeline,reference)
 if not match:
  life.log('INTRO_FINGERPRINT_NOT_FOUND',reference=str(reference));print(f'[WARN] Znělka {reference.name} nebyla nalezena s dostatečnou jistotou. Timeline zůstává beze změny.');return timeline
 try:
  rebuilt=_rebuild(mp,timeline,match['start_frame'],match['end_frame'])
 except Exception as e:
  life.log('INTRO_FINGERPRINT_ROUTING_FAILED',reference=str(reference),error=str(e));print(f'[WARN] Znělka nalezena, ale bezpečný střih/routing selhal: {e}');return timeline
 life.log('INTRO_FINGERPRINT_ROUTED',reference=str(reference),start_frame=match['start_frame'],end_frame=match['end_frame'],confidence=match['confidence'])
 print(f"[OK] Znělka {reference.name}: confidence {match['confidence']:.3f}, audio přesunuto na čistou stopu, střih na konci znělky.")
 return rebuilt
