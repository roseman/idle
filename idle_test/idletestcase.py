"""Define some IDLE-specific support routines on top of the more generic
   TkTestCase.
"""
from idlelib.idle_test.tktestcase import TkTestCase, requires_mac
from idlelib.FileList import FileList


class IdleTestCase(TkTestCase):

    def open_editwindow(self):
        self.root.wm_withdraw()
        self.flist = FileList(self.root)
        self.ed = self.flist.new()
        self.text = self.getWidget('text')
        self.waitForExists('toplevel', title='Untitled', viewable=1)
        self.topwin = self.getWidget('toplevel', title='Untitled')

    def close_editwindow(self):
        self.ed._close()
