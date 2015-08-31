import os
from tkinter import *
from tkinter import ttk
from tkinter.font import Font


class DebugPanel(ttk.Frame):
    def __init__(self, parent, flist=None):
        ttk.Frame.__init__(self, parent)
        self['width'] = 200
        self['height'] = 200
        
        # outermost paned window
        self.pane = ttk.PanedWindow(self, orient='vertical')
        self.pane.grid(column=0, row=0, sticky='nwes')
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # top pane is debugger area
        self.debug = DebugTools(self.pane)
        self.debug.grid(column=0, row=0, sticky='nwes')
        self.debug.grid_columnconfigure(0, weight=1)
        self.debug.grid_rowconfigure(0, weight=1)
        self.pane.add(self.debug)
        
        # bottom pane is shell area
        self.shell = ShellPanel(self.pane, flist=flist)
        self.shell.grid(column=0, row=0, sticky='nwes')
        self.shell.grid_columnconfigure(0, weight=1)
        self.shell.grid_rowconfigure(0, weight=1)
        self.pane.add(self.shell)
        
        
class ShellPanel(ttk.Frame):
    def __init__(self, parent, flist=None):
        ttk.Frame.__init__(self, parent, padding=5)
        
        self.text = None
        if flist is not None and flist.pyshell is not None and flist.pyshell.text is not None:
            dummy = Text(self)
            oldpath = dummy._w
            newname='textpeer' # for now
            newpath = self._w + '.' + newname
            flist.pyshell.text.peer_create(newpath)
            del(self.children[dummy._name])
            dummy._name = newname
            dummy._w = self._w + '.' + newname
            self.children[newname] = dummy
            self.text = dummy
            self.tk.call('destroy', oldpath)
        if self.text is None:
            self.text = Text(self)
        self.text['height'] = 5
        self.text['highlightthickness'] = 0
        
        
#        self.text = Text(self, height=5, highlightthickness=0)
        scroll = ttk.Scrollbar(self, command=self.text.yview)
        self.text['yscrollcommand'] = scroll.set
        self.text.grid(column=0, row=0, sticky='nwes')
        scroll.grid(column=1, row=0, sticky='nwes')
        self.grid_columnconfigure(0, weight=1)
        
                
        
        
        self.grid_rowconfigure(0, weight=1)
 #       self.text.insert(END, 'Python 3.6.0a0 (default:74fc1af57c72+, Jul 31 2015, 16:41:41)\n[GCC 4.2.1 Compatible Apple LLVM 6.1.0 (clang-602.0.53)] on darwin\nType "copyright", "credits" or "license()" for more information.\n>>>\n[DEBUG ON]\n>>>\n===== RUN /Users/roseman/vboxshare/cpython/Lib/idlelib/uipreferences.py =====')



class DebugTools(ttk.Frame):
    def __init__(self, parent):
        ttk.Frame.__init__(self, parent)
        self.pane = ttk.PanedWindow(self, orient='horizontal')
        self.pane.grid(column=0, row=0, sticky='nwes')
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        left = ttk.Frame(self.pane, padding=5)
        self.pane.add(left)
        controls = ttk.Frame(left)
        f = Font(name='TkSmallCaptionFont', exists=True, root=self._root())
        
        fn = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                              "Icons", "debug_go.gif")
        self.goimg = PhotoImage(master=self._root(), file=fn)
        fn = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                              "Icons", "debug_step.gif")
        self.stepimg = PhotoImage(master=self._root(), file=fn)
        fn = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                              "Icons", "debug_over.gif")
        self.overimg = PhotoImage(master=self._root(), file=fn)
        fn = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                              "Icons", "debug_out.gif")
        self.outimg = PhotoImage(master=self._root(), file=fn)
        fn = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                              "Icons", "debug_stop.gif")
        self.stopimg = PhotoImage(master=self._root(), file=fn)
        
        
        go = ttk.Label(controls, image=self.goimg, text='Go', compound='top', font=f)
        step = ttk.Label(controls, image=self.stepimg, text='Step', compound='top', font=f)
        over = ttk.Label(controls, image=self.overimg, text='Over', compound='top', font=f)
        out = ttk.Label(controls, image=self.outimg, text='Out', compound='top', font=f)
        stop = ttk.Label(controls, image=self.stopimg, text='Stop', compound='top', font=f)

        go.grid(column=0, row=0, padx=[0,5])
        step.grid(column=1, row=0, padx=[0,5])
        over.grid(column=2, row=0, padx=[0,5])
        out.grid(column=3, row=0, padx=[0,5])
        stop.grid(column=4, row=0, padx=[0,5])
        
        self.status = ttk.Label(controls, text='Program stopped by exception.', foreground='#ff0000', font=('helvetica', 13, 'italic'))
        self.status.grid(column=5, row=0, padx=[50,0])
        
        controls.grid(column=0, row=0, sticky='nw', pady=[0,6])
        #self.stack = Text(left, height=5, highlightthickness=0)
        #self.stack.insert(END, "__init__ [uipreferences.py:163]\nadd_panes [uipreferences.py:180]\n__init__ [uipreferences.py:424]\nrebuild_themes_list [uipreferences.py:433]\ntheme_changed [uipreferences.py:443]\nupdate_colors [uipreferences.py:477]")
        
        self.stack = ttk.Treeview(left, columns=('location', 'statement'), displaycolumns=('statement',), height=5)
        self.stack.insert('', 'end', text='__init__', values=('[__main__:163]', 'self.add_panes(tabs)'))
        self.stack.insert('', 'end', text='add_panes', values=('[__main__.py:180]', "self.add_pane(ThemesPane(parent, self), 'Themes')"))
        self.stack.insert('', 'end', text='__init__', values=('[__main__.py:424]', "self.rebuild_themes_list()"))
        self.stack.insert('', 'end', text='rebuild_themes_list', values=('[__main__.py:433]', "self.theme_changed()"))
        self.stack.insert('', 'end', text='theme_changed()', values=('[__main__.py:443]', "self.update_colors()"))
        self.stack.insert('', 'end', text='update_colors()', values=('[__main__.py:477]', "x = 5/0"))
        self.stack.insert('', 'end', text='ZeroDivisionError:', values=('', "division by zero"), tags=('error',))
        self.stack.tag_configure('error', foreground='red')
        
        
        scroll = ttk.Scrollbar(left, command=self.stack.yview)
        self.stack['yscrollcommand'] = scroll.set
        self.stack.grid(column=0, row=1, sticky='nwes')
        scroll.grid(column=1, row=1, sticky='ns')
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=1)
        
        right = ttk.Frame(self.pane, padding=5)
        self.pane.add(right)
        tree = ttk.Treeview(right, columns=('value',), height=5)
        locals = tree.insert('', 'end', text='Locals')
        globals = tree.insert('', 'end', text='Globals')
        tree.insert(locals, 'end', text='bg', values=("'#ffffff'",))
        tree.insert(locals, 'end', text='element', values=("'Shell Normal Text'", ))
        tree.insert(locals, 'end', text='elt', values=("'console'",))
        tree.insert(locals, 'end', text='fg', values=("'#770000'",))
        tree.insert(locals, 'end', text='self', values="<__main__.ThemesPane object...28896.4437729008.4437729232>")
        tree.insert(locals, 'end', text='theme', values=("'IDLE Classic'",))
        tree.insert(globals, 'end', text='One',)
        tree.insert(globals, 'end', text='Two',)
        tree.insert(globals, 'end', text='Three',)
        tree.grid(column=0, row=0, sticky='nwes')
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=1)

        
        
if __name__ == '__main__':
    root = Tk()
    f = ttk.Frame(root)
    f.grid(column=0, row=0, sticky='nwes')
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(0, weight=1)
    dbg = DebugPanel(parent=root)
    dbg.grid(column=0, row=0, sticky='nwes')
    f.grid_columnconfigure(0, weight=1)
    f.grid_rowconfigure(0, weight=1)
    root.mainloop()

