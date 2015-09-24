"""
IDLE interactive debugger user interface.

The organization of the window has changed greatly from earlier versions.
Most notably:
 * works with both Tk 8.4 and 8.5+
 * paned window separates left and right, allowing adjusting relative sizes
 * on left, toolbar with graphical/text buttons, plus message, and stack
 * on right, local and global variables of selected stack frame
 * running program can be interrupted via 'stop' button
 * stack and variables use listbox (8.4) or tree (with resizable columns)
 * removed locals, globals, and stack 'view' options
 * source option changed to auto-open windows to see source
 * can always view source by double-clicking or context menu in stack
 * full value of variable can be seen via tooltip in variable list
 
In future, this will also replace the 'stack viewer' feature for displaying
exceptions, but this has not yet been integrated.
"""

import os
import bdb
import linecache
from tkinter import *
from tkinter import ttk
from tkinter.font import Font
from idlelib.ScrolledList import ScrolledList
from idlelib import macosxSupport
from idlelib import ui
from idlelib.component import Component


    
def underscore_at_end(s):   
    # return a key that will sort variable names like __foo__ below others
    return s.replace('_', '~')      # note: ~ is after letters in ASCII


class Idb(bdb.Bdb):

    def __init__(self, gui):
        self.gui = gui
        bdb.Bdb.__init__(self)

    def user_line(self, frame):
        if self.in_rpc_code(frame):
            self.set_step()
            return
        message = self.__frame2message(frame)
        self.gui.interaction(message, frame)

    def user_exception(self, frame, info):
        if self.in_rpc_code(frame):
            self.set_step()
            return
        message = self.__frame2message(frame)
        self.gui.interaction(message, frame, info)

    def in_rpc_code(self, frame):
        if frame.f_code.co_filename.count('rpc.py'):
            return True
        else:
            prev_frame = frame.f_back
            if prev_frame.f_code.co_filename.count('Debugger.py'):
                # (that test will catch both Debugger.py and RemoteDebugger.py)
                return False
            return self.in_rpc_code(prev_frame)

    def __frame2message(self, frame):
        code = frame.f_code
        filename = code.co_filename
        lineno = frame.f_lineno
        basename = os.path.basename(filename)
        message = "%s:%s" % (basename, lineno)
        if code.co_name != "?":
            message = "%s: %s()" % (message, code.co_name)
        return message


class Debugger(Component):

    vstack = vsource = vlocals = vglobals = None

    def __init__(self, pyshell, idb=None):
        Component.__init__(self, pyshell.flist)
        if idb is None:
            idb = Idb(self)
        self.framevars = {}
        self.pyshell = pyshell
        self.idb = idb
        self.frame = None
        self._ttk = ui.using_ttk
        self.make_gui()
        self.interacting = 0
        self.nesting_level = 0
        self.running = False

    def run(self, *args):
        if self.nesting_level > 0:
            self.abort_loop()
            self.root.after(100, lambda: self.run(*args))
            return
        try:
            self.interacting = 1
            return self.idb.run(*args)
        finally:
            self.interacting = 0

    def beginexecuting(self):
        self.running = True

    def endexecuting(self):
        self.abort_loop()
        self.running = False
        self.show_status('')
        self.enable_buttons(['prefs'])
        self.clear_stack()

    def close(self, event=None, without_save=False):
        if self.interacting:
            self.top.top.bell()
            return
        self.abort_loop()
        # Clean up pyshell if user clicked debugger control close widget.
        # (Causes a harmless extra cycle through close_debugger() if user
        # toggled debugger from pyshell Debug menu)
        self.pyshell.close_debugger()
        # NOTE: container will invoke this, so we don't need to destroy it

    def make_gui(self):
        pyshell = self.pyshell
        self.flist = pyshell.flist
        self.root = root = pyshell.root
        self.tooltip = None
        self.var_values = {}
        _ttk = self._ttk
        self.top = top = self.flist.new_container(own_window=True)
        self.top.add_component(self)
        self.top.w.bind("<Escape>", self.close)
        self.var_open_source_windows = BooleanVar(top.w, False)
        
        self.pane = ui.PanedWindow(self.top.w, orient='horizontal')
        self.pane.grid(column=0, row=0, sticky='nwes')
        self.top.w.grid_columnconfigure(0, weight=1)
        self.top.w.grid_rowconfigure(0, weight=1)
        self.left = left = ui.padframe(ui.Frame(self.pane), 5)
        if _ttk:
            self.pane.add(left, weight=1)
        else:
            self.pane.add(left, stretch='always', sticky='nsew')
        controls = ui.Frame(left)
        col = 0
        f = ('helvetica', 9)
        self.buttondata = {}
        self.buttons = ['go', 'step', 'over', 'out', 'stop', 'prefs']
        self.button_names = {'go':'Go', 'step':'Step', 'over':'Over',
                             'out':'Out', 'stop':'Stop', 'prefs':'Options'}
        self.button_cmds = {'go':self.cont, 'step':self.step, 
                            'over':self.next, 'out':self.ret, 
                            'stop':self.quit, 'prefs':self.options}
        for key in self.buttons:
            normal = ui.image('debug_'+key+'.gif')
            disabled = ui.image('debug_'+key+'_disabled.gif')
            b = ui.Label(controls, image=normal, text=self.button_names[key], 
                          compound='top', font=f)
            b.grid(column=col, row=0, padx=[0,5])
            self.buttondata[key] = (b, normal, disabled)
            col += 1
        self.enable_buttons(['prefs'])
        self.status = ui.Label(controls, text=' ', font=('helvetica', 13))
        self.status.grid(column=6, row=0, sticky='nw', padx=[25,0])
        controls.grid(column=0, row=0, sticky='new', pady=[0,6])
        controls.grid_columnconfigure(7, weight=1)

        self.current_line_img = ui.image('debug_current.gif')
        self.regular_line_img = ui.image('debug_line.gif')
        if _ttk:
            self.stack = ttk.Treeview(left, columns=('statement', ),
                                      height=5, selectmode='browse')
            self.stack.column('#0', width=100)
            self.stack.column('#1', width=150)
            self.stack.tag_configure('error', foreground='red')
        else:
            self.stack = Listbox(left, height=5, width=35, selectmode='browse',
                     exportselection=False, activestyle='none')
        self.stack.bind('<<TreeviewSelect>>' if _ttk else '<<ListboxSelect>>', 
                        lambda e: self.stack_selection_changed())
        self.stack.bind('<Double-1>', lambda e: self.stack_doubleclick())
        self.stack.bind('<<context-menu>>', self.stack_contextmenu)

        scroll = ui.Scrollbar(left, command=self.stack.yview)
        self.stack['yscrollcommand'] = scroll.set
        self.stack.grid(column=0, row=2, sticky='nwes')
        scroll.grid(column=1, row=2, sticky='ns')
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(2, weight=1)

        right = ui.padframe(ui.Frame(self.pane), 5)
        if _ttk:
            self.pane.add(right, weight=1)
        else:
            self.pane.add(right, stretch='always', sticky='nsew')
        if _ttk:
            self.vars = ttk.Treeview(right, columns=('value',), height=5,
                                                    selectmode='none')
            self.locals = self.vars.insert('', 'end', text='Locals', 
                                           open=True)
            self.globals = self.vars.insert('', 'end', text='Globals',
                                            open=False)
            self.vars.column('#0', width=100)
            self.vars.column('#1', width=150)
        else:
            self.vars = Listbox(right, height=5, width=35, selectmode='none',
                    exportselection=False, activestyle='none')
        self.vars.bind('<Motion>', self.mouse_moved_vars)
        self.vars.bind('<Leave>', self.leave_vars)
        scroll2 = ui.Scrollbar(right, command=self.vars.yview)
        self.vars['yscrollcommand'] = scroll2.set
        self.vars.grid(column=0, row=0, sticky='nwes')
        scroll2.grid(column=1, row=0, sticky='ns')
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=1)
        left.bind('<Configure>', lambda e: self._adjust_layout())
        self.clear_stack()
        

    def _adjust_layout(self):
        # if too narrow, move message below buttons
        if self.left.winfo_width() < 380:
            self.status.grid(column=0, row=1, columnspan=8, padx=[5,0])
        else:
            self.status.grid(column=6, row=0, columnspan=1, padx=[25,0])

    def enable_buttons(self, buttons=None):
        for key in self.buttons:
            if buttons is None or not key in buttons:
                self.buttondata[key][0]['image'] = self.buttondata[key][2]
                self.buttondata[key][0]['foreground'] = '#aaaaaa'
                self.buttondata[key][0]['cursor'] = ''
                self.buttondata[key][0].bind('<1>', 'break')
                self.buttondata[key][0].bind('<<context-menu>>', 'break')
            else:
                self.buttondata[key][0]['image'] = self.buttondata[key][1]
                self.buttondata[key][0]['foreground'] = '#000000'
                self.buttondata[key][0].bind('<1>', self.button_cmds[key])
                self.buttondata[key][0].bind('<<context-menu>>',
                                             self.button_cmds[key])
                self.buttondata[key][0]['cursor'] = ui.clickable_cursor

    def stack_selection_changed(self):
        self.show_vars()

    def stack_doubleclick(self):
        sel = self.stack.selection() if self._ttk else \
                                    self.stack.curselection()
        if len(sel) == 1:
            self.show_source(sel[0])

    def stack_contextmenu(self, event):
        if self._ttk:
            item = self.stack.identify('item', event.x, event.y)
        else:
            item = self.stack.nearest(event.y)
        if item is not None and item != -1 and item != '':
            menu = Menu(self.top.w, tearoff=0)
            menu.add_command(label='View Source',
                             command = lambda: self.show_source(item))
            menu.tk_popup(event.x_root, event.y_root)

    def show_source(self, item):
        if item in self.framevars:
            fname = self.framevars[item][2]
            lineno = self.framevars[item][3]
            if fname[:1] + fname[-1:] != "<>" and os.path.exists(fname):
                self.flist.gotofileline(fname, lineno)

    def show_status(self, msg, error=False):
        self.status['text'] = msg
        self.status['foreground'] = '#ff0000' if error else '#006600'
        self.status['font'] = ('helvetica', 13, 'italic') if error \
                            else ('helvetica', 13)

    def clear_stack(self):
        if self._ttk:
            self.stack.delete(*self.stack.get_children(''))
            self.vars.delete(*self.vars.get_children(self.locals))
            self.vars.delete(*self.vars.get_children(self.globals))
            self.vars.detach(self.locals)
            self.vars.detach(self.globals)
        else:
            self.stack.delete(0, 'end')
            self.vars.delete(0, 'end')
        self.var_values = {}
        
    def add_stackframe(self, frame, lineno, current=False):
        func = frame.f_code.co_name
        if func in ("?", "", None):
            func = '.'
        try:
            selfval = frame.f_locals['self']
            if selfval.__class__.__name__ == 'str':
                # we've probably got the string representation of the 
                # object sent from the remote debugger, see if we can
                # parse it into something useful
                match = re.match('^<(?:.*)\.([^\.]*) object at 0x[0-9a-f]+>$',
                                 selfval)
                if match:
                    func = match.group(1) + '.' + func
            else:
                func = selfval.__class__.__name__ + '.' + func
        except Exception:
            pass
        stmt = linecache.getline(frame.f_code.co_filename, lineno).strip()
        if self._ttk:
            image=self.current_line_img if current else self.regular_line_img
            item = self.stack.insert('', 'end', text=func, 
                                   values=(stmt,), image=image)
        else:
            self.stack.insert('end', func + '  ' + stmt)
            item = self.stack.index('end') - 1
        self.framevars[item] = (frame.f_locals, frame.f_globals,
                                frame.f_code.co_filename, lineno)
        if current:
            if not self._ttk:
                self.stack.selection_clear(0, 'end')
            self.stack.selection_set(item)

    def interaction(self, message, frame, info=None):
        self.frame = frame
        self.show_status(message)
        #
        if info:
            type, value, tb = info
            try:
                m1 = type.__name__
            except AttributeError:
                m1 = "%s" % str(type)
            if value is not None:
                try:
                    m1 = "%s: %s" % (m1, str(value))
                except:
                    pass
        else:
            m1 = ""
            tb = None
        if m1 != '':
            self.show_status(m1, error=True)
            
        stack, idx = self.idb.get_stack(self.frame, tb)
        self.clear_stack()
        for i in range(len(stack)):
            frame, lineno = stack[i]
            self.add_stackframe(frame, lineno, current=(i == idx))
        self.show_vars()
        self.sync_source_line()
        self.enable_buttons(self.buttons)
        self.top.move_to_front(self)
        # nested event loop
        self.nesting_level += 1
        self.root.tk.call('vwait', '::idledebugwait')
        self.nesting_level -= 1
        self.frame = None

    def show_vars(self):
        _ttk = self._ttk
        if _ttk:
            self.vars.move(self.locals, '', 0)
            self.vars.move(self.globals, '', 1)
            self.vars.delete(*self.vars.get_children(self.locals))
            self.vars.delete(*self.vars.get_children(self.globals))
        else:
            self.vars.delete(0, 'end')
        self.var_values = {}
        sel = self.stack.selection() if _ttk else self.stack.curselection()
        if len(sel) == 1 and sel[0] in self.framevars:
            locals, globals, _, _ = self.framevars[sel[0]]
            # note: locals/globals may be from a remotedebugger, in
            # which case for reasons we don't need to get into here,
            # they aren't iterable
            self.add_varheader()
            for name in sorted(locals.keys(), key=underscore_at_end):
                self.add_var(name, locals[name])
            self.add_varheader(isGlobal=True)
            for name in sorted(globals.keys(), key=underscore_at_end):
                self.add_var(name, globals[name], isGlobal=True)

    def add_varheader(self, isGlobal=False):
        if not self._ttk:
            self.vars.insert('end', 'Globals:' if isGlobal else 'Locals:')
            
    def add_var(self, varname, value, isGlobal=False):
        if self._ttk:
            item = self.vars.insert(self.globals if isGlobal else self.locals,
                             'end', text=varname, values=(value, ))
        else:
            self.vars.insert('end', '   ' + varname + ':   ' + str(value))
            item = self.vars.index('end') - 1
        self.var_values[item] = value

    def mouse_moved_vars(self, ev):
        ui.tooltip_schedule(ev, self.var_tooltip)

    def leave_vars(self, ev):
        ui.tooltip_clear()

    def var_tooltip(self, ev):
        # Callback from tooltip package to return text of tooltip
        item = None
        if self._ttk:
            if self.vars.identify('column', ev.x, ev.y) == '#1':
                item = self.vars.identify('item', ev.x, ev.y)
        else:
            item = self.vars.nearest(ev.y)
        if item and item in self.var_values:
            return(self.var_values[item], ev.x + self.vars.winfo_rootx() + 10,
                                          ev.y + self.vars.winfo_rooty() + 5)
        return None

    def short_title(self):
        return "Debug Control"

    def sync_source_line(self):
        frame = self.frame
        if not frame:
            return
        filename, lineno = self.__frame2fileline(frame)
        if filename[:1] + filename[-1:] != "<>" and os.path.exists(filename):
            if self.var_open_source_windows.get() or\
                                    self.flist.already_open(filename):
                self.flist.gotofileline(filename, lineno)

    def __frame2fileline(self, frame):
        code = frame.f_code
        filename = code.co_filename
        lineno = frame.f_lineno
        return filename, lineno

    def invoke_program(self):
        "Called just before taking the next action in debugger, adjust state"
        self.enable_buttons(['stop'])
        self.show_status('Running...')

    def cont(self, ev=None):
        self.invoke_program()
        self.idb.set_continue()
        self.abort_loop()

    def step(self, ev=None):
        self.invoke_program()
        self.idb.set_step()
        self.abort_loop()

    def next(self, ev=None):
        self.invoke_program()
        self.idb.set_next(self.frame)
        self.abort_loop()

    def ret(self, ev=None):
        self.invoke_program()
        self.idb.set_return(self.frame)
        self.abort_loop()

    def quit(self, ev=None):
        if self.running:
            self.pyshell.interp.restart_subprocess()
        else:
            self.invoke_program()
            self.idb.set_quit()
        self.abort_loop()
            
    def abort_loop(self):
        self.root.tk.call('set', '::idledebugwait', '1')        

    def options(self, ev=None):
        menu = Menu(self.top.w, tearoff=0)
        menu.add_checkbutton(label='Show Source in Open Files Only',
                variable=self.var_open_source_windows, onvalue=False)
        menu.add_checkbutton(label='Automatically Open Files to Show Source',
                variable=self.var_open_source_windows, onvalue=True)
        menu.tk_popup(ev.x_root, ev.y_root)

    def set_breakpoint_here(self, filename, lineno):
        self.idb.set_break(filename, lineno)

    def clear_breakpoint_here(self, filename, lineno):
        self.idb.clear_break(filename, lineno)

    def clear_file_breaks(self, filename):
        self.idb.clear_all_file_breaks(filename)

    def load_breakpoints(self):
        "Load PyShellEditorWindow breakpoints into subprocess debugger"
        self.flist.apply_breakpoints(self.set_breakpoint_here)
