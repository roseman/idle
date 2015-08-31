"Functional tests for find dialogs"

from idlelib.idle_test.idletestcase import IdleTestCase


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


if __name__ == '__main__':
    IdleTestCase.main(verbosity=2)
