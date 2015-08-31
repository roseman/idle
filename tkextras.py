"""
Module tkextras -- helpers that extend Tkinter in ways useful to IDLE
"""

from tkinter import *
import sys
import platform


class IdleSpinbox(Spinbox):
    """
    A ttk::spinbox was added in Tk 8.5.9; use it if present, otherwise
    use a spinbox. Note the two have different options and methods, so this
    only works for the basics.
    """
    def __init__(self, master=None, cnf={}, **kw):
        hasTtkSpinbox = master and master.tk.call('info', 'commands',
                                                  'ttk::spinbox')
        base = 'ttk::spinbox' if hasTtkSpinbox else 'spinbox'
        Widget.__init__(self, master, base, cnf, kw)


def need_sizegrip():
    """
    Older versions of OS X in particular require a ttk::sizegrip widget
    at the bottom right corner of the window. This is no longer the case
    in more recent versions.
    """
    if sys.platform == 'darwin':
        v, _, _ = platform.mac_ver()
        major, minor = v.split('.')[:2]
        if (int(major) == 10 and int(minor) < 7):
            return True
    return False


def windowingsystem():
    """
    Approximation of the 'tk windowingsystem' call, based on guessing
    platform. We don't actually call it because we don't necessarily have
    a Tk window handle available.
    """
    if sys.platform == 'darwin':
        return 'aqua'
    elif sys.platform == 'win32':
        return 'win32'
    else:
        return 'x11'


def clickable_cursor():
    "Return an appropriate cursor for when things are clickable, e.g. links"
    if sys.platform == 'darwin':
        return 'pointinghand'
    else:
        return 'hand2'
        
    
class VerticalScrolledFrame(ttk.Frame):
    """A pure Tkinter vertically scrollable frame.

    * Use the 'interior' attribute to place widgets inside the scrollable frame
    * Construct and pack/place/grid normally
    * This frame only allows vertical scrolling
    """
    def __init__(self, parent, *args, **kw):
        ttk.Frame.__init__(self, parent, *args, **kw)

        # create a canvas object and a vertical scrollbar for scrolling it
        vscrollbar = ttk.Scrollbar(self, orient=VERTICAL)
        vscrollbar.pack(fill=Y, side=RIGHT, expand=FALSE)
        canvas = Canvas(self, bd=0, highlightthickness=0,
                        yscrollcommand=vscrollbar.set)
        canvas.pack(side=LEFT, fill=BOTH, expand=TRUE)
        vscrollbar.config(command=canvas.yview)

        # reset the view
        canvas.xview_moveto(0)
        canvas.yview_moveto(0)

        # create a frame inside the canvas which will be scrolled with it
        self.interior = interior = ttk.Frame(canvas)
        interior_id = canvas.create_window(0, 0, window=interior, anchor=NW)

        # track changes to the canvas and frame width and sync them,
        # also updating the scrollbar
        def _configure_interior(event):
            # update the scrollbars to match the size of the inner frame
            size = (interior.winfo_reqwidth(), interior.winfo_reqheight())
            canvas.config(scrollregion="0 0 %s %s" % size)
            
        interior.bind('<Configure>', _configure_interior)

        def _configure_canvas(event):
            if interior.winfo_reqwidth() != canvas.winfo_width():
                # update the inner frame's width to fill the canvas
                canvas.itemconfigure(interior_id, width=canvas.winfo_width())
        canvas.bind('<Configure>', _configure_canvas)

        return
