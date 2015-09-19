"""
Object that holds a Component, e.g. editor

For now, a toplevel, but later a frame too...
"""

import platform
from tkinter import *
from idlelib.statusbar import Statusbar


_py_version = ' (%s)' % platform.python_version()


class Container(object):
    def __init__(self, flist):
        self.flist = flist
        self.component = None               # component should set this
        self.w = self.make_widget()         # w: widget component packs into
        self.top = self.w.winfo_toplevel()  # top: toplevel for this container
        self.statusbar = None
        if self.flist:
            self.flist.add_container(self)
        self.w.after_idle(self.title_changed)

    def make_widget(self):
        t = Toplevel(self.flist.root)
        t.protocol('WM_DELETE_WINDOW', self._close)
        t.bind("<<close-window>>", lambda e: self._close())
        return t

    def _close(self):
        if self.component is not None:
            try:
                self.component.close()
                self.w.destroy()
                self.w = None
                self.component = None
                if self.flist:
                    self.flist.delete_container(self)
            except Exception:       # if file needs saving, user may abort
                pass

    def title_changed(self):
        if self.component is not None:
            short = self.component.short_title()
            long = self.component.long_title()
            if short and long:
                title = short + " - " + long + _py_version
            elif short:
                title = short
            elif long:
                title = long
            else:
                title = "Untitled"
            icon = short or long or title
            if not self.component.get_saved():
                title = "*%s*" % title
                icon = "*%s" % icon
            self.w.wm_title(title)
            self.w.wm_iconname(icon)

    def get_title(self):
        return self.w.wm_title()

    def set_menubar(self, menu):
        self.w['menu'] = menu

    def setup_statusbar(self):
        self.create_statusbar()
        self.statusbar.observe(self.component)

    def create_statusbar(self):
        self.statusbar = Statusbar(self.w)
        self.statusbar.pack(side=BOTTOM, fill=X)

    def ping_statusbar(self):   # TODO later - 'metadata_changed'?
        if self.statusbar is not None:
            self.statusbar.update()

    def move_to_front(self, component): 
        "Adjust the container so the given component is brought forward."
        # we can ignore component parameter for now, as base container
        # supports only a single component
        try:
            if self.w.wm_state() == "iconic":
                self.w.wm_withdraw()
                self.w.wm_deiconify()
            self.w.tkraise()
        except TclError:
            # This can happen when the window menu was torn off.
            # Simply ignore it.
            pass
