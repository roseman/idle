"""
Standalone 'tabs' widget to switch between multiple different views.

Unlike the Tkinter ttk.Notebook widget, this widget is suitable for
displaying a potentially large number of tabs, as might be found in a
tabbed editor. If there are too many tabs to show based on the available
width, the remainder can be viewed via a popup menu on the last tab.

Tabs can be rearranged by dragging, closed, or new tabs added. Each tab
can have a title which is displayed in the tab, a tooltip for when the
mouse hovers over the tab, and a 'dirty' indicator that can be used to
indicate files needing to be saved.

The appearance and behaviour of the tabs is strongly influenced by the
TextMate editor on Mac OS X.

Implementation is via a single Tkinter canvas.

Unlike many other tabbed widgets, this widget does not take care of
actually switching content being displayed; this is left to the caller.

A UITabsObserver (see below) must be provided to the widget, and is
used to notify the caller when changes are made that must be reflected
in other parts of the user interface.
"""

from tkinter import *
from tkinter.font import Font


class UITabs(Frame):
    def __init__(self, parent, observer):
        Frame.__init__(self, parent)
        self.parent = parent
        self.observer = observer

        self.tabs = []          # list of tab id's
        self.info = {}          # info on each tab
        self.drag = None        # state information when drag in progress
        self.current = None     # id of currently selected tab
        self.mouseover = None   # id of tab the mouse is currently over
        self.tooltip = None     # state information for tooltips
        self.last_x = -1
        self.nextid = 1

        self.define_appearance()
        self.c = Canvas(self, highlightthickness=0, borderwidth=0)
        self.c.grid(column=0, row=0, sticky='nwes')
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.c['background'] = self.bg
        self.c['height'] = self.height
        self.bind('<Configure>', self.rebuild)
        self.c.bind('<Motion>', self.mouse_moved)
        self.c.bind('<Leave>', self.leave)
        self.c.bind('<1>', self.mouse_down)
        self.c.bind('<B1-Motion>', self.mouse_dragged)
        self.c.bind('<ButtonRelease-1>', self.mouse_up)

    def add(self, tabid=None, title=None, dirty=False, tooltip=None):
        "Add a new tab"
        if tabid is None:
            while 'tab'+str(self.nextid) in self.tabs:
                self.nextid += 1
            tabid = 'tab'+str(self.nextid)
            self.nextid += 1
        if tabid in self.tabs:
            raise ValueError('tab already added')
        self.tabs.append(tabid)
        self.info[tabid] = {'title': title, 'dirty': dirty, 'tooltip': tooltip}
        self.select(tabid)
        return tabid

    def remove(self, tabid):
        "Remove an existing tab"
        if tabid not in self.tabs:
            raise ValueError('no such tab')
        self.tooltip_clear()
        idx = self.tabs.index(tabid)
        del(self.info[tabid])
        self.tabs.remove(tabid)
        if tabid == self.current:
            if len(self.tabs) == 0:
                self.current = None
            elif idx > len(self.tabs)-1:
                self.current = self.tabs[-1]
            else:
                self.current = self.tabs[idx]
            if self.current is not None:
                self.observer.tab_selected(self, self.current)
        self.update_mouseover(self.last_x)
        self.rebuild()

    def select(self, tabid):
        "Change the currently selected (frontmost) tab."
        if tabid not in self.tabs:
            raise ValueError('no such tab')
        if self.current != tabid:
            self.observer.tab_deselected(self, self.current)
            self.current = tabid
            self.rebuild()
            self.observer.tab_selected(self, self.current)

    def set_title(self, tabid, title):
        "Change the title of a tab"
        if tabid not in self.tabs:
            raise ValueError('no such tab')
        self.info[tabid]['title'] = title
        self.rebuild()

    def set_dirty(self, tabid, dirty=True):
        "Change the saved/unsaved indicator for a tab"
        if tabid not in self.tabs:
            raise ValueError('no such tab')
        self.info[tabid]['dirty'] = dirty
        self.rebuild()

    def set_tooltip(self, tabid, tooltip):
        "Change the tooltip for a tab"
        if tabid not in self.tabs:
            raise ValueError('no such tab')
        self.info[tabid]['tooltip'] = tooltip

    def mouse_moved(self, ev):
        self.last_x = ev.x
        self.update_mouseover(ev.x)

    def leave(self, ev):
        self.mouseover = None
        self.tooltip_clear()
        self.last_x = -1
        self.rebuild()

    def mouse_down(self, ev):
        self.drag_initiate(ev)

    def mouse_dragged(self, ev):
        self.drag_continue(ev)

    def mouse_up(self, ev):
        self.drag_conclude(ev)

    def define_appearance(self):
        self.height = 22
        self.minwidth = 130
        self.maxwidth = 300
        self.addiconwidth = 24
        self.gapwidth = 15
        self.bg = '#c4c4c4'
        self.selbg = '#d3d3d3'
        self.dividerbg = '#b0b0b0'
        self.textcolor = '#424242'
        self.holecolor = '#eeeeee'
        self.titlefont = Font(name='TkTooltipFont', exists=True,
                              root=self.parent)
        self.tooltipfont = Font(name='TkTooltipFont', exists=True,
                                root=self.parent)
        self.plusfont = Font(name='TkMenuFont', exists=True, root=self.parent)

    def calculate_positions(self):
        "Update state info on each tab needed for display, e.g. position"
        self.tabwidth = tabwidth = self.calculate_tabwidth()
        displayed = []
        extra = []
        xpos = 0
        # Step 1: Calculate positions for each tab that will fit on the
        #         display, and note which tabs won't fit
        for t in self.tabs:
            if xpos + tabwidth > self.winfo_width() - self.addiconwidth:
                self.info[t]['visible'] = False
                extra.append(t)
            else:
                self.info[t]['visible'] = True
                self.info[t]['left'] = xpos
                self.info[t]['shift'] = 0
                displayed.append(t)
                xpos += tabwidth
            self.info[t]['tablabel'] = self.tablabel(self.info[t]['title'],
                                                     tabwidth-40)
        # Step 2: If we're in the middle of dragging a tab, potentially
        #         to move it, we indicate a place where it can be dropped
        #         via a gap between tabs. If such a gap has been identified
        #         (see drag_identifygap), open up a space by moving all tabs
        #         to the left of the gap a bit more left, and all tabs to
        #         the right of the gap a bit more right.
        if self.drag is not None and self.drag['state'] == 'inprogress' \
                                 and self.drag['gap'] is not None:
            gap = self.drag['gap']
            tabidx = self.tabs.index(self.drag['tabid'])
            idx = 0
            for t in self.tabs:
                if self.info[t]['visible']:
                    if idx < gap:
                        self.info[t]['shift'] = -self.gapwidth
                    elif idx >= gap:
                        self.info[t]['shift'] = +self.gapwidth
                idx += 1
        # Step 3: If the currently selected tab will not fit on the screen
        #         because there are too many tabs before it on the list,
        #         swap the last displayed tab with the currently selected
        #         one, to ensure it is displayed. Note this doesn't update
        #         the actual order (in self.tabs), just display state info.
        if self.current in extra:
            last = displayed[-1]
            self.info[self.current]['visible'] = True
            self.info[self.current]['left'] = self.info[last]['left']
            self.info[self.current]['shift'] = self.info[last]['shift']
            self.info[last]['visible'] = False
            del(self.info[last]['left'])
            del(self.info[last]['shift'])
            displayed.remove(last)
            extra.insert(0, last)
            extra.remove(self.current)
            displayed.append(self.current)
        self.overflow_tab = displayed[-1] if extra else None
        self.plus_x = xpos

    def calculate_tabwidth(self):
        "Determine width of a tab, factoring in available space, etc."
        fullwidth = self.winfo_width()
        numtabs = len(self.tabs)
        if numtabs == 0:
            return -1
        tabwidth = int((fullwidth - self.addiconwidth) / numtabs)
        if tabwidth < self.minwidth:
            tabwidth = self.minwidth
        if tabwidth > self.maxwidth:
            tabwidth = self.maxwidth
        return tabwidth

    def tablabel(self, title, width):
        "Truncate any long titles that would not fit within the tab label"
        if self.titlefont.measure(title) <= width:
            return title
        dotwidth = self.titlefont.measure('...')
        while True:
            if self.titlefont.measure(title+'...') <= width:
                return title+'...'
            title = title[:-1]

    def update_mouseover(self, x):
        "Determine if the tab our mouse is over has changed, and adjust if so"
        nowover = self.tabunder(x) if x != -1 else None
        if nowover != self.mouseover:
            self.tooltip_clear()
            self.mouseover = nowover
            self.rebuild()
            if nowover is not None and \
                            self.info[nowover]['tooltip'] is not None:
                self.tooltip_schedule()

    def tabunder(self, x):
        "Identify which tab is at a given position"
        for t in self.tabs:
            if self.info[t]['visible'] and self.info[t]['left'] <= x <\
                                self.info[t]['left'] + self.tabwidth:
                return t
        return None

    def rebuild(self, ev=None):
        """
        Update the display to match the current state of the user interface.
        This actually draws all the pieces of the tabs, indicators, etc. on
        the canvas. We take a brute force approach and recreate everything
        from scratch each time we're called, which happens on any significant
        state change.
        """
        self.c.delete('all')
        if self.winfo_width() < self.addiconwidth:
            return
        self.calculate_positions()
        tabwidth = self.tabwidth
        for t in self.tabs:
            if not self.info[t]['visible']:
                continue
            lbl = self.info[t]['tablabel']
            xpos = self.info[t]['left'] + self.info[t]['shift']

            color = self.selbg if t == self.current else self.bg
            rect = self.c.create_rectangle(xpos, 0, xpos + tabwidth - 2,
                            self.height, fill=color, outline=color)
            self.c.tag_bind(rect, '<ButtonRelease-1>',
                            lambda ev=None, t=t: self.select(t))

            self.c.create_line(xpos-1, 0, xpos-1,
                            self.height, fill=self.dividerbg)
            self.c.create_line(xpos+tabwidth-1, 0, xpos+tabwidth-1,
                            self.height, fill=self.dividerbg)
            color = self.textcolor
            if self.drag is not None and self.drag['state'] == 'inprogress' \
                                     and self.drag['tabid'] == t:
                color = self.holecolor
            txt = self.c.create_text(xpos + tabwidth / 2, self.height - 3,
                                   anchor='s', text=lbl, fill=color,
                                   font=self.titlefont)
            self.c.tag_bind(txt, '<ButtonRelease-1>',
                            lambda ev=None, t=t: self.select(t))
            if self.info[t]['dirty']:
                close = self.c.create_oval(xpos+4, self.height-13, xpos+10,
                            self.height-7, fill=self.textcolor,
                            outline=self.textcolor, activefill='red',
                            activeoutline='red')
                self.c.tag_bind(close, '<1>',
                            lambda ev=None, t=t: self.closetab(t, ev))
            elif t == self.mouseover:
                if self.drag is None or self.drag['state'] != 'inprogress':
                    close = self.c.create_text(xpos+8, self.height-3,
                                    anchor='s', text='x', fill=self.textcolor,
                                    activefill='red', font=self.plusfont)
                    self.c.tag_bind(close, '<ButtonRelease-1>',
                                    lambda ev=None, t=t: self.closetab(t, ev))
            if t == self.overflow_tab:
                more = self.c.create_text(xpos + tabwidth - 12,
                            self.height - 5, anchor='s', text='>>',
                            fill=self.textcolor, font=self.titlefont)
                self.c.tag_bind(more, '<1>', self.post_extras_menu)
        plus = self.c.create_text(self.plus_x+self.addiconwidth/2,
                            self.height-3, anchor='s', text='+',
                            fill=self.textcolor, font=self.plusfont)
        self.c.tag_bind(plus, '<ButtonRelease-1>', self.addtab)
        self.drag_createitems()

    def addtab(self, ev=None):
        self.observer.handle_addtab(self)

    def closetab(self, tabid, ev):
        self.observer.handle_closetab(self, tabid)

    def post_extras_menu(self, ev):
        "Show a menu for selecting the tabs that do not fit onscreen"
        self.tooltip_clear()
        self.calculate_positions()
        menu = Menu(self, tearoff=0)
        for t in self.tabs:
            if not self.info[t]['visible']:
                menu.add_command(label=self.info[t]['title'],
                                 command=lambda t=t: self.select(t))
        menu.tk_popup(ev.x_root, ev.y_root)

    def drag_initiate(self, ev):
        tabid = self.tabunder(ev.x)
        if tabid is not None:
            self.drag = {'state': 'pending', 'tabid': tabid,
                         'offsetx': ev.x - (self.info[tabid]['left'] +
                                            self.tabwidth/2),
                         'offsety': ev.y - (self.height - 3),
                         'x': ev.x, 'y': ev.y}

    def drag_continue(self, ev):
        if self.drag is None:
            return
        if self.drag['state'] == 'pending':
            if abs(ev.x - self.drag['x']) > 3 or \
                            abs(ev.y - self.drag['y']) > 3:
                self.drag['state'] = 'inprogress'
                self.drag['x'] = ev.x - self.drag['offsetx']
                self.drag['y'] = ev.y - self.drag['offsety']
                self.drag['gap'] = None
                self.rebuild()
        elif self.drag['state'] == 'inprogress':
            self.drag['x'] = ev.x - self.drag['offsetx']
            self.drag['y'] = ev.y - self.drag['offsety']
            self.c.coords(self.drag['textitem'],
                          (self.drag['x'], self.drag['y']))
            self.drag_identifygap(ev.x, ev.y)

    def drag_conclude(self, ev):
        if self.drag is not None and self.drag['state'] == 'inprogress':
            self.drag_identifygap(ev.x, ev.y)
            gap = self.drag['gap']
            if gap is not None:
                curidx = self.tabs.index(self.drag['tabid'])
                if gap > curidx:
                    gap -= 1
                self.tabs.remove(self.drag['tabid'])
                self.tabs.insert(gap, self.drag['tabid'])
        self.drag = None
        self.rebuild()

    def drag_createitems(self):
        "Called by rebuild to create canvas items for drag in progress"
        if self.drag is not None and self.drag['state'] == 'inprogress':
            if self.drag['gap'] is not None:
                x = self.drag['gap'] * self.tabwidth
                self.c.create_rectangle(x-self.gapwidth, 0, x+self.gapwidth,
                            self.height, fill=self.holecolor,
                            outline=self.holecolor)
            label = self.info[self.drag['tabid']]['tablabel']
            self.drag['textitem'] = self.c.create_text(self.drag['x'],
                            self.drag['y'], text=label, font=self.titlefont,
                            fill=self.textcolor, anchor='s')

    def drag_identifygap(self, x, y):
        gap = None
        for t in self.tabs:
            if not self.info[t]['visible']:
                continue
            left = self.info[t]['left']
            if left <= x <= left + self.tabwidth / 2:
                gap = self.tabs.index(t)
                break
            elif left + self.tabwidth / 2 <= x <= left + self.tabwidth:
                gap = self.tabs.index(t) + 1
                break
        tabidx = self.tabs.index(self.drag['tabid'])
        if gap is not None and (tabidx == gap or tabidx + 1 == gap):
            gap = None
        if y < 0 or y > self.height:
            gap = None
        if gap != self.drag['gap']:
            self.drag['gap'] = gap
            self.rebuild()

    def tooltip_schedule(self):
        self.tooltip_clear()
        self.tooltip = {'window': None,
                        'afterid': self.after(1500, self.tooltip_display)}

    def tooltip_clear(self):
        if self.tooltip is not None:
            if self.tooltip['window'] is not None:
                self.tooltip['window'].destroy()
            if self.tooltip['afterid'] is not None:
                self.after_cancel(self.tooltip['afterid'])
            self.tooltip = None

    def tooltip_display(self):
        self.tooltip['afterid'] = None
        if self.mouseover is None:
            return
        x = self.winfo_rootx() + self.info[self.mouseover]['left'] + 20
        y = self.winfo_rooty() + self.height + 5
        txt = self.info[self.mouseover]['tooltip']
        tw = self.tooltip['window'] = Toplevel(self)
        tw.wm_withdraw()
        tw.wm_geometry("+%d+%d" % (x, y))
        tw.wm_overrideredirect(1)
        try:
            tw.tk.call("::tk::unsupported::MacWindowStyle", "style", tw._w,
                       "help", "noActivates")
        except TclError:
            pass
        lbl = Label(tw, text=txt, justify=LEFT, background="#ffffe0",
                    borderwidth=0, font=self.tooltipfont)
        if self.tk.call('tk', 'windowingsystem') != 'aqua':
            lbl['borderwidth'] = 1
            lbl['relief'] = 'solid'
        lbl.pack()
        tw.update_idletasks()  # calculate window size to avoid resize flicker
        tw.deiconify()
        tw.lift()  # needed to work around bug in Tk 8.5.18+ (issue #24570)


class UITabsObserver(object):
    """
    Protocol that UITabs widget uses for callbacks on significant user
    interface events that the caller will generally need to respond to.
    """
    def __init__(self):
        pass

    def handle_addtab(self, tabs):
        # tabs.add(tabid, title)
        pass

    def handle_closetab(self, tabs, tabid):
        tabs.remove(tabid)

    def tab_deselected(self, tabs, tabid):
        pass

    def tab_selected(self, tabs, tabid):
        pass


if __name__ == '__main__':
    class TabsDemo(UITabsObserver):
        def __init__(self):
            self.count = 1
            root = Tk()
            tabs = UITabs(root, self)
            tabs.grid(column=0, row=0, sticky='ew')
            Text(root, height=5).grid(column=0, row=1, sticky='nwes')
            root.grid_rowconfigure(1, weight=1)
            root.grid_columnconfigure(0, weight=1)
            tabs.add(tabid='l1', title='uitabs.py',
                     tooltip='/full/path/to/uitabs.py')
            tabs.add(tabid='l2', title='OutputWindow.py', dirty=True)
            tabs.add(tabid='l3', title='veryLongNameToTestThingsOutCrash.py',
                    tooltip='Really, a long name')
            tabs.select('l1')
            root.mainloop()

        def handle_addtab(self, tabs):
            tabs.add(title='Untitled '+str(self.count))
            self.count += 1

    TabsDemo()
