"""
IDLE Component (e.g. editor, shell, dialog, etc.)
"""

class Component(object):

    def __init__(self, flist):
        self.flist = flist
        self.top = None     # component should set this to its Container
        self.type = 'component'

    def close(self, without_save=False):
        "Called e.g. when close button on window containing us is clicked"
        self.flist.unregister_maybe_terminate(self)
        self.flist = None
        # NOTE: container will destroy all widgets after this returns

    def wakeup(self):
        "Bring component to front and set focus"
        self.top.move_to_front(self)
        # NOTE: we used to call 'wakeup' on ListedTopLevel widgets
        #       (now Container) rather than the component itself;
        #       because containers will eventually contain more than
        #       one component, this is a better approach.

    def short_title(self):
        return 'component'

    def long_title(self):
        return None

    def get_saved(self):
        return True     # by default, no changes to component need saving

    def maybesave(self):
        return "yes"    # needed if get_saved ever returns False; should
                        # prompt to save, save if selected, and return one of
                        # 'yes', 'no', or 'cancel'

    # Below here are various notifications that subclasses may choose
    # to act on if needed

    def configuration_will_change(self):
        "Callback from configuration dialog before settings are applied."
        pass

    def configuration_changed(self):
        "Callback from configuration dialog after settings are applied."
        pass

    def filenames_changed(self):
        "Callback when one or more filenames changed; rebuild windows menu"
        pass
