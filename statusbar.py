"""
Status bar knows how to display status for IDLE components

For now, just knows about a single editor/shell component, but will likely
expand over time...
"""

from tkinter import *
from tkinter import ttk
from idlelib import uifactory

class Statusbar(Frame):

    def __init__(self, master):
        cls = ttk.Frame
        cls.__init__(self, master)
        self.labels = {}
        self.component = None
        sep = ttk.Separator(self, orient=HORIZONTAL)
        sep.pack(side=TOP, fill=X)
        self.set_label('column', 'Col: ?', side=RIGHT, width=7)
        self.set_label('line', 'Ln: ?', side=RIGHT, width=7)
        
    def observe(self, component):
        self.component = component  # for now, must be editor/shell
        self.after_idle(self.update)
        
    def update(self):
        line, column = self.component.text.index(INSERT).split('.')
        self.set_label('column', 'Col: %s' % column)
        self.set_label('line', 'Ln: %s' % line)

    def set_label(self, name, text='', side=LEFT, width=0):
        if name not in self.labels:
            cls = ttk.Label
            label = cls(self)
            label.pack(side=side, pady=0, padx=4)
            self.labels[name] = label
        else:
            label = self.labels[name]
        if width != 0: 
            label.config(width=width)
        label.config(text=text)
