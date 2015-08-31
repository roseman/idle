"""

*** Hack of Roger's tabbed editor window extension to use uitabs.py

----

Tabbed Editor Window Extension
Version: 0.3

Author: Roger D. Serwy
        roger.serwy@gmail.com

Date: 2011-08-26

Add to the end of config-extensions.def

    [TabExtension]
    enable=1
    enable_shell = 0
    [TabExtension_cfgBindings]
    tab-new=<Control-Key-t>

"""
import sys

if sys.version_info.major == 3:
    from tkinter import *
    from . import EditorWindow
    from . import WindowList
    from . import ToolTip
    import tkinter.messagebox
    tkMessageBox = tkinter.messagebox
    from . import FileList
    xrange = range    

elif sys.version_info.major == 2:
    from Tkinter import *
    import EditorWindow
    import WindowList
    import ToolTip
    import tkMessageBox
    import FileList

else:
    raise(BaseException("Python v3 or v2 not detected. TabExtension will not work."))
   
from idlelib.uitabs import UITabs, UITabsObserver
 

WARN_MULTIPLE_TAB_CLOSING = True

class TabExtension(object):

    menudefs = [
        ('windows', [None,
                ('New Tab', '<<tab-new-event>>'),
       ]),]

    def __init__(self, editwin):
        self.editwin = editwin

        # monkey-patching the call backs to get updates to filename into tab bar
        editwin.undo.set_saved_change_hook(self.saved_change_hook)
        def updaterecentfileslist(x):
            editwin.update_recent_files_list(x)
            self.saved_change_hook()  # to reflect opened file names in tab bar
        editwin.io.updaterecentfileslist = updaterecentfileslist

        text = self.editwin.text
        text.bind('<<tab-new-event>>', self.tab_new_event)

        if 'TAB_MANAGER' in dir(editwin.top):
            # clone the tab master pointers
            self.TAB_FRAME = editwin.top    # containing widget
            self.tabmanager = editwin.top.TAB_MANAGER
            self.add_tab_for_frame()
            editwin.top.wakeup = self.wakeup
            editwin.top.TAB_MANAGER = None   # break reference, no longer needed
            return

        # INITIALIZE THE FIRST TAB MANAGER

        flist = self.editwin.flist
        self.tabmanager = tabmanager = TabManager(top=self.editwin.top, tab=self, flist=flist)
        tabmanager.ACTIVE = self

        # REPACK the EditorWindow widget contents into a Frame
        TOPLEVEL = self.editwin.top
        F = tabmanager.create_frame()
        F.wakeup = self.wakeup

        for elt in TOPLEVEL.pack_slaves():
            p = elt.pack_info()
            p['in'] = F
            elt.pack(**p)

        F.pack(side='top', fill=BOTH, expand=YES)
        F._lower() # fix Z-order

        # TODO: repack all grid and place widgets

        self.TAB_FRAME = F    # reference to container frame
        editwin.top = F

        self.add_tab_for_frame() # populate tab bar
        TOPLEVEL.after_idle(self.editwin.postwindowsmenu)   # need to change menu
        
        tabmanager.showtabs()

    def wakeup(self):
        self.select()
        
    def select(self, event=None):
        return self.tabmanager.tab_wakeup(tabframe=self)

    def closetab(self, event=None):
        return self.tabmanager.close_tab(tabframe=self)

    def add_tab_for_frame(self):
        self.tabmanager.addtab(tabframe=self)

    def tab_new_event(self, event=None):
        self.tabmanager.newtab()
        return "break"

    def saved_change_hook(self):
        self.editwin.saved_change_hook()
        self.tabmanager.tablabel(self, self.get_title())
        self.tabmanager.tabdirty(self, not self.editwin.get_saved())
        self.tabmanager.tabtooltip(self, self.get_filepath())
        # TODO self.tooltip.text = self.get_filepath()


    def get_filepath(self, event=None):
        f = self.editwin.long_title()
        if not f:
            f = 'Untitled'
        return f

    def get_title(self, event=None):
        short = self.editwin.short_title()
        if not short:
            short = "Untitled"
        return short

    def close(self):
        #print 'unloading tabextension.py'
        self.editwin = None
        self.TAB_FRAME = None
        self.tooltip = None



class TabManagerList(object):  # for window list
    def __init__(self):
        self.clients = []
        self.ACTIVE = None
        self.orig_LTL = WindowList.ListedToplevel  # save original

    def get_frame(self):
        if self.ACTIVE is not None:
            F = self.ACTIVE.create_frame()
        else:
            if self.clients:
                F = self.clients[0].create_frame()
            else:
                F = None # should not happen
        return F

    def set_active(self, t):
        if t in self.clients:
            self.ACTIVE = t
            self.postwindowsmenu()
        else:
            pass

    def postwindowsmenu(self, event=None):
        for t in self.clients:
            t.active_frame.editwin.postwindowsmenu()

    def add(self, m):
        TOPLEVEL = m.TOPLEVEL
        def change(event=None, m=m):
            tabmanagerlist.set_active(m)
        TOPLEVEL.bind('<FocusIn>', change, '+')

        self.clients.append(m)

    def remove(self, m):
        if m is self.ACTIVE:
            self.ACTIVE = None
        self.clients.remove(m)


tabmanagerlist = TabManagerList()

# MONKEY PATCH - temporarily replace the ListedTopLevel with a Frame
# object in the current TabManager window
def patch(func):
    def n(*arg, **kw):
        if tabmanagerlist.ACTIVE is not None:  # are there any toplevel windows?
            orig = WindowList.ListedToplevel  # save original
            def open_patch(*arg, **kw):
                return tabmanagerlist.get_frame()
            WindowList.ListedToplevel = open_patch  # patch it
            retval = func(*arg, **kw)   # call function
            WindowList.ListedToplevel = orig  # restore it
            return retval
        else:
            return func(*arg, **kw)   # call original function
    return n

FileList.FileList.open = patch(FileList.FileList.open)


class TabManager(UITabsObserver):   # for handling an instance of ListedTopLevel

    def __init__(self, top=None, tab=None, flist=None):
        
        self.flist = flist
        TOPLEVEL = self.TOPLEVEL = top
        self.CLOSE_FRAME = None
        self.active_frame = tab
        TOPLEVEL.protocol("WM_DELETE_WINDOW", self.closetoplevel)
        self.tabframes = {}  # map tabid -> tabframe
        self.nexttabid = 1
        tab_bar = self.tab_bar = UITabs(self.TOPLEVEL, self)
        tabmanagerlist.add(self)

    def showtabs(self):
        self.tab_bar.pack(side='top', fill=X, expand=NO, before=self.active_frame.TAB_FRAME)
        
    def create_frame(self):
        # make a FRAME for holding the editors,
        # duck-typing to mimic a Toplevel object

        TOPLEVEL = self.TOPLEVEL
        F = Frame(TOPLEVEL)
        F.state = lambda: "normal"
        F.wm_geometry = TOPLEVEL.wm_geometry
        F.protocol = lambda a,b: True    # override protocol requests
        F.wm_title = TOPLEVEL.wm_title   # pass-thru
        F.wm_iconname = TOPLEVEL.wm_iconname  # pass-thru
        F.TAB_MANAGER = self  # INDICATOR
        F._lower = F.lower
        F._lift = F.lift

        F.lift = lambda: "break"
        F.lower = lambda: "break"

        F.instance_dict = TOPLEVEL.instance_dict
        F.update_windowlist_registry = TOPLEVEL.update_windowlist_registry
        return F

    def newtab(self):
        patch(self.flist.new)()

    def addtab(self, tabframe=None):
        tabid = 't'+str(self.nexttabid)
        self.tabframes[tabid] = tabframe
        self.nexttabid += 1
        tabid = self.tab_bar.add(tabid=tabid, title=tabframe.get_title(),
                                 tooltip=tabframe.get_filepath())

    def handle_addtab(self, tabs):
        self.newtab()
        
    def handle_closetab(self, tabs, tabid):
        tabframe = self.tabframes[tabid]
        reply = tabframe.editwin.maybesave()
        if str(reply) == "cancel":
            return "cancel"
        tabs.remove(tabid)
        self.CLOSE_FRAME = tabframe
        del(self.tabframes[tabid])
        self.delayed_close()
        
    def tab_deselected(self, tabs, tabid):
        pass
        
    def tab_selected(self, tabs, tabid):
        self.tab_wakeup(tabframe=self.tabframes[tabid])
    
    
    def tabidfromframe(self, tabframe):
        for tabid, frame in self.tabframes.items():
            if frame == tabframe:
                return tabid
        return None
        
    def tablabel(self, tabframe, label):
        self.tab_bar.set_title(self.tabidfromframe(tabframe), label)
        
    def tabdirty(self, tabframe, dirty):
        self.tab_bar.set_dirty(self.tabidfromframe(tabframe), dirty)

    def tabtooltip(self, tabframe, tooltip):
        self.tab_bar.set_tooltip(self.tabidfromframe(tabframe), tooltip)
        
    def tab_wakeup(self, tabframe=None):
        #print 'tab_wakeup', tabframe.get_title()

        if self.active_frame is tabframe:
            return # already awake

        self.tab_bar.select(self.tabidfromframe(tabframe))

        self.TOPLEVEL.pack_propagate(False)
        if self.active_frame:
            self.active_frame.TAB_FRAME.pack_forget()

        tabframe.TAB_FRAME.pack(fill=BOTH, expand=YES)
        self.active_frame = tabframe

        # switch toplevel menu
        TOPLEVEL = self.TOPLEVEL
        TOPLEVEL.config(menu=None)   # restore menubar

        def later(TOPLEVEL=TOPLEVEL, tabframe=tabframe):
            TOPLEVEL.config(menu=tabframe.editwin.menubar)   # restore menubar
            TOPLEVEL.update_idletasks()  # critical for avoiding flicker (on Linux at least)
            TOPLEVEL.lift()  # fix a bug caused in Compiz? where a maximized window loses the menu bar
            TOPLEVEL.focused_widget=tabframe.editwin.text  # for windowlist wakeup
            tabframe.editwin.text.focus_set()
            TOPLEVEL.pack_propagate(True)

        TOPLEVEL.after_idle(later)

        TOPLEVEL.after_idle(tabframe.saved_change_hook)
        TOPLEVEL.after_idle(tabmanagerlist.postwindowsmenu)  # need to change only the menus of active tabs

        if self.CLOSE_FRAME is not None:  # to prevent flicker when the recently closed tab was active
            self.delayed_close()


    def _close(self):
        self.TOPLEVEL.destroy()
        tabmanagerlist.remove(self)

    def delayed_close(self):
        # for when closing the active tab,
        # to prevent flicker of the GUI when closing the active frame
        tabframe = self.CLOSE_FRAME
        if tabframe is not None:
            tabframe.editwin._close()
            if len(self.tabframes) == 0:   # last tab closed
                self._close()
        self.CLOSE_FRAME = None


    def closetoplevel(self, event=None):
        if self.closewarning() == False:
            return "break"

        for tabid, tabframe in self.tabframes.items():
            if not tabframe.editwin.get_saved():
                self.tab_wakeup(tabframe)
            reply = tabframe.editwin.maybesave()
            if str(reply) == "cancel":
                return "break"

        # close all tabs
        for tabid, tabframe in self.tabframes.items():
            tabframe.editwin._close()

        self._close()
        return "break"

    def closewarning(self, event=None):
        if not WARN_MULTIPLE_TAB_CLOSING:
            return True

        L = len(self.tabframes)
        if L > 1:
            res = tkMessageBox.askyesno(
                        "Close Multiple Tabs?",
                        "Do you want to close %i tabs?" % L,
                        default="no",
                        master=self.TOPLEVEL)
        else:
            res = True
        return res



