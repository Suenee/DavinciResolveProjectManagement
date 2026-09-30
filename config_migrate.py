#!/usr/bin/env python3
from __future__ import annotations
import configparser
from pathlib import Path
APP=Path(__file__).resolve().parent
CURRENT=APP/'config.ini'; TEMPLATE=APP/'config.example.ini'
def load(path):
 p=configparser.ConfigParser(interpolation=None); p.optionxform=str; p.read(path,encoding='utf-8'); return p
def main():
 if not TEMPLATE.exists():raise SystemExit('ERROR: config.example.ini is missing.')
 if not CURRENT.exists():CURRENT.write_text(TEMPLATE.read_text(encoding='utf-8'),encoding='utf-8'); print('Created config.ini from config.example.ini.'); return 0
 current=load(CURRENT); template=load(TEMPLATE); added=[]
 if current.has_section('SilenceTrim') and current.has_option('SilenceTrim','Enabled'):
  current.remove_option('SilenceTrim','Enabled');added.append('removed legacy SilenceTrim.Enabled (now profile-controlled)')
 if current.has_section('IntroDetection') and current.has_option('IntroDetection','Folder'):
  legacy_intro=current.get('IntroDetection','Folder').strip();current.remove_option('IntroDetection','Folder')
  if legacy_intro:
   if not current.has_section('IntroPaths'):current.add_section('IntroPaths')
   if not any(v.strip().casefold()==legacy_intro.casefold() for _,v in current.items('IntroPaths')):current.set('IntroPaths','Legacy',legacy_intro);added.append('IntroPaths.Legacy (migrated from IntroDetection.Folder)')
 if current.has_section('Paths') and current.has_option('Paths','ProjectRoot'):
  legacy=current.get('Paths','ProjectRoot').strip()
  current.remove_option('Paths','ProjectRoot')
  if legacy and not any(v.strip().casefold()==legacy.casefold() for _,v in current.items('Paths')):
   key='Legacy';n=2
   while current.has_option('Paths',key):key=f'Legacy{n}';n+=1
   current.set('Paths',key,legacy);added.append(f'Paths.{key} (migrated from ProjectRoot)')
 for section in template.sections():
  if not current.has_section(section):current.add_section(section); added.append(f'[{section}]')
  existing={k.casefold():k for k,_ in current.items(section)}
  for key,value in template.items(section):
   if key.casefold() not in existing:current.set(section,key,value); added.append(f'{section}.{key}')
 if added:
  with CURRENT.open('w',encoding='utf-8',newline='') as f:current.write(f,space_around_delimiters=True)
  print('Migrated config.ini; added: '+', '.join(added))
 else:print('config.ini is up to date.')
 return 0
if __name__=='__main__':raise SystemExit(main())
