import os
from tkinter import *
import tkinter.messagebox as tkMessageBox
from idlelib.uifactory import other_windows_open, set_allclosed_callback


class FileList:

    # N.B. this import overridden in PyShellFileList.
    from idlelib.EditorWindow import EditorWindow

    def __init__(self, root):
        self.root = root
        self.dict = {}
        self.inversedict = {}
        self.vars = {} # For EditorWindow.getrawvar (shared Tcl variables)
        import idlelib.uifactory
        idlelib.uifactory.initialize(root, avoid_ttk=False)
        set_allclosed_callback(self.auxilliary_windows_closed)

    def open(self, filename, action=None):
        assert filename
        filename = self.canonize(filename)
        if os.path.isdir(filename):
            # This can happen when bad filename is passed on command line:
            tkMessageBox.showerror(
                "File Error",
                "%r is a directory." % (filename,),
                master=self.root)
            return None
        key = os.path.normcase(filename)
        if key in self.dict:
            edit = self.dict[key]
            edit.top.wakeup()
            return edit
        if action:
            # Don't create window, perform 'action', e.g. open in same window
            return action(filename)
        else:
            edit = self.EditorWindow(self, filename, key)
            if edit.good_load:
                return edit
            else:
                edit._close()
                return None

    def gotofileline(self, filename, lineno=None):
        edit = self.open(filename)
        if edit is not None and lineno is not None:
            edit.gotoline(lineno)

    def new(self, filename=None):
        return self.EditorWindow(self, filename)

    def close_all_callback(self, *args, **kwds):
        for edit in list(self.inversedict):
            reply = edit.close()
            if reply == "cancel":
                break
        return "break"

    def auxilliary_windows_closed(self):
        "Callback from UIFactory when the last auxilliary window is closed"
        if not self.inversedict:
            self.root.quit()
        
    def register_editor_window(self, win, key=None):
        self.inversedict[win] = key
        if key:
            self.dict[key] = win
        
    def unregister_maybe_terminate(self, edit):
        try:
            key = self.inversedict[edit]
        except KeyError:
            print("Don't know this EditorWindow object.  (close)")
            return
        if key:
            del self.dict[key]
        del self.inversedict[edit]
        if not self.inversedict and not other_windows_open():
            self.root.quit()

    def filename_changed_edit(self, edit):
        edit.saved_change_hook()
        try:
            key = self.inversedict[edit]
        except KeyError:
            print("Don't know this EditorWindow object.  (rename)")
            return
        filename = edit.io.filename
        if not filename:
            if key:
                del self.dict[key]
            self.inversedict[edit] = None
            return
        filename = self.canonize(filename)
        newkey = os.path.normcase(filename)
        if newkey == key:
            return
        if newkey in self.dict:
            conflict = self.dict[newkey]
            self.inversedict[conflict] = None
            tkMessageBox.showerror(
                "Name Conflict",
                "You now have multiple edit windows open for %r" % (filename,),
                master=self.root)
        self.dict[newkey] = edit
        self.inversedict[edit] = newkey
        if key:
            try:
                del self.dict[key]
            except KeyError:
                pass

    def canonize(self, filename):
        if not os.path.isabs(filename):
            try:
                pwd = os.getcwd()
            except OSError:
                pass
            else:
                filename = os.path.join(pwd, filename)
        return os.path.normpath(filename)

    def configuration_will_change(self):
        "Callback from configuration dialog before settings are applied."
        for w in self.inversedict.keys():
            w.configuration_will_change()
        
    def configuration_changed(self):
        "Callback from configuration dialog after settings are applied."
        for w in self.inversedict.keys():
            w.configuration_changed()


def _test():
    from idlelib.EditorWindow import fixwordbreaks
    import sys
    root = Tk()
    fixwordbreaks(root)
    root.withdraw()
    flist = FileList(root)
    if sys.argv[1:]:
        for filename in sys.argv[1:]:
            flist.open(filename)
    else:
        flist.new()
    if flist.inversedict:
        root.mainloop()

if __name__ == '__main__':
    _test()
