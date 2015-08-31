import unittest
from test.support import requires, ResourceDenied
from tkinter import Tk
from idlelib.macosxSupport import _initializeTkVariantTests
import re
import sys


class TkTestCase(unittest.TestCase):
    """
    Helpers for functional testing of Tkinter applications
    """
    @classmethod
    def setUpClass(cls):
        requires('gui')
        cls.root = Tk()
        _initializeTkVariantTests(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()
        del cls.root

    @classmethod    
    def main(cls, **kwargs):
        unittest.main(**kwargs)
        
    def allwidgets(self):
        return self._allwidgets(self.root)

    def _allwidgets(self, parent):
        wlist = [parent]
        for w in parent.winfo_children():
            wlist += self._allwidgets(w)
        return wlist

    def _widgetMatches(self, w, widgetclass, matchopts):
        wtype = self._widgetType(w)
        if (wtype != '*' and wtype != widgetclass):
            return False
        for k, val in matchopts.items():
            if (wtype == "toplevel" and k == "title"):
                actual = w.wm_title()
            elif k == 'viewable':
                actual = w.winfo_viewable()
            elif k == 'toplevel':
                actual = w.winfo_toplevel().wm_title()
            else:
                actual = w.cget(k)
            if (actual != val):
                return False
        return True

    def getWidget(self, widgetclass, **kwargs):
        for w in self.allwidgets():
            if (self._widgetMatches(w, widgetclass, kwargs)):
                return w
        return None

    def assertExists(self, widgetclass, **kwargs):
        if self.getWidget(widgetclass, **kwargs):
            return
        raise AssertionError("widget not found")

    def assertNotExists(self, widgetclass, **kwargs):
        if self.getWidget(widgetclass, **kwargs):
            raise AssertionError("widget found")
        return
        
    def assertVisible(self, widgetclass, **kwargs):
        kwargs['viewable'] = 1
        self.assertExists(widgetclass, **kwargs)
        
    def countMatches(self, widgetclass, **kwargs):
        count = 0
        for w in self.allwidgets():
            if (self._widgetMatches(w, widgetclass, kwargs)):
                count += 1
        return count

    def waitForExists(self, widgetclass, **kwargs):
        for i in range(2000): # TODO change to use elapsed time
            self.root.update()
            self.root.update_idletasks()
            try:
                self.assertExists(widgetclass, **kwargs)
                return
            except AssertionError:
                pass
        raise Timeout("wait condition never satisfied")

    def waitForNotExists(self, widgetclass, **kwargs):
        for i in range(2000): # TODO change to use elapsed time
            self.root.update()
            self.root.update_idletasks()
            try:
                self.assertNotExists(widgetclass, **kwargs)
                return
            except AssertionError:
                pass
        raise Timeout("wait condition never satisfied")

    def runModalTest(self, modal_cmd, modal_testcmd):
        exc = None
        def runmodal():
            try:
                modal_testcmd()
            except Exception as e:
                print("EXCEPTION!!!!!!!!"+str(e))
                exc = e
        self.root.after_idle(runmodal)
        modal_cmd()
        if exc is not None:
            raise exc

    def _widgetType(self, w):
        cls = w.winfo_class()
        if re.match("^T[A-Z]", cls):
            cls = cls[1:]
        return cls.lower()

class Timeout(Exception):
    pass

def requires_mac():
    if sys.platform != 'darwin':
        raise ResourceDenied("Not on Mac OS X")

def requires_windows():
    if sys.platform[:3] != 'win':
        raise ResourceDenied("Not on Windows")

