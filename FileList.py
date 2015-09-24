import os
from tkinter import *
import tkinter.messagebox as tkMessageBox
from idlelib.container import Container, TabbedContainer, ProxyContainer


class FileList:

    # N.B. this import overridden in PyShellFileList.
    from idlelib.EditorWindow import EditorWindow

    def __init__(self, root):
        self.root = root
        self.dict = {}
        self.inversedict = {}
        self.containers = {}
        self.tab_container = None
        self.using_tabs = True
        self.vars = {} # For EditorWindow.getrawvar (shared Tcl variables)

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
            edit.wakeup()
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

    def new_container(self, own_window=False):
        "Return a new Container for a component"
        if self.using_tabs and not own_window:
            if self.tab_container is None:
                self.tab_container = TabbedContainer(self)
            return ProxyContainer(self.tab_container)
        else:
            return Container(self)

    def register_editor_window(self, win, key=None):
        self.inversedict[win] = key
        if key:
            self.dict[key] = win

    def already_open(self, filename):
        assert filename
        filename = self.canonize(filename)
        if not os.path.isdir(filename):
            key = os.path.normcase(filename)
            return key in self.dict
        return False

    def gotofileline(self, filename, lineno=None):
        edit = self.open(filename)
        if edit is not None and lineno is not None:
            edit.gotoline(lineno)

    def new(self, filename=None):
        return self.EditorWindow(self, filename)

    def new_topwindow(self, event=None):
        self.tab_container = None
        return self.new()

    def close_all_callback(self, *args, **kwds):
        for edit in list(self.inversedict):
            reply = edit.close()
            if reply == "cancel":
                break
        return "break"

    def keep_running(self):
        "Application should stay running while any editors are open"
        return len(self.inversedict) > 0

    def unregister_maybe_terminate(self, edit):
        try:
            key = self.inversedict[edit]
        except KeyError:
            print("Don't know this EditorWindow object.  (close)")
            return
        if key:
            del self.dict[key]
        del self.inversedict[edit]
        if not self.inversedict:
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
        self.root.after_idle(self.filenames_changed)

    # note: replacement for WindowList.add
    def add_container(self, container):
        container.w.after_idle(self.filenames_changed)
        self.containers[str(container)] = container
        
    # note: replacement for WindowList.delete
    def delete_container(self, container):
        if self.tab_container == container:
            self.tab_container = None
        try:
            del self.containers[str(container)]
        except KeyError:
            # Sometimes, destroy() is called twice
            pass
        self.filenames_changed()
        
    # note: replaces callbacks from WindowList; whereas those needed to be
    # explicitly registered for and unregistered from, here we just send
    # the notice to every component
    def filenames_changed(self):
        "Callback when one or more filenames changed"
        for w in self.inversedict.keys():
            w.filenames_changed()
            
    def add_windows_to_menu(self,  menu):
        list = []
        for key in self.containers:
            container = self.containers[key]
            try:
                title = container.get_title()
            except TclError:
                continue
            list.append((title, key, container))
        list.sort()
        for title, key, container in list:
            if container.component is not None:
                menu.add_command(label=title,
                                 command=container.component.wakeup)

    def configuration_will_change(self):
        "Callback from configuration dialog before settings are applied."
        for w in self.inversedict.keys():
            w.configuration_will_change()

    def configuration_changed(self):
        "Callback from configuration dialog after settings are applied."
        for w in self.inversedict.keys():
            w.configuration_changed()

    def apply_breakpoints(self, applycmd):
        "Callback from debugger asking each editor to apply it's breakpoints"
        for w in self.inversedict.keys():
            try:    # only PyShellEditorWindow will support this callback
                w.apply_breakpoints(applycmd)
            except Exception:
                pass

    def rebuild_recent_files_menu(self, rf_list):
        "Called when all editors need to rebuild their recent files menus"
        for w in self.inversedict.keys():
            w.rebuild_recent_files_menu(rf_list)

    def canonize(self, filename):
        if not os.path.isabs(filename):
            try:
                pwd = os.getcwd()
            except OSError:
                pass
            else:
                filename = os.path.join(pwd, filename)
        return os.path.normpath(filename)


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
