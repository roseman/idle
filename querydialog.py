from tkinter import *
from tkinter.font import Font
from tkinter import ttk


def askinteger(**kw):
    if 'min' in kw:
        min = kw['min']
        del kw['min']
    else:
        min = None
    if 'max' in kw:
        max = kw['max']
        del kw['max']
    else:
        max = None
    kw['validatecmd'] = lambda s:validate_int(s, min=min, max=max)
    d = QueryDialog(**kw)
    return int(d.result) if d.result is not None else None


def askstring(**kw):
    d = QueryDialog(**kw)
    return d.result


class QueryDialog(Toplevel):

    def __init__(self, prompt=None, title=None, parent=None, 
                 initialvalue=None, validatecmd=None, oklabel=None,
                 use_ttk=True):
        Toplevel.__init__(self, parent)
        self.parent = parent
        self.validatecmd = validatecmd
        self.result = None
        self.wm_withdraw()
        if parent is not None and parent.winfo_viewable():
            self.wm_transient(parent)
        windowingsystem = self.tk.call('tk', 'windowingsystem')
        if windowingsystem == 'aqua':
            try:
                self.tk.call('::tk::unsupported::MacWindowStyle', 'style',
                             self._w, 'moveableModal', '')
            except:
                pass
        if title is not None:
            self.title(title)
        if use_ttk:
            frm = ttk.Frame(self, padding=10)
        else:
            frm = Frame(self, padx=10, pady=10)
        frm.grid(column=0, row=0, sticky='news')
        frm.grid_columnconfigure(0, weight=1)

        if prompt is not None:
            if use_ttk:
                w = ttk.Label(frm, text=prompt, justify=LEFT)
            else:
                w = Label(frm, text=prompt, justify=LEFT)
            w.grid(column=0, row=0, columnspan=3, padx=5, sticky=W)

        if use_ttk:
            self.entry = ttk.Entry(frm, width=30)
        else:
            self.entry = Entry(frm, width=30)
        self.entry.grid(column=0, row=1, columnspan=3, padx=5, sticky=W+E,
                        pady=[10,0])
        if initialvalue is not None:
            self.entry.insert(0, initialvalue)
            self.entry.select_range(0, END)
        self.entry.bind('<KeyPress>', self._clearerrmsg)
        if use_ttk:
            self.errmsg = ttk.Label(frm, text=' ', foreground='red',
                                    font=Font(name='TkCaptionFont',
                                              exists=True, root=parent))
        else:
            self.errmsg = Label(frm, text=' ', foreground='red')
        self.errmsg.grid(column=0, row=2, columnspan=3, padx=5, sticky=W+E)

        if oklabel is None:
            oklabel = 'OK'
        if use_ttk:
            w = ttk.Button(frm, text=oklabel, command=self._ok, default=ACTIVE)
        else:
            w = Button(frm, text=oklabel, command=self._ok, default=ACTIVE)
        w.grid(column=1, row=99, padx=5)
        if use_ttk:
            w = ttk.Button(frm, text="Cancel", command=self._cancel)
        else:
            w = Button(frm, text="Cancel", command=self._cancel)
        w.grid(column=2, row=99, padx=5)
        self.bind("<Return>", self._ok)
        self.bind("<Escape>", self._cancel)
        if windowingsystem == 'aqua':
            self.bind("<KP_Enter>", self._ok)
            self.bind("<Command-.>", self._cancel)

        if parent is not None:
            self.geometry("+%d+%d" % (parent.winfo_rootx()+50,
                                      parent.winfo_rooty()+50))
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.update_idletasks()
        self.wm_resizable(False, False)
        self.wm_deiconify()
        self.entry.focus_set()
        self.wait_visibility()
        self.grab_set()
        self.wait_window(self)

    def _clearerrmsg(self, event=None):
        self.errmsg['text'] = ' '

    def _ok(self, event=None):
        s = self.entry.get().strip()
        errmsg = self.get_validation_error(s)
        if errmsg is not None:
            self.errmsg['text'] = errmsg
            self.entry.focus_set()  # put focus back
            return
        self.result = s
        self.withdraw()
        self.update_idletasks()
        self.destroy()

    def _cancel(self, event=None):
        self.destroy()

    def destroy(self):
        if self.parent is not None:
            self.parent.focus_set()
        Toplevel.destroy(self)

    def get_validation_error(self, s):
        if self.validatecmd is not None:
            try:
                self.validatecmd(s)
            except ValueError as e:
                return e.args[0]
        return None


def validate_int(s, min=None, max=None):
    try:
        v = int(s)
    except ValueError:
        raise ValueError("Must be an integer")
    if min is not None and max is not None:
        if v < min or v > max:
            raise ValueError("Must be between " + str(min) +
                             " and " + str(max))
    if min is not None and v < min:
        raise ValueError("Must be at least "+str(min))
    if max is not None and v > max:
        raise ValueError("Must be no larger than "+str(max))



if __name__ == '__main__':

    root = Tk()
    val = askinteger(parent=root, prompt='Number', title='Gimme', min=5, max=9)
    print(str(val))
