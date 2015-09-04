"Functional tests for find dialogs"

from idlelib.idle_test.idletestcase import IdleTestCase
from idlelib.EditorWindow import EditorWindow


class FindDialogsTest(IdleTestCase):

    def setUp(self):
        self.open_editwindow()

    def tearDown(self):
        self.close_editwindow()

    def test_find(self):
        self.text.insert('1.0', 'once upon a time\nthere was a nice\nstory.')
        self.text.event_generate('<<find>>', when='tail')
        self.waitForExists('toplevel', title='Search Dialog', viewable=1)
        self.assertExists('button', text='close') # TODO - should be Close
        self.assertExists('button', text='Find Next')
        entry = self.getWidget('entry')
        self.assertEqual(entry.get(), '')
        entry.insert(0, 'c')
        entry.event_generate('<Return>')
        start, end = self.text.tag_ranges('sel')
        self.assertEqual(str(start), '1.2')
        self.assertEqual(str(end), '1.3')
        entry.event_generate('<Escape>')
        self.waitForExists('toplevel', title='Search Dialog', viewable=0)

    def test_twowindows(self):
        self.text['background'] = 'red'
        self.text['exportselection'] = False
        ed2 = self.flist.new()
        text2 = ed2.text
        text2['exportselection'] = False
        topwin2 = ed2.top
        self.root.update_idletasks()
        self.assertEqual(self.root.tk.eval('wm stackorder ' + str(topwin2) +
                    ' isabove '+str(self.topwin)), '1')
        self.text.insert('1.0', 'abc def ghi\nabc def ghi\nabc def ghi')
        text2.insert('1.0', 'ghi def abc\nghi def abc\nghi def abc')
        text2.event_generate('<<find>>', when='tail')
        self.waitForExists('toplevel', title='Search Dialog', viewable=1)
        entry = self.getWidget('entry')
        entry.delete(0, 'end')
        entry.insert(0, 'abc')
        self.getWidget('button', text='Find Next').invoke()
        start, end = text2.tag_ranges('sel')
        self.assertEqual((str(start), str(end)), ('1.8', '1.11'))
        self.getWidget('button', text='Find Next').invoke()
        start, end = text2.tag_ranges('sel')
        self.assertEqual((str(start), str(end)), ('2.8', '2.11'))
        self.topwin.tkraise(topwin2)
        self.topwin.update_idletasks()
        self.topwin.update_idletasks()
        self.topwin.update()
        self.text.event_generate('<Map>')
        import time; time.sleep(0.1)
        print("********** JUST SWITCHED WINDOWS ****************")
        self.assertEqual(self.root.tk.eval('wm stackorder ' + str(topwin2) +
                    ' isbelow '+str(self.topwin)), '1')
        self.getWidget('button', text='Find Next').invoke()
        start, end = text2.tag_ranges('sel')
        self.assertEqual((str(start), str(end)), ('2.8', '2.11'))
        start, end = self.text.tag_ranges('sel')
        self.assertEqual((str(start), str(end)), ('1.0', '1.3'))
        
    def test_close_when_last_editor_closes(self):
        pass   # TODO
            

if __name__ == '__main__':
    IdleTestCase.main(verbosity=2)
