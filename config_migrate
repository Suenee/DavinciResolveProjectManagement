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
