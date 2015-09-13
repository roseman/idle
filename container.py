"""
Object that holds a Component, e.g. editor

For now, a toplevel, but later a frame too...
"""

from tkinter import Toplevel

class Container(object):
    def __init__(self, flist):
        self.flist = flist
        self.component = None               # component should set this
        self.focus_widget = None
        self.w = self.make_widget()         # w: widget component packs into
        self.top = self.w.winfo_toplevel()  # top: toplevel for this container
        if self.flist:
            self.flist.add_container(self)

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

    def set_title(self, title, short_title=None):
        self.w.wm_title(title)
        if short_title is not None:
            self.w.wm_iconname(short_title)

    def get_title(self):
        return self.w.wm_title()

    def set_menubar(self, menu):
        self.w['menu'] = menu

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
