"""
Object that holds a Component, e.g. editor

For now, a toplevel, but later a frame too...
"""

import platform
from tkinter import *
from idlelib.statusbar import Statusbar
from idlelib.uitabs import UITabs, UITabsObserver


_py_version = ' (%s)' % platform.python_version()


class Container(object):
    def __init__(self, flist):
        self.flist = flist
        self.component = None               # caller sets via add_component
        self.w = self.make_widget()         # w: widget component packs into
        self.top = self.w.winfo_toplevel()  # top: toplevel for this container
        self.statusbar = None
        if self.flist:
            self.flist.add_container(self)

    def make_widget(self):
        t = Toplevel(self.flist.root)
        t.protocol('WM_DELETE_WINDOW', self._close)
        t.bind("<<close-window>>", lambda e: self._close())
        return t

    def add_component(self, component):
        self.component = component
        self.w.after_idle(self.title_changed)

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

    def ping_statusbar(self):   #  later - 'metadata_changed'?
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


class TabbedContainer(Container, UITabsObserver):

    def __init__(self, flist):
        Container.__init__(self, flist)
        self.containers = {}    # map tab to container
        self.active = None

    def add_component(self, component):
        id = self.tabs.add(title='Shell***')
        self.containers[id] = component.top

    def make_widget(self):
        t = Container.make_widget(self)
        self.tabs = UITabs(t, self)
        self.tabs.pack(side='top', fill='x')
        self.main = Frame(t)
        self.main.pack(side='top', fill='both')
        return t

    def move_to_front(self, component):
        Container.move_to_front(self, component)
        tabid = self.get_tabid(component.top)
        self.tabs.select(tabid)

    def handle_addtab(self, tabs):
        self.flist.new()

    def remove(self, container):
        tabid = self.get_tabid(container)
        if tabid is not None:
            if container == self.active:
                self.tab_deselected(self.tabs, tabid)
                self.active = None
            del(self.containers[tabid])
            self.tabs.remove(tabid)
            if len(self.containers) == 0:
                self._close()

    def _close(self):
        "Close button on window - try to close all tabs"
        # loop through all dirty containers, if nobody aborts, we're good
        # to close the whole window
        for t, c in self.containers.items():
            if c.component is not None and not c.component.get_saved():
                # NOTE: while maybesave() does move the tab to the front,
                #       because of deferred drawing plus the 'after_idle' in
                #       our tab_selected routine, the changes don't appear
                #       onscreen immediately.
                #
                #       This is normally not a problem, but because this may
                #       be immediately followed by a modal dialog call which
                #       blocks the update events, we ensure everything is
                #       onscreen before calling maybesave()
                self.move_to_front(c.component)
                self.w.update()
                self.w.update_idletasks()
                if c.component.maybesave() == 'cancel':
                    return      # user aborted the close
        for t, c in self.containers.items():
            if c.component is not None:
                c.component.close(without_save=True)  # already asked
        self.w.destroy()
        self.w = None
        self.component = None
        if self.flist:
            self.flist.delete_container(self)

    def handle_closetab(self, tabs, tabid):
        self.containers[tabid]._close()

    def tab_deselected(self, tabs, tabid):
        if len(self.containers) == 0:
            return
        self.w.pack_propagate(False)
        self.containers[tabid].w.pack_forget()
        self.w['menu'] = None

    def setup_statusbar(self):
        if self.statusbar is None:
            self.create_statusbar()

    def get_tabid(self, container):
        for t in self.containers:
            if self.containers[t] == container:
                return t
        return None

    def container_title_changed(self, container):
        tabid = self.get_tabid(container)
        if tabid is not None:
            self.tabs.set_title(tabid, container.short_title)
            if container.title is not None:
                self.tabs.set_tooltip(tabid, container.title)
            self.tabs.set_dirty(tabid, not container.saved)
        if container == self.active:
            self.w.wm_title(container.title if container.title else container.short_title)
            self.w.wm_iconname(container.short_title)

    def tab_selected(self, tabs, tabid):
        self.w.after_idle(lambda: self._tab_selected(tabid))

    def _tab_selected(self, tabid):
        if self.active != self.containers[tabid]:
            self.active = self.containers[tabid]
            self.active.w.pack(side='top', fill='both')
            self.w['menu'] = self.active.menubar
            self.statusbar.observe(self.active.component)
            self.container_title_changed(self.active)
            self.w.pack_propagate(True)


class ProxyContainer(Container):
    def __init__(self, top_container):
        self.top_container = top_container
        Container.__init__(self, top_container.flist)
        self.short_title = ''
        self.title = ''
        self.saved = ''
        self.menubar = None

    def _close(self):
        if self.component is not None:
            try:
                self.component.close()
                self.top_container.remove(self)
            except Exception:       # if file needs saving, user may abort
                pass

    def add_component(self, component):
        Container.add_component(self, component)
        self.top_container.add_component(component)

    def make_widget(self):
        return Frame(self.top_container.w)

    def active(self):
        return self.top_container.active == self

    def title_changed(self):
        self.short_title = self.component.short_title()
        self.long_title = self.component.long_title()
        self.saved = self.component.get_saved()
        self.top_container.container_title_changed(self)

    def get_title(self):
        return self.title

    def set_menubar(self, menu):
        self.menubar = menu
        if self.active():
            self.top_container.set_menubar(menu)

    def setup_statusbar(self):
        self.top_container.setup_statusbar()

    def ping_statusbar(self):
        if self.active():
            self.top_container.ping_statusbar()

    def move_to_front(self, component):
        self.top_container.move_to_front(component)
