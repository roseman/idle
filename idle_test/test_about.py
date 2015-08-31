"Functional tests for about dialog"


from idlelib.idle_test.idletestcase import IdleTestCase


class AboutTest(IdleTestCase):

    def setUp(self):
        self.open_editwindow()

    def tearDown(self):
        self.close_editwindow()

    def test_basics(self):
        self.text.event_generate('<<about-idle>>')   
        self.waitForExists('toplevel', title='About IDLE') 
        self.assertExists('label', text='More...', viewable=1)   
        abt = self.getWidget('toplevel', title='About IDLE')
        self.assertEqual(self.root.tk.eval('wm stackorder ' + str(abt) +
                    ' isabove '+str(self.topwin)), '1')
        self.assertNotExists('menubutton')
        self.getWidget('label', text='More...').event_generate('<1>')
        self.waitForExists('label', text='More...', viewable=0)
        self.assertExists('menubutton', text='IDLE Readme')
        txt = self.getWidget('text', toplevel='About IDLE')
        self.assertRegex(txt.get('1.0','end'), "IDLE is Python's")
        mb = self.getWidget('menubutton', toplevel='About IDLE')
        mb['menu'].invoke(4)
        self.assertEqual(mb['text'], 'Python Copyright')
        self.assertNotRegex(txt.get('1.0','end'), "IDLE is Python's")
        self.assertRegex(txt.get('1.0','end'), 
                    "Corporation for National Research Initiatives")
        abt.close()

    def test_not_modal(self):
        self.text.event_generate('<<about-idle>>')   
        self.waitForExists('toplevel', title='About IDLE', viewable=1) 
        abt = self.getWidget('toplevel', title='About IDLE')
        self.assertEqual(self.root.tk.eval('wm stackorder ' + str(abt) +
                    ' isabove '+str(self.topwin)), '1')
        self.text.event_generate('<1>')
        self.assertEqual(self.root.tk.eval('wm stackorder ' + str(abt) +
                    ' isbelow '+str(self.topwin)), '1')
        abt.close()

if __name__ == '__main__':
    IdleTestCase.main(verbosity=2)
