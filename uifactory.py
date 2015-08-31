"""Create IDLE user interface components, factoring in any backwards
   compatibility constraints, e.g. Tk8.4 vs. Tk8.5.

   We also keep track of the non-editor windows running in the application,
   so there is some overlap/coordination with FileList.py
"""

from tkinter import *


def initialize(root, avoid_ttk=False):
    "Should be called before using rest of this module."
    global _inst
    _inst = _UIFactory(root, avoid_ttk)


def open_about():
    "Open the application's about dialog."
    _inst.open_about()


def open_preferences(editor_window):
    """Open the preferences dialog, as requested by the given editor window.

    Note that we use the editor window only when starting, to position the
    preferences dialog, as well as retrieve the file list that the editor
    window is part of. The provided editor window may be destroyed while
    the preferences dialog is still active (e.g. if the dialog is not modal).
    """
    _inst.open_preferences(editor_window)


def askstring(prompt=None, title=None, parent=None, 
              initialvalue=None, oklabel=None, validatecmd=None):
    "Post a modal dialog which returns a string or None."
    return _inst.askstring(prompt=prompt, title=title, parent=parent, 
               initialvalue=initialvalue, oklabel=oklabel,
               validatecmd=validatecmd)

def askinteger(prompt=None, title=None, parent=None,
               initialvalue=None, oklabel=None, min=None, max=None):
    "Post a modal dialog which returns an integer or None."
    return _inst.askinteger(prompt=prompt, title=title,  parent=parent, 
               initialvalue=initialvalue, oklabel=oklabel, min=min, max=max)


def using_ttk():
    return _inst.using_ttk()


def other_windows_open():
    "Return True if any of the non-editor windows we manage is open."
    return _inst.other_windows_open()


def set_allclosed_callback(cmd):
    "We'll notify when the last window we manage closes; used by FileList"
    _inst.set_allclosed_callback(cmd)


class _UIFactory(object):
    def __init__(self, root, avoid_ttk=False):
        self.root = root
        self.using_ttk = False
        self.windows = {}
        self.allclosed_callback = None
        if not avoid_ttk and TkVersion >= 8.5:
            try:
                from tkinter import ttk
                self.using_ttk = True
            except:
                pass

    def open_about(self):
        if 'about' not in self.windows.keys():
            from idlelib.aboutDialog import AboutDialog
            self.windows['about'] = AboutDialog(self.root, 'About IDLE',
                            must_be_modal=False,
                            destroy_callback=lambda: self._destroyed('about'))
        self.windows['about'].lift()

    def open_preferences(self, editor_window):
        if 'prefs' not in self.windows.keys():
            if self.using_ttk:
                from idlelib.uipreferences import PreferencesDialog
                self.windows['prefs'] = PreferencesDialog(parent=self.root,
                            observer=editor_window.flist,
                            destroy_callback=lambda: self._destroyed('prefs'))
            else:
                from idlelib.configDialog import ConfigDialog
                self.windows['prefs'] = ConfigDialog(editor_window,
                            'Settings', must_be_modal=False,
                            destroy_callback=lambda: self._destroyed('prefs'))
        self.windows['prefs'].lift()

    def askstring(self, prompt=None, title=None, parent=None, 
                  initialvalue=None, oklabel=None, validatecmd=None):
        from idlelib.querydialog import askstring
        if parent is None:
            parent = self.root
        return askstring(prompt=prompt, title=title, parent=parent,
                         initialvalue=initialvalue, validatecmd=validatecmd,
                         oklabel=oklabel, use_ttk=self.using_ttk)

    def askinteger(self, prompt=None, title=None, parent=None, 
                   initialvalue=None, oklabel=None, min=None, max=None):
        from idlelib.querydialog import askinteger
        if parent is None:
            parent = self.root
        return askinteger(prompt=prompt, title=title, parent=parent,
                          initialvalue=initialvalue, min=min, max=max,
                          oklabel=oklabel, use_ttk=self.using_ttk)

    def _destroyed(self, key):
        if key in self.windows.keys():
            del self.windows[key]
            if not self.other_windows_open() and self.allclosed_callback:
                self.allclosed_callback()

    def using_ttk(self):
        return self.using_ttk

    def other_windows_open(self):
        return len(self.windows) > 0

    def set_allclosed_callback(self, cmd):
        self.allclosed_callback = cmd


_inst = None

if __name__ == '__main__':
    root = Tk()
    initialize(root)
