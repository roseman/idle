import os
from idlelib.idle_test.tktestcase import TkTestCase
from idlelib import uifactory
# Don't import anything that would cause configHandler to be imported, as
# that loads the config files before we get a chance to move them away
# from idlelib.uipreferences import PreferencesDialog



class UIpreferencesTest(TkTestCase):

    @classmethod
    def setUpClass(cls):
        TkTestCase.setUpClass()
        cls.move_prefs_files('config', 'keep')
        
    @classmethod
    def tearDownClass(cls):
        TkTestCase.tearDownClass()
        cls.move_prefs_files('config', None)
        cls.move_prefs_files('keep', 'config')

    @classmethod
    def move_prefs_files(cls, from_, to_=None):
        cls.cfgdir = '/Users/roseman/.idlerc'
        cls.cfgtypes =  ('main', 'extensions', 'highlight', 'keys')
        for type_ in cls.cfgtypes:
            src = os.path.join(cls.cfgdir, from_ + '-' + type_ + '.cfg')
            if os.path.exists(src):
                if to_ is not None:
                    dest = os.path.join(cls.cfgdir, to_ + '-' + type_ + '.cfg')
                    if os.path.exists(dest):
                        os.remove(dest)
                    os.rename(src, dest)
                    print("MOVED "+src+" TO "+dest)
                else:
                    os.remove(src)
                    print("DELETED "+src)

    def setUp(self):
        self.root.wm_withdraw()
        uifactory.initialize(self.root)
        import idlelib.uipreferences
        self.dlg = idlelib.uipreferences.PreferencesDialog(parent=self.root)
        self.waitForExists('toplevel', title='Preferences', viewable=1)

    def tearDown(self):
        self.dlg.close()

    def switchTab(self, label):
        '''Helper since we cannot inspect inside tabs directly when they
        are not built up from other Tkinter widgets, like on Mac.'''
        t = self.getWidget('notebook')
        for idx in range(0, t.index('end')):
            if t.tab(idx, 'text') == label:
                t.select(idx)
                t.update()
                t.update_idletasks()
                return
        raise AssertionError("tab not found")
        
    def test_dialog(self):
        '''Tests for overall appearance and functionality of dialog'''
        self.assertEqual(self.getWidget('notebook').tab('current', 'text'),
                         'Fonts/Tabs') # start on Fonts/Tabs page
        self.assertExists('button', text='OK')
        self.assertExists('button', text='Apply')
        self.assertExists('button', text='Cancel')
        
    def test_fonts_pane(self):
        self.switchTab('Fonts/Tabs')
        self.assertVisible('label', text='Indent:')
        self.assertEqual(self.getWidget('spinbox', viewable=1).get(), '4')
        
    def test_themes_pane(self):
        self.switchTab('Themes')
        self.assertNotExists('label', text='Indent:', viewable=1)
        self.assertVisible('label', text='Themes')

    def test_keys_pane(self):
        self.switchTab('Keys')
        self.assertVisible('label', text='Keys')

    def test_general_pane(self):
        self.switchTab('General')
        self.assertVisible('label', text='General')

    def test_extensions_pane(self):
        self.switchTab('Extensions')
        self.assertVisible('label', text='Extensions')

    # TODO - if all editorwindows quit but prefs still up, check doesn't exit

if __name__ == '__main__':
    TkTestCase.main(verbosity=2)
