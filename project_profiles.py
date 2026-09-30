#!/usr/bin/env python3
from __future__ import annotations
import configparser,re
from dataclasses import dataclass
from pathlib import Path
import resolve_lifecycle as life

APP=Path(__file__).resolve().parent
CONFIG=APP/'config.ini'

@dataclass(frozen=True)
class ProjectProfile:
 name:str
 match:str
 title_image:bool
 intro:str
 end_credits:bool
 silence_trim:str

def _flag(value,default=False):
 return str(value).strip().casefold() in ('1','true','yes','on') if value is not None else default

def _trim(value):
 value=str(value or '0').strip().casefold()
 return value if value in ('0','1','ask') else '0'

def resolve(project_name,config_path=CONFIG):
 p=configparser.ConfigParser(interpolation=None);p.optionxform=str;p.read(config_path,encoding='utf-8')
 sections=[s for s in p.sections() if s.casefold().startswith('profile:')]
 for section in sections:
  name=section.split(':',1)[1].strip() or section
  pattern=p.get(section,'Match',fallback='').strip()
  if not pattern:continue
  try:matched=re.search(pattern,project_name,re.I) is not None
  except re.error as exc:
   life.log('PROFILE_MATCH_INVALID',profile=name,pattern=pattern,error=str(exc));continue
  life.log('PROFILE_MATCH_TEST',project=project_name,profile=name,pattern=pattern,matched=matched)
  if not matched:continue
  profile=ProjectProfile(name,pattern,_flag(p.get(section,'TitleImage',fallback='0')),p.get(section,'Intro',fallback='0').strip(),_flag(p.get(section,'EndCredits',fallback='0')),_trim(p.get(section,'SilenceTrim',fallback='0')))
  life.log('PROFILE_MATCH',project=project_name,profile=profile.name)
  life.log('PROFILE_LAYERS',title_image=profile.title_image,intro=profile.intro,end_credits=profile.end_credits,silence_trim=profile.silence_trim)
  return profile
 profile=ProjectProfile('ImplicitDefault','',False,'0',False,'0')
 life.log('PROFILE_MATCH',project=project_name,profile=profile.name)
 life.log('PROFILE_LAYERS',title_image=False,intro='0',end_credits=False,silence_trim='0')
 return profile
