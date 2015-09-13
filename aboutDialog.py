"""About Dialog for IDLE

"""

import os
from sys import version
from tkinter import *


dlg = None

def show(parent):
    "Main routine; show dialog window, creating or raising as necessary."
    global dlg
    if dlg is None:
        dlg = AboutDialog(parent, destroy_callback=_destroyed)
    dlg.lift()
    dlg.focus_set()

def _destroyed():
    global dlg
    dlg = None


class AboutDialog(Toplevel):
    """About dialog for IDLE """
    def __init__(self, parent, title='About IDLE', _htest=False,
                 destroy_callback=None):
        """
        _htest - bool, change box location when running htest
        """
        Toplevel.__init__(self, parent)
        self.destroy_callback = destroy_callback
        self.configure(borderwidth=5)
        # place dialog below parent if running htest
        self.geometry("+%d+%d" % (
                        parent.winfo_rootx()+30,
                        parent.winfo_rooty()+(30 if not _htest else 100)))
        self.bg = "#bbbbbb"
        self.fg = "#000000"
        self.link_cursor = 'hand2'  # TODO use ui.clickable_cursor
        self.CreateWidgets()
        self.resizable(height=FALSE, width=FALSE)
        self.title(title)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.parent = parent
        self.bind('<Escape>', self.close)   # dismiss dialog

    def CreateWidgets(self):
        self['borderwidth'] = 0
        release = version[:version.index(' ')]
        logofn = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                              "Icons", "idle_48.gif")
        self.picture = PhotoImage(master=self._root(), file=logofn)
        self.frameBg = frameBg = Frame(self, bg=self.bg, borderwidth=0)
        frameBg.grid(sticky='nsew')
        labelTitle = Label(frameBg, text='IDLE', fg=self.fg, bg=self.bg,
                           font=('courier', 24, 'bold'))
        labelTitle.grid(row=0, column=1, sticky=W, padx=10, pady=[10,0])
        labelPicture = Label(frameBg, image=self.picture, bg=self.bg)
        labelPicture.grid(row=0, column=0, sticky=NE, rowspan=2,
                          padx=10, pady=10)
        byline = "Python's Integrated DeveLopment Environment"
        labelDesc = Label(frameBg, text=byline, justify=LEFT,
                          fg=self.fg, bg=self.bg)
        labelDesc.grid(row=1, column=1, sticky=W, columnspan=3, padx=10,
                       pady=[0,20])
        labelEmail = Label(frameBg, text='email:  idle-dev@python.org',
                           justify=LEFT, fg=self.fg, bg=self.bg)
        labelEmail.grid(row=6, column=1, columnspan=2,
                        sticky=W, padx=10, pady=0)
        labelWWW = Label(frameBg, text='https://docs.python.org/' +
                         version[:3] + '/library/idle.html',
                         justify=LEFT, fg=self.fg, bg=self.bg)
        labelWWW.grid(row=7, column=1, columnspan=2, sticky=W, padx=10, pady=0)
        tkVer = self.tk.call('info', 'patchlevel')
        labelVersion = Label(frameBg, text='Python ' +
                             release + '     (with Tk '+tkVer+')',
                             fg=self.fg, bg=self.bg)
        labelVersion.grid(row=4, column=1, sticky=W, padx=10, pady=[0,5])
        self.morelink = Label(frameBg, text='More...', fg='blue', bg=self.bg,
                              cursor=self.link_cursor)
        self.morelink.grid(column=0, columnspan=3, pady=10, padx=10, sticky=E)
        self.morelink.bind('<1>', self.showMore)

    def showMore(self, ev=None):
        self.morelink.grid_forget()
        fmore = Frame(self.frameBg, borderwidth=2, relief='ridge', bg='white')
        fmore.grid_columnconfigure(0, weight=1)
        self.t = Text(fmore, height=15, width=80, borderwidth=0,
                      highlightthickness=0, state='disabled', bg='white')
        s = Scrollbar(fmore, command=self.t.yview)
        self.t['yscrollcommand'] = s.set
        self.load_moreinfo()
        self.which = StringVar(self)
        self.which.set(self.info[0][0])
        self.which.trace_variable('w', self.changeInfo)
        fmore.grid(column=0, row=20, sticky='nwes', padx=5, pady=[15,5],
                   columnspan=4)
        l = []
        for k, t in self.info:
            l.append(k)
        wh = OptionMenu(fmore, self.which, *l)
        wh.grid(column=0, row=0, pady=[2,10])
        self.t.grid(column=0, row=1)
        s.grid(column=1, row=0, sticky='ns', rowspan=2)
        self.changeInfo()

    def changeInfo(self, *params):
        for key, txt in self.info:
            if key == self.which.get():
                self.t['state'] = 'normal'
                self.t.delete('1.0', 'end')
                self.t.insert('1.0', txt)
                self.t['state'] = 'disabled'

    def load_moreinfo(self):
        self.info = []
        self.load_from_file('IDLE Readme', 'README.txt')
        self.load_from_file('IDLE News', 'NEWS.txt')
        self.load_from_file('IDLE Credits', 'CREDITS.txt', 'iso-8859-1')
        self.load_from_printer('Python License', license)
        self.load_from_printer('Python Copyright', copyright)
        self.load_from_printer('Python Credits', credits)

    def load_from_file(self, key, filename, encoding=None):
        fn = os.path.join(os.path.abspath(os.path.dirname(__file__)), filename)
        try:
            with open(fn, 'r', encoding=encoding) as file:
                contents = file.read()
        except IOError:
            pass
        else:
            self.info.append((key, contents))

    def load_from_printer(self, key, printercmd):
        printercmd._Printer__setup()
        self.info.append((key, '\n'.join(printercmd._Printer__lines)))

    def close(self, event=None):
        if self.destroy_callback:
            self.destroy_callback()
        self.destroy()

if __name__ == '__main__':
    from idlelib.idle_test.htest import run
    run(AboutDialog)
