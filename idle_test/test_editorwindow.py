"Functional tests for main editor window"


from idlelib.idle_test.idletestcase import IdleTestCase


class EditorWindowTest(IdleTestCase):

    def setUp(self):
        self.open_editwindow()

    def tearDown(self):
        self.close_editwindow()

    def test_mainwindow_appearance(self):                   # Issue 24750
        self.assertExists('toplevel', title='Untitled')
        self.assertExists('text', highlightthickness=0)
        self.assertNotExists('label', text='Col: 0', relief='sunken')
        self.assertExists('separator')
        # TODO - status bar not same color as text widget
        # TODO - scrollbar

    def test_no_tearoff(self):                              # Issue 13884
        self.assertExists('menu', tearoff=0)
        self.assertNotExists('menu', tearoff=1)    


if __name__ == '__main__':
    IdleTestCase.main(verbosity=2)
