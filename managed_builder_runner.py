#!/usr/bin/env python3
from __future__ import annotations
import ctypes
import os
import socket
import threading
import managed_builder
import project_update
import project_update_dialog
import project_browser
import ui_windows

_base_create_initial_timeline=managed_builder.create_initial_timeline
_INSTANCE_PORT=47631
_instance_server=None
_active_root=None


def _center_above_resolve(root):
 global _active_root
 _active_root=root
 ui_windows.center_and_place_above_resolve(root)


def _choose(candidates,query):
 return project_browser.choose_project(candidates,query)


def _create_initial_timeline(mp,master,shoot,name,intro_first=None):
 return _base_create_initial_timeline(mp,master,shoot,name,intro_first)


def _activate_current():
 root=_active_root
 if root is not None:
  try:root.after(0,lambda:ui_windows.activate_window(root))
  except Exception:pass


def _instance_loop(server):
 while True:
  try:
   conn,_=server.accept()
   with conn:
    data=conn.recv(64)
    if data.startswith(b'ACTIVATE'):_activate_current()
  except OSError:return
  except Exception:continue


def _claim_instance():
 global _instance_server
 if os.name!='nt':return True
 server=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
 try:
  server.bind(('127.0.0.1',_INSTANCE_PORT));server.listen(2);_instance_server=server
  threading.Thread(target=_instance_loop,args=(server,),daemon=True).start()
  return True
 except OSError:
  try:
   with socket.create_connection(('127.0.0.1',_INSTANCE_PORT),timeout=1.0) as client:client.sendall(b'ACTIVATE')
  except OSError:pass
  server.close();return False


managed_builder.center=_center_above_resolve
managed_builder.choose=_choose
project_update.ask=project_update_dialog.ask
project_update.set_intro_selector(project_update_dialog.choose_intro)
project_update.set_timeline_creator(_create_initial_timeline)
managed_builder.build=project_update.build

if __name__=='__main__':
 if not _claim_instance():raise SystemExit(0)
 raise SystemExit(managed_builder.main())
