""" Display IDLE's help file
"""

from idlelib import sphinxview
from os import path

win = None

def show(parent):
    "Main routine; show dialog window, creating or raising as necessary."
    global win
    if win is None:
        fn = path.join(path.abspath(path.dirname(__file__)), 'idle.html')
        win = sphinxview.SphinxHTMLViewerWindow(parent, fn, 'IDLE Help')
        win.protocol("WM_DELETE_WINDOW", _destroy)
    win.lift()
    win.focus_set()

def _destroy():
    global win
    win.destroy()
    win = None
