"""Define some IDLE-specific support routines on top of the more generic
   TkTestCase.
"""
from idlelib.idle_test.tktestcase import TkTestCase, requires_mac
from idlelib.EditorWindow import EditorWindow
import idlelib.uifactory


class IdleTestCase(TkTestCase):

    def open_editwindow(self):
        idlelib.uifactory.initialize(self.root)
        self.root.wm_withdraw()
        self.ed = EditorWindow(root=self.root)
        self.text = self.getWidget('text')
        self.waitForExists('toplevel', title='Untitled', viewable=1)
        self.topwin = self.getWidget('toplevel', title='Untitled')

    def close_editwindow(self):
        self.ed._close()
