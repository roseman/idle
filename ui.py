"""
Central place for flags, variables, small utilities etc. that determine
how Tk is used throughout IDLE.
"""

import os
import tkinter
from tkinter import ttk
from tkinter.font import Font

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

# Classes for widgets that have ttk counterparts; since they'll have
# different options, code will need to check which they're using for all
# but the simplest things
Button = tkinter.Button
Frame = tkinter.Frame
Label = tkinter.Label
Scrollbar = tkinter.Scrollbar
Spinbox = tkinter.Spinbox
PanedWindow = tkinter.PanedWindow
Entry = tkinter.Entry
Checkbutton = tkinter.Checkbutton
Radiobutton = tkinter.Radiobutton


# Initialize our common variables; this needs to be called before the
# variables can be used. We require this to avoid the overhead of creating
# a temporary Tk instance.

def init(root_, allow_ttk=True):
    global _initialized, root, using_ttk, windowing_system, need_sizegrip,\
           clickable_cursor, Button, Frame, Label, Scrollbar, PanedWindow,\
           Spinbox, Entry, Checkbutton, Radiobutton
    
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
    try:
        _tooltipfont = Font(name='TkTooltipFont', exists=True, root=root)
    except tkinter.TclError:
        _tooltipfont = Font(family='helvetica', size=10, root=root)
    if using_ttk:
        Button = ttk.Button
        Frame = ttk.Frame
        Label = ttk.Label
        Scrollbar = ttk.Scrollbar
        PanedWindow = ttk.PanedWindow
        Entry = ttk.Entry
        Checkbutton = ttk.Checkbutton
        Radiobutton = ttk.Radiobutton
        Spinbox = _Spinbox  # see below
    if windowing_system == 'aqua':
        clickable_cursor = 'pointinghand'
        import platform
        v, _, _ = platform.mac_ver()
        major, minor = v.split('.')[:2]
        if (int(major) == 10 and int(minor) < 7):
            need_sizegrip = True
        # NOTE: Tk 8.6 defines a <<ContextMenu>> event
        root.event_add('<<context-menu>>', '<Button-2>', '<Control-Button-1>')
    else:
        root.event_add('<<context-menu>>', '<Button-3>')
    _initialized = True

_initialized = False
_tooltipfont = None


def padframe(frame, padding):
    "Convenience procedure to add padding to a frame, ttk or otherwise"
    try:
        frame['padding'] = padding
    except tkinter.TclError:
        frame['padx'] = padding
        frame['pady'] = padding
    return frame

def image(filename):
    "Return an image object for a file in our 'Icons' directory"
    dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'Icons')
    return tkinter.PhotoImage(master=root, file=os.path.join(dir, filename))


class _Spinbox(tkinter.Spinbox):
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


# TODO - duplication from uitabs.py
_tooltip = None

def tooltip_clear():
    global _tooltip
    if _tooltip is not None:
        if _tooltip['window'] is not None:
            _tooltip['window'].destroy()
        if _tooltip['afterid'] is not None:
            _tooltip['event'].widget.after_cancel(_tooltip['afterid'])
        _tooltip = None

def tooltip_schedule(event, callback):
    global _tooltip
    tooltip_clear()
    _tooltip = {'window': None, 'event': event, 'callback': callback,
                'afterid': event.widget.after(1500, _tooltip_display)}

def _tooltip_display():
    global _tooltip
    _tooltip['afterid'] = None
    event = _tooltip['event']
    callback = _tooltip['callback']
    _tooltip['event'] = None
    _tooltip['callback'] = None
    ret = callback(event)
    if ret is not None:
        txt, x, y = ret
        tw = _tooltip['window'] = tkinter.Toplevel(event.widget)
        tw.wm_withdraw()
        tw.wm_geometry("+%d+%d" % (x, y))
        tw.wm_overrideredirect(1)
        try:
            tw.tk.call("::tk::unsupported::MacWindowStyle", "style",
                       tw._w, "help", "noActivates")
        except tkinter.TclError:
            pass
        lbl = tkinter.Label(tw, text=txt, justify='left',
                      background="#ffffe0", borderwidth=0, font=_tooltipfont)
        if windowing_system != 'aqua':
            lbl['borderwidth'] = 1
            lbl['relief'] = 'solid'
        lbl.pack()
        tw.update_idletasks()  # calculate window size to avoid resize flicker
        tw.deiconify()
        tw.lift()  # needed to work around bug in Tk 8.5.18+ (issue #24570)
