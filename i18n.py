#!/usr/bin/env python3
from __future__ import annotations
import configparser, ctypes, gettext, locale
from pathlib import Path
APP=Path(__file__).resolve().parent
CONFIG=APP/'config.ini'; LOCALE_DIR=APP/'locale'; DOMAIN='drpm'
DEFAULT_LANGUAGE='en'; SUPPORTED=('en','cs')
LANGUAGE_NAMES={'auto':'Automatic','en':'English','cs':'Čeština'}
def _configured_language():
 p=configparser.ConfigParser(interpolation=None);p.read(CONFIG,encoding='utf-8')
 return p.get('General','Language',fallback='auto').strip().casefold() or 'auto'
def _windows_language():
 try:
  lang_id=ctypes.windll.kernel32.GetUserDefaultUILanguage()
  return locale.windows_locale.get(lang_id,'').split('_',1)[0].casefold()
 except Exception:return ''
def resolve_language(value=None):
 value=(value or _configured_language()).casefold()
 if value=='auto':value=_windows_language()
 return value if value in SUPPORTED else DEFAULT_LANGUAGE
def available_languages():return ['auto']+list(SUPPORTED)
def translation(language=None):
 code=resolve_language(language)
 if code=='en':return gettext.NullTranslations()
 return gettext.translation(DOMAIN,localedir=str(LOCALE_DIR),languages=[code],fallback=True)
_current=translation()
def set_language(language=None):
 global _current;_current=translation(language);return resolve_language(language)
def _(message):return _current.gettext(message)
