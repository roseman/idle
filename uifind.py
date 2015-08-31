from tkinter import *
from tkinter import ttk
from idlelib import SearchEngine
import re
import os
import fnmatch
import sys

class SearchDialogBase:
    '''Create most of a 3 or 4 row, 3 column search dialog.

    The left and wide middle column contain:
    1 or 2 labeled text entry lines (make_entry, create_entries);
    a row of standard Checkbuttons (make_frame, create_option_buttons),
    each of which corresponds to a search engine Variable;
    a row of dialog-specific Check/Radiobuttons (create_other_buttons).

    The narrow right column contains command buttons
    (make_button, create_command_buttons).
    These are bound to functions that execute the command.

    Except for command buttons, this base class is not limited to items
    common to all three subclasses.  Rather, it is the Find dialog minus
    the "Find Next" command, its execution function, and the
    default_command attribute needed in create_widgets. The other
    dialogs override attributes and methods, the latter to replace and
    add widgets.
    '''

    title = "Search Dialog"  # replace in subclasses
    icon = "Search"
    needwrapbutton = 1  # not in Find in Files

    def __init__(self, root, engine):
        '''Initialize root, engine, and top attributes.

        top (level widget): set in create_widgets() called from open().
        text (Text searched): set in open(), only used in subclasses().
        ent (ry): created in make_entry() called from create_entry().
        row (of grid): 0 in create_widgets(), +1 in make_entry/frame().
        default_command: set in subclasses, used in create_widgers().

        title (of dialog): class attribute, override in subclasses.
        icon (of dialog): ditto, use unclear if cannot minimize dialog.
        '''
        self.root = root
        self.engine = engine
        self.top = None

    def open(self, text, searchphrase=None):
        "Make dialog visible on top of others and ready to use."
        self.text = text
        if not self.top:
            self.create_widgets()
        else:
            self.top.deiconify()
            self.top.tkraise()
        if searchphrase:
            self.ent.delete(0,"end")
            self.ent.insert("end",searchphrase)
        self.ent.focus_set()
        self.ent.selection_range(0, "end")
        self.ent.icursor(0)
        self.top.grab_set()

    def close(self, event=None):
        "Put dialog away for later use."
        if self.top:
            self.top.grab_release()
            self.top.withdraw()

    def create_widgets(self):
        '''Create basic 3 row x 3 col search (find) dialog.

        Other dialogs override subsidiary create_x methods as needed.
        Replace and Find-in-Files add another entry row.
        '''
        top = Toplevel(self.root)
        top.bind("<Return>", self.default_command)
        top.bind("<Escape>", self.close)
        if sys.platform == 'darwin':
            top.bind("<KP_Enter>", self.default_command)
            top.bind("<Command-.>", self.close)
        
        top.protocol("WM_DELETE_WINDOW", self.close)
        top.wm_title(self.title)
        top.wm_iconname(self.icon)
        self.top = top
        self.inner = ttk.Frame(top, padding=10)
        self.inner.grid(column=0, row=0, sticky='nwes')

        self.row = 0
        self.inner.grid_columnconfigure(0, pad=2, weight=0)
        self.inner.grid_columnconfigure(1, pad=2, minsize=100, weight=100)

        self.create_entries()  # row 0 (and maybe 1), cols 0, 1
        self.create_option_buttons()  # next row, cols 0, 1
        #self.create_other_buttons()  # next row, cols 0, 1
        self.create_command_buttons()  # col 2, all rows

    def make_entry(self, label_text, var):
        '''Return (entry, label), .

        entry - gridded labeled Entry for text entry.
        label - Label widget, returned for testing.
        '''
        label = ttk.Label(self.inner, text=label_text)
        label.grid(row=self.row, column=0, sticky="nw")
        entry = ttk.Entry(self.inner, textvariable=var, exportselection=0)
        entry.grid(row=self.row, column=1, sticky="nwe", pady=[0,5])
        self.row = self.row + 1
        return entry, label

    def create_entries(self):
        "Create one or more entry lines with make_entry."
        self.ent = self.make_entry("Find:", self.engine.patvar)[0]

    def make_frame(self,labeltext=None):
        '''Return (frame, label).

        frame - gridded labeled Frame for option or other buttons.
        label - Label widget, returned for testing.
        '''
        if labeltext:
            label = ttk.Label(self.inner, text=labeltext)
            label.grid(row=self.row, column=0, sticky="w")
        else:
            label = ''
        frame = ttk.Frame(self.inner)
        frame.grid(row=self.row, column=1, columnspan=1, sticky="nwe")
        self.row = self.row + 1
        return frame, label

    def create_option_buttons(self):
        '''Return (filled frame, options) for testing.

        Options is a list of SearchEngine booleanvar, label pairs.
        A gridded frame from make_frame is filled with a Checkbutton
        for each pair, bound to the var, with the corresponding label.
        '''
        frame = self.make_frame("Options:")[0]
        engine = self.engine
        options = [(engine.revar, "Regular expression"),
                   (engine.casevar, "Match case"),
                   (engine.wordvar, "Whole word")]
        if self.needwrapbutton:
            options.append((engine.wrapvar, "Wrap around"))
        for var, label in options:
            btn = ttk.Checkbutton(frame, variable=var, text=label)
            btn.pack(side="left", fill="both")
        return frame, options

    def create_other_buttons(self):
        '''Return (frame, others) for testing.

        Others is a list of value, label pairs.
        A gridded frame from make_frame is filled with radio buttons.
        '''
        frame = self.make_frame("Direction:")[0]
        var = self.engine.backvar
        others = [(1, 'Up'), (0, 'Down')]
        for val, label in others:
            btn = ttk.Radiobutton(frame, variable=var, value=val, text=label)
            btn.pack(side="left", fill="both")
        return frame, others

    def make_button(self, label, command, isdef=0, gap=0):
        "Return command button gridded in command frame."
        b = ttk.Button(self.buttonframe,
                   text=label, command=command,
                   default=isdef and "active" or "normal")
        cols,rows=self.buttonframe.grid_size()
        b.grid(column=cols, row=0, padx=[30,2] if gap else 2)
        self.buttonframe.grid(rowspan=rows+1)
        return b

    def create_command_buttons(self):
        "Place buttons in vertical command frame gridded on right."
        f = self.buttonframe = ttk.Frame(self.inner)
        f.grid(row=99, column=0, columnspan=2, sticky='e', pady=[20,0])
        #b = self.make_button("Close", self.close)
        #b.lower()

############################## FIND ##############################


def _setup(text):
    root = text._root()
    engine = SearchEngine.get(root)
    if not hasattr(engine, "_searchdialog"):
        engine._searchdialog = SearchDialog(root, engine)
    return engine._searchdialog

def find(text):
    pat = text.get("sel.first", "sel.last")
    return _setup(text).open(text,pat)

def find_again(text):
    return _setup(text).find_again(text)

def find_selection(text):
    return _setup(text).find_selection(text)

class SearchDialog(SearchDialogBase):

    def create_widgets(self):
        SearchDialogBase.create_widgets(self)
        self.make_button("Find Next", self.default_command, 1)

    def default_command(self, event=None):
        if not self.engine.getprog():
            return
        self.find_again(self.text)

    def find_again(self, text):
        if not self.engine.getpat():
            self.open(text)
            return False
        if not self.engine.getprog():
            return False
        res = self.engine.search_text(text)
        if res:
            line, m = res
            i, j = m.span()
            first = "%d.%d" % (line, i)
            last = "%d.%d" % (line, j)
            try:
                selfirst = text.index("sel.first")
                sellast = text.index("sel.last")
                if selfirst == first and sellast == last:
                    text.bell()
                    return False
            except TclError:
                pass
            text.tag_remove("sel", "1.0", "end")
            text.tag_add("sel", first, last)
            text.mark_set("insert", self.engine.isback() and first or last)
            text.see("insert")
            return True
        else:
            text.bell()
            return False

    def find_selection(self, text):
        pat = text.get("sel.first", "sel.last")
        if pat:
            self.engine.setcookedpat(pat)
        return self.find_again(text)


############################## REPLACE ##############################

def replace(text):
    root = text._root()
    engine = SearchEngine.get(root)
    if not hasattr(engine, "_replacedialog"):
        engine._replacedialog = ReplaceDialog(root, engine)
    dialog = engine._replacedialog
    dialog.open(text)


class ReplaceDialog(SearchDialogBase):

    title = "Find"
    icon = "Find"

    def __init__(self, root, engine):
        SearchDialogBase.__init__(self, root, engine)
        self.replvar = StringVar(root)

    def open(self, text):
        SearchDialogBase.open(self, text)
        try:
            first = text.index("sel.first")
        except TclError:
            first = None
        try:
            last = text.index("sel.last")
        except TclError:
            last = None
        first = first or text.index("insert")
        last = last or first
        self.show_hit(first, last)
        self.ok = 1

    def create_entries(self):
        SearchDialogBase.create_entries(self)
        self.replent = self.make_entry("Replace:", self.replvar)[0]

    def create_command_buttons(self):
        SearchDialogBase.create_command_buttons(self)
        self.make_button("Replace All", self.replace_all)
        self.make_button("Replace", self.replace_it)
        self.make_button("Replace & Find", self.default_command)
        self.make_button("Previous", self.do_previous, gap=1)
        self.make_button("Next", self.do_next, 1)

    def do_next(self, event=None):
        self.find_it()
        
    def do_previous(self, event=None):
        self.find_it()
        
    def find_it(self, event=None):
        self.do_find(0)

    def replace_it(self, event=None):
        if self.do_find(self.ok):
            self.do_replace()

    def default_command(self, event=None):
        if self.do_find(self.ok):
            if self.do_replace():   # Only find next match if replace succeeded.
                                    # A bad re can cause a it to fail.
                self.do_find(0)

    def _replace_expand(self, m, repl):
        """ Helper function for expanding a regular expression
            in the replace field, if needed. """
        if self.engine.isre():
            try:
                new = m.expand(repl)
            except re.error:
                self.engine.report_error(repl, 'Invalid Replace Expression')
                new = None
        else:
            new = repl

        return new

    def replace_all(self, event=None):
        prog = self.engine.getprog()
        if not prog:
            return
        repl = self.replvar.get()
        text = self.text
        res = self.engine.search_text(text, prog)
        if not res:
            text.bell()
            return
        text.tag_remove("sel", "1.0", "end")
        text.tag_remove("hit", "1.0", "end")
        line = res[0]
        col = res[1].start()
        if self.engine.iswrap():
            line = 1
            col = 0
        ok = 1
        first = last = None
        # XXX ought to replace circular instead of top-to-bottom when wrapping
        text.undo_block_start()
        while 1:
            res = self.engine.search_forward(text, prog, line, col, 0, ok)
            if not res:
                break
            line, m = res
            chars = text.get("%d.0" % line, "%d.0" % (line+1))
            orig = m.group()
            new = self._replace_expand(m, repl)
            if new is None:
                break
            i, j = m.span()
            first = "%d.%d" % (line, i)
            last = "%d.%d" % (line, j)
            if new == orig:
                text.mark_set("insert", last)
            else:
                text.mark_set("insert", first)
                if first != last:
                    text.delete(first, last)
                if new:
                    text.insert(first, new)
            col = i + len(new)
            ok = 0
        text.undo_block_stop()
        if first and last:
            self.show_hit(first, last)
        self.close()

    def do_find(self, ok=0):
        if not self.engine.getprog():
            return False
        text = self.text
        res = self.engine.search_text(text, None, ok)
        if not res:
            text.bell()
            return False
        line, m = res
        i, j = m.span()
        first = "%d.%d" % (line, i)
        last = "%d.%d" % (line, j)
        self.show_hit(first, last)
        self.ok = 1
        return True

    def do_replace(self):
        prog = self.engine.getprog()
        if not prog:
            return False
        text = self.text
        try:
            first = pos = text.index("sel.first")
            last = text.index("sel.last")
        except TclError:
            pos = None
        if not pos:
            first = last = pos = text.index("insert")
        line, col = SearchEngine.get_line_col(pos)
        chars = text.get("%d.0" % line, "%d.0" % (line+1))
        m = prog.match(chars, col)
        if not prog:
            return False
        new = self._replace_expand(m, self.replvar.get())
        if new is None:
            return False
        text.mark_set("insert", first)
        text.undo_block_start()
        if m.group():
            text.delete(first, last)
        if new:
            text.insert(first, new)
        text.undo_block_stop()
        self.show_hit(first, text.index("insert"))
        self.ok = 0
        return True

    def show_hit(self, first, last):
        text = self.text
        text.mark_set("insert", first)
        text.tag_remove("sel", "1.0", "end")
        text.tag_add("sel", first, last)
        text.tag_remove("hit", "1.0", "end")
        if first == last:
            text.tag_add("hit", first)
        else:
            text.tag_add("hit", first, last)
        text.see("insert")
        text.update_idletasks()

    def close(self, event=None):
        SearchDialogBase.close(self, event)
        self.text.tag_remove("hit", "1.0", "end")

############################## GREP ##############################

# Importing OutputWindow fails due to import loop
# EditorWindow -> GrepDialop -> OutputWindow -> EditorWindow

def grep(text, io=None, flist=None):
    root = text._root()
    engine = SearchEngine.get(root)
    if not hasattr(engine, "_grepdialog"):
        engine._grepdialog = GrepDialog(root, engine, flist)
    dialog = engine._grepdialog
    searchphrase = text.get("sel.first", "sel.last")
    dialog.open(text, searchphrase, io)

class GrepDialog(SearchDialogBase):

    title = "Find in Files Dialog"
    icon = "Grep"
    needwrapbutton = 0

    def __init__(self, root, engine, flist):
        SearchDialogBase.__init__(self, root, engine)
        self.flist = flist
        self.globvar = StringVar(root)
        self.recvar = BooleanVar(root)

    def open(self, text, searchphrase, io=None):
        SearchDialogBase.open(self, text, searchphrase)
        if io:
            path = io.filename or ""
        else:
            path = ""
        dir, base = os.path.split(path)
        head, tail = os.path.splitext(base)
        if not tail:
            tail = ".py"
        self.globvar.set(os.path.join(dir, "*" + tail))

    def create_entries(self):
        SearchDialogBase.create_entries(self)
        self.globent = self.make_entry("In files:", self.globvar)[0]

    def create_other_buttons(self):
        f = self.make_frame()[0]

        btn = Checkbutton(f, anchor="w",
                variable=self.recvar,
                text="Recurse down subdirectories")
        btn.pack(side="top", fill="both")
        btn.select()

    def create_command_buttons(self):
        SearchDialogBase.create_command_buttons(self)
        self.make_button("Search Files", self.default_command, 1)

    def default_command(self, event=None):
        prog = self.engine.getprog()
        if not prog:
            return
        path = self.globvar.get()
        if not path:
            self.top.bell()
            return
        from idlelib.OutputWindow import OutputWindow  # leave here!
        save = sys.stdout
        try:
            sys.stdout = OutputWindow(self.flist)
            self.grep_it(prog, path)
        finally:
            sys.stdout = save

    def grep_it(self, prog, path):
        dir, base = os.path.split(path)
        list = self.findfiles(dir, base, self.recvar.get())
        list.sort()
        self.close()
        pat = self.engine.getpat()
        print("Searching %r in %s ..." % (pat, path))
        hits = 0
        try:
            for fn in list:
                try:
                    with open(fn, errors='replace') as f:
                        for lineno, line in enumerate(f, 1):
                            if line[-1:] == '\n':
                                line = line[:-1]
                            if prog.search(line):
                                sys.stdout.write("%s: %s: %s\n" %
                                                 (fn, lineno, line))
                                hits += 1
                except OSError as msg:
                    print(msg)
            print(("Hits found: %s\n"
                  "(Hint: right-click to open locations.)"
                  % hits) if hits else "No hits.")
        except AttributeError:
            # Tk window has been closed, OutputWindow.text = None,
            # so in OW.write, OW.text.insert fails.
            pass

    def findfiles(self, dir, base, rec):
        try:
            names = os.listdir(dir or os.curdir)
        except OSError as msg:
            print(msg)
            return []
        list = []
        subdirs = []
        for name in names:
            fn = os.path.join(dir, name)
            if os.path.isdir(fn):
                subdirs.append(fn)
            else:
                if fnmatch.fnmatch(name, base):
                    list.append(fn)
        if rec:
            for subdir in subdirs:
                list.extend(self.findfiles(subdir, base, rec))
        return list

    def close(self, event=None):
        if self.top:
            self.top.grab_release()
            self.top.withdraw()


#
#
# TEST CODE BELOW HERE
#
#

def _search_dialog(parent):
    root = Tk()
    root.title("Test SearchDialog")
    width, height, x, y = list(map(int, re.split('[x+]', parent.geometry())))
    root.geometry("+%d+%d"%(x, y + 150))
    text = Text(root)
    text.pack()
    text.insert("insert","This is a sample string.\n"*10)

    def show_find():
        text.tag_add(SEL, "1.0", END)
        s = _setup(text)
        s.open(text)
        text.tag_remove(SEL, "1.0", END)

    button = Button(root, text="Search", command=show_find)
    button.pack()

def _replace_dialog(parent):
    root = Tk()
    root.title("Test ReplaceDialog")
    width, height, x, y = list(map(int, re.split('[x+]', parent.geometry())))
    root.geometry("+%d+%d"%(x, y + 150))

    # mock undo delegator methods
    def undo_block_start():
        pass

    def undo_block_stop():
        pass

    text = Text(root)
    text.undo_block_start = undo_block_start
    text.undo_block_stop = undo_block_stop
    text.pack()
    text.insert("insert","This is a sample string.\n"*10)

    def show_replace():
        text.tag_add(SEL, "1.0", END)
        replace(text)
        text.tag_remove(SEL, "1.0", END)

    button = Button(root, text="Replace", command=show_replace)
    button.pack()


def _grep_dialog(parent):  # htest #
    from idlelib.PyShell import PyShellFileList
    root = Tk()
    root.title("Test GrepDialog")
    width, height, x, y = list(map(int, re.split('[x+]', parent.geometry())))
    root.geometry("+%d+%d"%(x, y + 150))

    flist = PyShellFileList(root)
    text = Text(root, height=5)
    text.pack()

    def show_grep_dialog():
        text.tag_add(SEL, "1.0", END)
        grep(text, flist=flist)
        text.tag_remove(SEL, "1.0", END)

    button = Button(root, text="Show GrepDialog", command=show_grep_dialog)
    button.pack()
    root.mainloop()

if __name__ == "__main__":
    root=Tk()
    _replace_dialog(root)
    root.mainloop()
    
