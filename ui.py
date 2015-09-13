"""
Central place for flags, variables, small utilities etc. that determine
how Tk is used throughout IDLE.
"""

import tkinter
from tkinter import ttk

# Should IDLE use themed-Tk widgets (ttk)?
using_ttk = False

# What windowing system are we using?
windowing_system = None     # will be set to 'aqua', 'win32', or 'x11'

# Do we need to include a Sizegrip widget?
need_sizegrip = False

# Cursor to use to indicate clickable things, like links - usually a hand
clickable_cursor = 'hand2'

# Tk root window for our application
root = None

# Initialize our common variables; this needs to be called before the
# variables can be used. We require this to avoid the overhead of creating
# a temporary Tk instance.

def init(root_, allow_ttk=True):
    global _initialized
    global root
    global using_ttk
    global windowing_system
    global need_sizegrip
    global clickable_cursor
    
    if _initialized:
        return
    root = root_
    if allow_ttk:
        try:
            b = ttk.Button(root)
            using_ttk = True
        except Exception:
            pass
    windowing_system = root.call('tk', 'windowingsystem')
    if windowing_system == 'aqua':
        clickable_cursor = 'pointinghand'
        import platform
        v, _, _ = platform.mac_ver()
        major, minor = v.split('.')[:2]
        if (int(major) == 10 and int(minor) < 7):
            need_sizegrip = True
    _initialized = True

_initialized = False


class Spinbox(tkinter.Spinbox):
    """
    A ttk::spinbox was added in Tk 8.5.9; use it if present, otherwise
    use a spinbox. Note the two have different options and methods, so this
    only works for the basics.
    """
    def __init__(self, master=None, cnf={}, **kw):
        hasTtkSpinbox = master and master.tk.call('info', 'commands',
                                                  'ttk::spinbox')
        base = 'ttk::spinbox' if hasTtkSpinbox else 'spinbox'
        tkinter.Widget.__init__(self, master, base, cnf, kw)
