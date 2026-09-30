#!/usr/bin/env python3
from __future__ import annotations
import configparser,re,unicodedata
from datetime import datetime,timedelta
from difflib import SequenceMatcher
from pathlib import Path
import managed_builder as m
import resolve_lifecycle as life

IMAGE_EXT={'.jpg','.jpeg','.png','.webp','.tif','.tiff','.bmp'}

def config():
 p=configparser.ConfigParser(interpolation=None);p.read(m.CONFIG,encoding='utf-8')
 return {'root':p.get('TimelineAssets','TitlesRoot',fallback=r'O:\Sueneé Universe\YouTube Channel\Titles\%Y').strip(),
         'title_seconds':p.getint('TimelineAssets','TitleDurationSeconds',fallback=20),
         'credits_file':p.get('TimelineAssets','EndCreditsFile',fallback=r'Credits\endcredits.jpg').strip(),
         'credits_seconds':p.getint('TimelineAssets','EndCreditsDurationSeconds',fallback=25),
         'boundary_days':p.getint('TimelineAssets','YearBoundaryToleranceDays',fallback=14),
         'candidate_count':p.getint('TimelineAssets','TitleCandidateCount',fallback=5),
         'auto_score':p.getfloat('TimelineAssets','TitleAutoMatchScore',fallback=0.88)}

def year_path(template,year):return Path(template.replace('%Y',str(year)))
def years_to_search(now,boundary):
 years=[now.year]
 if now-datetime(now.year,1,1)<timedelta(days=boundary):years.append(now.year-1)
 if datetime(now.year+1,1,1)-now<timedelta(days=boundary):years.append(now.year+1)
 return years

def normalize(text):
 text=unicodedata.normalize('NFKD',text);text=''.join(c for c in text if not unicodedata.combining(c)).casefold()
 return ' '.join(re.findall(r'[a-z0-9]+',text))

def _title_core(path):
 stem=path.stem
 stem=re.sub(r'^\s*\d{1,2}[-_.]\d{1,2}\s*[-–—]\s*','',stem)
 stem=re.sub(r'^\s*suenee\s*[-–—]\s*','',stem,flags=re.I)
 return normalize(stem)

def title_candidates(project_name,now=None):
 now=now or datetime.now();c=config();query=normalize(m.nodate(project_name));found=[]
 for year in years_to_search(now,c['boundary_days']):
  folder=year_path(c['root'],year)
  if not folder.is_dir():continue
  for path in folder.iterdir():
   if not path.is_file() or path.suffix.casefold() not in IMAGE_EXT:continue
   core=_title_core(path);score=SequenceMatcher(None,query,core).ratio()
   found.append((score,path))
 # Similarity decides relevance. For equal/similar candidates the visible order is filename Z-A.
 found.sort(key=lambda x:x[1].name.casefold(),reverse=True)
 found.sort(key=lambda x:x[0],reverse=True)
 top=found[:max(1,c['candidate_count'])]
 life.log('TITLE_CANDIDATES',project=project_name,query=query,candidates=[{'file':str(p),'match_name':_title_core(p),'score':round(s,4)} for s,p in top])
 return top

def choose_title(project_name,selector):
 c=config();top=title_candidates(project_name)
 if top and top[0][0]>=c['auto_score'] and (len(top)==1 or top[0][0]-top[1][0]>=0.08):
  life.log('TITLE_AUTO_SELECTED',file=str(top[0][1]),score=top[0][0]);return top[0][1]
 chosen=selector(project_name,[p for _,p in top],c['root']) if selector else None
 if chosen is False:return False
 life.log('TITLE_MANUAL_SELECTION',file=str(chosen) if chosen else None);return Path(chosen) if chosen else None

def find_credits(now=None):
 now=now or datetime.now();c=config()
 # Current year first, then walk backwards. Around New Year also test adjacent configured year.
 years=years_to_search(now,c['boundary_days'])
 for y in range(now.year-1,max(now.year-10,0),-1):
  if y not in years:years.append(y)
 for year in years:
  p=year_path(c['root'],year)/c['credits_file']
  life.log('END_CREDITS_TEST',year=year,file=str(p),exists=p.is_file())
  if p.is_file():life.log('END_CREDITS_SELECTED',year=year,file=str(p));return p
 life.log('END_CREDITS_SKIPPED',reason='not_found');return None
