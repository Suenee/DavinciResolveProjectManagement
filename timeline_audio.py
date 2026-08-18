#!/usr/bin/env python3
from __future__ import annotations
import configparser
from pathlib import Path
import resolve_lifecycle as life

APP = Path(__file__).resolve().parent
CONFIG = APP / 'config.ini'


def _settings():
    p = configparser.ConfigParser()
    p.read(CONFIG, encoding='utf-8')
    amount = p.getint('Timeline', 'VoiceIsolationAmount', fallback=100)
    amount = max(0, min(100, amount))
    create_clean = p.getboolean('Timeline', 'CreateCleanAudioTrack', fallback=True)
    clean_name = p.get('Timeline', 'CleanAudioTrackName', fallback='AUDIO').strip()
    return amount, create_clean, clean_name


def configure(timeline):
    if timeline is None:
        raise RuntimeError('Timeline pro audio konfiguraci neexistuje.')
    if not hasattr(timeline, 'SetVoiceIsolationState'):
        raise RuntimeError('Tato verze DaVinci Resolve nepodporuje scripting API pro Voice Isolation.')

    amount, create_clean, clean_name = _settings()
    source_tracks = int(timeline.GetTrackCount('audio') or 0)

    for track_index in range(1, source_tracks + 1):
        if not timeline.SetVoiceIsolationState(track_index, {'isEnabled': True, 'amount': amount}):
            raise RuntimeError(f'Nelze zapnout Voice Isolation na audio stopě A{track_index}.')

    clean_track_index = None
    if create_clean:
        subtype = 'stereo'
        if source_tracks > 0:
            try:
                subtype = timeline.GetTrackSubType('audio', 1) or 'stereo'
            except Exception:
                subtype = 'stereo'
        if not timeline.AddTrack('audio', subtype):
            raise RuntimeError('Nelze vytvořit prázdnou audio stopu bez Voice Isolation.')
        clean_track_index = int(timeline.GetTrackCount('audio') or 0)
        if clean_track_index < 1:
            raise RuntimeError('Nová audio stopa nebyla po vytvoření nalezena.')
        if not timeline.SetVoiceIsolationState(clean_track_index, {'isEnabled': False, 'amount': 0}):
            raise RuntimeError(f'Nelze vypnout Voice Isolation na audio stopě A{clean_track_index}.')
        if clean_name:
            try:
                timeline.SetTrackName('audio', clean_track_index, clean_name)
            except Exception:
                pass

    life.log('TIMELINE_AUDIO_CONFIGURED', source_tracks=source_tracks, voice_isolation_amount=amount, clean_track=clean_track_index)
    print(f'[OK] Voice Isolation: A1-A{source_tracks} = ON ({amount} %)' if source_tracks else '[OK] Voice Isolation: žádná zdrojová audio stopa')
    if clean_track_index:
        print(f'[OK] Prázdná audio stopa A{clean_track_index}: Voice Isolation = OFF')
    return timeline
