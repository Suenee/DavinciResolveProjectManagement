#!/usr/bin/env python3
from __future__ import annotations
import configparser
from pathlib import Path

def configured_roots(parser: configparser.ConfigParser) -> list[tuple[str, Path]]:
    if not parser.has_section('Paths'):
        return []
    out=[];seen=set()
    for key,value in parser.items('Paths'):
        raw=value.strip()
        if not raw:
            continue
        path=Path(raw)
        norm=str(path).rstrip('\\/').casefold()
        if norm in seen:
            continue
        seen.add(norm);out.append((key,path))
    return out

def available_roots(parser: configparser.ConfigParser) -> list[tuple[str, Path]]:
    return [(key,path) for key,path in configured_roots(parser) if path.is_dir()]

def active_root(parser: configparser.ConfigParser) -> Path:
    configured=configured_roots(parser)
    available=[item for item in configured if item[1].is_dir()]
    if available:
        return available[0][1]
    if not configured:
        raise RuntimeError('No project paths are configured in [Paths].')
    tried='; '.join(f'{key}={path}' for key,path in configured)
    raise RuntimeError(f'None of the configured project paths exists: {tried}')

def named_paths(parser: configparser.ConfigParser, section: str) -> list[tuple[str, Path]]:
    if not parser.has_section(section):
        return []
    out=[];seen=set()
    for key,value in parser.items(section):
        raw=value.strip()
        if not raw: continue
        path=Path(raw);norm=str(path).rstrip('\\/').casefold()
        if norm in seen: continue
        seen.add(norm);out.append((key,path))
    return out

def first_available_named_path(parser: configparser.ConfigParser, section: str) -> Path | None:
    for _,path in named_paths(parser,section):
        if path.is_dir(): return path
    return None
