"""
IDLE Preferences dialog

TODO (as of August 18/2015):
- error checking for help sources
- on deleting a keyset, go back to the right one for their platform


NOTES:

Just want to provide a bit of a heads up in terms of how the code in here
is structured, vs. how it was done in configDialog.py.

Most notably, things are separated out more:
  1. There is a class which handles pending (not yet applied) changes,
     i.e. 'changedItems'.
  2. There is a (short) class for the main dialog.
  3. There is a base class for preference panes, with some common utilities.
  4. Each pane has its own class.

This keeps things together more, and makes it easier to use simpler instance
variable names without worrying about stomping on something else.

Second, while the old code notified all the active editor windows when
preferences were applied (requiring knowledge of editor window objects),
we now have an 'observer' object that gets passed in that we notify.
In practice, this is the global FileList object.

Third, a lot of the boilerplate to do with creating and managing TkVar
instances, and tying them to configuration options has been replaced by
a 'register_prefvar' call which takes care of all the housekeeping.

I won't comment much here on the actual UI differences, beyond noting that
things were adjusted so that the use of further dialogs (e.g. for editing
themes or help sources) was minimized.

I did want to draw attention to how the new querydialog can handle custom
validations while the dialog is still posted, without adding additional error
dialogs. Search for 'validate_theme' for an example.
"""

import os
from collections import OrderedDict
from tkinter import *
from tkinter import ttk
import tkinter.messagebox as messagebox
import tkinter.colorchooser as colorchooser
import tkinter.filedialog as filedialog
import tkinter.font as tkFont
from idlelib.configHandler import idleConf
from idlelib import macosxSupport
from idlelib import querydialog
from idlelib import ui



dlg = None

def show(parent, flist):
    "Main routine; show dialog window, creating or raising as necessary."
    global dlg
    if dlg is None:
        dlg = PreferencesDialog(parent, flist, destroy_callback=_destroyed)
    dlg.lift()
    dlg.focus_set()

def _destroyed():
    global dlg
    dlg = None
    

class PreferencesChanger(object):
    """
    Maintain sets of preferences that are in the process of being
    changed, but don't push them to the configuration system until we're
    told to apply all changes.

    A possible extension of this is to have all (or select) changes
    immediately be pushed.

    Much of this logic should probably be pushed into configHandler.py
    """
    def __init__(self, observer=None):
        self.observer = observer
        self.reset()

    def change(self, type_, section, item, value):
        if section not in self.changedItems[type_]:
            self.changedItems[type_][section] = {}
        self.changedItems[type_][section][item] = str(value)

    def get_pending_change(self, type_, section, item):
        "Note: can return an exception if no pending change was made"
        return self.changedItems[type_][section][item]        

    def cancel_pending_change(self, type_, section, item=None):
        """Note: will not generate errors if the section or item is not
        present, but we do expect the type to be there"""
        if section in self.changedItems[type_]:
            if item is not None:
                if item in self.changedItems[type_][section]:
                    del(self.changedItems[type_][section][item])
            else:
                del(self.changedItems[type_][section])

    def reset(self):
        self.changedItems = {'main':{}, 'highlight':{}, 'keys':{},
                            'extensions':{}}

    def save_changes(self):
        "Dynamically apply configuration changes"
        if self.observer:
            self.observer.configuration_will_change()
        self.SaveAllChangedConfigs()
        if self.observer:
            self.observer.configuration_changed()

    def SetUserValue(self, type_, section, item, value):
        if idleConf.defaultCfg[type_].has_option(section, item):
            if idleConf.defaultCfg[type_].Get(section, item) == value:
                # the setting equals a default, remove it from user cfg
                return idleConf.userCfg[type_].RemoveOption(section, item)
        # if we got here set the option
        return idleConf.userCfg[type_].SetOption(section, item, value)

    def SaveAllChangedConfigs(self):
        "Save configuration changes to the user config file."
        idleConf.userCfg['main'].Save()
        for configType in self.changedItems:
            cfgTypeHasChanges = False
            for section in self.changedItems[configType]:
                if section == 'HelpFiles':
                    # this section gets completely replaced
                    idleConf.userCfg['main'].remove_section('HelpFiles')
                    cfgTypeHasChanges = True
                for item in self.changedItems[configType][section]:
                    value = self.changedItems[configType][section][item]
                    if self.SetUserValue(configType, section, item, value):
                        cfgTypeHasChanges = True
            if cfgTypeHasChanges:
                idleConf.userCfg[configType].Save()
        for configType in ['keys', 'highlight']:
            # save these even if unchanged!
            idleConf.userCfg[configType].Save()
        self.reset()   # clear the changed items dict


class PreferencesDialog(Toplevel):
    """
    IDLE preferences dialog, providing a user interface for modifying
    configuration settings.

    Consists of multiple preference panes, organized via a tabbed interface.

    Our preference_changed() routine should be called whenever a
    preference has been changed in a pane.
    """
    def __init__(self, parent, observer=None, destroy_callback=None):
        Toplevel.__init__(self, parent)
        self.parent = parent
        self.observer = observer
        self.destroy_callback = destroy_callback
        self.panes = []
        self.pref_changer = PreferencesChanger(observer)
        self.wm_withdraw()
        self.title('Preferences')
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.config(borderwidth=0)
        self.outerframe = ttk.Frame(self)
        self.outerframe.grid(column=0, row=0, sticky='NWES')
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.outerframe.grid_columnconfigure(0, weight=1)
        self.outerframe.grid_rowconfigure(0, weight=1)
        tabs = self.tabs = ttk.Notebook(self.outerframe)
        tabs.grid(column=0, row=0, sticky='NWES')
        if ui.windowing_system != 'aqua':
            tabs.grid_configure(pady=[10,10])
        self.add_panes(tabs)
        buttons = ttk.Frame(self.outerframe, padding=[0,0,10,10])
        self.w_ok = ttk.Button(buttons, text='OK', command=self.Ok)
        self.w_apply = ttk.Button(buttons, text='Apply', command=self.Apply)
        self.w_cancel = ttk.Button(buttons, text='Cancel', command=self.Cancel)
        buttons.grid(column=0, row=99, sticky='SE')
        self.w_ok.grid(column=0, row=0, padx=5)
        self.w_apply.grid(column=1, row=0, padx=5)
        self.w_cancel.grid(column=2, row=0, padx=5)
        self.update_idletasks()     # avoid flicker
        self.wm_deiconify()

    def add_pane(self, pane, label):
        self.panes.append(pane)
        self.tabs.add(pane, text=label)

    def add_panes(self, parent):
        self.add_pane(FontsPane(parent, self), 'Fonts/Tabs')
        self.add_pane(ThemesPane(parent, self), 'Themes')
        self.add_pane(KeysPane(parent, self), 'Keys')
        self.add_pane(GeneralPane(parent, self), 'General')
        self.add_pane(ExtensionsPane(parent, self), 'Extensions')

    def preference_changed(self, type_, section, item, value):
        self.pref_changer.change(type_, section, item, value)

    def get_pending_change(self, type_, section, item):
        return self.pref_changer.get_pending_change(type_, section, item)

    def cancel_pending_change(self, type_, section, item=None):
        return self.pref_changer.cancel_pending_change(type_, section, item)

    def Ok(self):
        self.Apply()
        self.close()

    def Apply(self):
        self.pref_changer.save_changes()

    def Cancel(self):
        self.close()

    def close(self):
        if self.destroy_callback:
            self.destroy_callback()
        self.destroy()


class PreferencesPane(ttk.Frame):
    """
    Base class for an individual preference pane.

    Provide common utilities (e.g. managing preferences and variables
    attached to preferences).
    """
    def __init__(self, parent, owner):
        ttk.Frame.__init__(self, parent)
        self.owner = owner
        self.parent = parent

    def register_prefvar(self, type_, sec, item, varclass=StringVar, **kw):
        v = varclass(self.parent)
        if 'value' in kw:
            v.set(kw['value'])
        else:
            v.set(idleConf.GetOption(type_, sec, item, **kw))
        v.trace_variable('w', lambda var, idx, op:
                         self.prefvar_changed(v, type_, sec, item))
        return v

    def prefvar_changed(self, v, type_, sec, item):
        self.owner.preference_changed(type_, sec, item, v.get())

    def preference_changed(self, type_, sec, item, value):
        self.owner.preference_changed(type_, sec, item, value)

    def get_pending_change(self, type_, sec, item):
        return self.owner.get_pending_change(type_, sec, item)

    def cancel_pending_change(self, type_, sec, item=None):
        self.owner.cancel_pending_change(type_, sec, item)


class FontsPane(PreferencesPane):
    """
    Preference pane for modifying the font and tab indent used by all
    editor windows.
    """
    def __init__(self, parent, owner):
        PreferencesPane.__init__(self, parent, owner)

        # font family
        config_font = idleConf.GetFont(self, 'main', 'EditorWindow')
        config_family = config_font[0].lower()
        self.family_v = self.register_prefvar('main', 'EditorWindow',
                                              'font', value=config_family)
        self.family_v = StringVar(parent)
        self.family_v.set(config_family)
        self.family = Listbox(self, height=5, takefocus=FALSE,
                              exportselection=FALSE, activestyle='none')
        fonts = list(tkFont.families(self))
        fonts.sort()
        for font in fonts:
            self.family.insert(END, font)
            if font.lower() == config_family:
                self.family.select_set(END)
                self.family.select_anchor(END)
        self.family.see(ANCHOR)
        self.family.bind('<<ListboxSelect>>', self.family_changed)
        scroll_family = ttk.Scrollbar(self, command=self.family.yview)
        self.family.config(yscrollcommand=scroll_family.set)
        self.family.grid(column=0, columnspan=3, row=0, rowspan=2,
                         sticky='NWES')
        scroll_family.grid(column=3, row=0, rowspan=2, sticky='NS')

        # font size
        config_size = config_font[1]
        self.size_v = self.register_prefvar('main', 'EditorWindow',
                                            'font-size', value=config_size)
        lbl_size = ttk.Label(self, text='Font Size:')
        sizes = ['7', '8', '9', '10', '11', '12', '13', '14', '16', '18',
                 '20', '22']
        self.size = ttk.Combobox(self, textvariable=self.size_v,
                                 values=sizes, width=4, state='readonly')
        lbl_size.grid(column=0, row=2, sticky='SE')
        self.size.grid(column=1, row=2, sticky='SW', padx=[5,0])

        # font weight
        config_bold = config_font[2] == 'bold'
        self.bold_v = self.register_prefvar('main', 'EditorWindow',
                        'font-bold', varclass=BooleanVar, value=config_bold)
        bold = ttk.Checkbutton(self, variable=self.bold_v, onvalue=1,
                        offvalue=0, text='Bold', command=self.update_font)
        bold.grid(column=2, row=2, sticky='S')

        # font sample
        frame_sample = ttk.Frame(self, relief=SOLID, borderwidth=1)
        self.sample = ttk.Label(frame_sample, anchor=CENTER,
                    text='AaBbCcDdEe\nFfGgHhIiJjK\n1234567890\n#:+=(){}[]')
        frame_sample.grid(column=4, row=0, sticky='NWES', padx=[10,0])
        frame_sample.columnconfigure(0, weight=1)
        frame_sample.rowconfigure(0, weight=1)
        self.sample.grid(column=0, row=0, sticky='WE')

        # indentation width
        self.indent_v = self.register_prefvar('main', 'Indent', 'num-spaces',
                                default=4, type='int', varclass=IntVar)
        lbl_indent = ttk.Label(self, text='Indent:')
        info_indent = ttk.Label(self, justify=LEFT,
                                text='Python Standard: 4 Spaces!')
        self.indent = ui.Spinbox(self, textvariable=self.indent_v,
                                           from_=2, to=16, width=3)
        lbl_indent.grid(column=0, row=3, sticky='SE')
        self.indent.grid(column=1, row=3, sticky='SW', padx=[5,0])
        info_indent.grid(column=2, columnspan=3, row=3, sticky='SW')

        self.configure(padding=6)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(4, weight=3)
        self.grid_rowconfigure(0, weight=2)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, pad=5)
        self.grid_rowconfigure(3, pad=10)

    def family_changed(self, event):
        self.family_v.set(self.family.get(
                                self.family.curselection()).lower())
        self.update_font()

    def update_font(self, event=None):
        newFont = (self.family_v.get(), self.size_v.get(),
                   tkFont.BOLD if self.bold_v.get() else tkFont.NORMAL)
        self.sample['font'] = newFont
        self.prefvar_changed(self.family_v, 'main', 'EditorWindow', 'font')
        self.prefvar_changed(self.size_v, 'main', 'EditorWindow', 'font-size')
        self.prefvar_changed(self.bold_v, 'main', 'EditorWindow', 'font-bold')


class ThemesPane(PreferencesPane):
    """
    Preference pane for choosing between highlighting "themes",
    which control the color different Python syntax elements are displayed
    in within the editor.

    Built-in themes are available, and users can add their own, modifying
    the individual colors used for each type of element.
    """
    def __init__(self, parent, owner):
        PreferencesPane.__init__(self, parent, owner)

        # list of themes, and current selection
        self.theme_v = self.register_prefvar('main', 'Theme', 'name')
        self.themes = Listbox(self, exportselection=FALSE, activestyle='none')
        self.default_themes = idleConf.GetSectionList('default', 'highlight')
        self.themes.bind('<<ListboxSelect>>', self.theme_changed)
        self.themes.grid(column=0, row=1, columnspan=2, rowspan=5, 
                         sticky='nwes')
        scroll = ttk.Scrollbar(self, command=self.themes.yview)
        self.themes.yscrollcommand = scroll.set
        scroll.grid(column=2, row=1, rowspan=5, sticky='ns', padx=[0,10])

        # new and delete theme buttons
        self.new_button = ttk.Button(self, text='New...',
                                     command=self.newtheme)
        self.new_button.grid(column=0, row=6)
        self.delete_button = ttk.Button(self, text='Delete...',
                                        command=self.delete_theme)
        self.delete_button.grid(column=1, row=6, sticky=W, padx=[0,20])

        # highlight sample
        self.load_element_data()
        self.sample = Text(
                self, relief=SOLID, borderwidth=1, wrap=NONE,
                font='TkFixedFont', cursor=ui.clickable_cursor,
                width=21, height=12, takefocus=FALSE, highlightthickness=0)
        self.sample.bind('<Double-Button-1>', lambda e: 'break')
        self.sample.bind('<B1-Motion>', lambda e: 'break')
        for txTa in self.sample_text_tags:
            self.sample.insert(END, txTa[0], txTa[1])
        for element in self.elements:
            self.sample.tag_bind(self.elements[element][0], '<1>',
                        lambda ev,element=element:self.element_v.set(element))
        self.sample.config(state=DISABLED)
        self.sample.grid(column=3, row=1, columnspan=2, rowspan=2,
                         sticky='nwe', padx=[0,10])

        # theme element we're viewing or changing; can be changed either with
        # the combobox we use here, or clicking the element in the sample
        self.element_v = StringVar(parent)
        self.element_v.set('Normal Text')
        self.element_v.trace_variable('w', lambda v,i,o:self.update_colors())
        elementNames = list(self.elements.keys())
        elementNames.sort(key=lambda x: self.elements[x][1])
        self.element = ttk.Combobox(self, state='readonly',
                    textvariable=self.element_v, values=elementNames,
                    width=20, exportselection=False)
        # by default comboboxes highlight their selection; change that:
        self.element.bind('<<ComboboxSelected>>',
                    lambda ev:self.element.selection_clear())
        self.element.grid(column=3, row=4, columnspan=2, pady=[5,0])

        # color wells to view/change foreground and background element colors
        self.foregroundWell = Frame(self, width=20, height=20, borderwidth=3,
                                    relief='ridge', background='black',
                                    cursor=ui.clickable_cursor)
        self.foregroundWell.bind('<1>',
                        lambda ev: self.change_color(foreground=True))
        self.foregroundWell.grid(column=4, row=5, pady=5, sticky='w', padx=6)
        ttk.Label(self, text='Foreground:').grid(column=3, row=5,
                                                 sticky='e', padx=[20,0])
        self.backgroundWell = Frame(self, width=20, height=20, borderwidth=3,
                                    relief='ridge', background='white',
                                    cursor=ui.clickable_cursor)
        self.backgroundWell.bind('<1>',
                        lambda ev: self.change_color(foreground=False))
        self.backgroundWell.grid(column=4, row=6, pady=5, sticky='w', padx=6)
        ttk.Label(self, text='Background:').grid(column=3, row=6,
                                                 sticky='e', padx=[20,0])
        self.configure(padding=6)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(4, weight=1)
        self.grid_rowconfigure(8, weight=10)
        self.rebuild_themes_list()

    def rebuild_themes_list(self):
        "Update the listbox containing the available themes"
        self.themes.delete(0, END)
        for t in sorted(self.all_theme_names()):
            self.themes.insert(END, t)
            if t == self.theme_v.get():
                self.themes.select_set(END, END)
        self.theme_changed()

    def theme_changed(self, event=None):
        "Current theme (from listbox) changed; adjust state and UI to match."
        theme = self.themes.get(self.themes.curselection())
        if theme in self.default_themes:
            self.delete_button['state'] = 'disabled'
        else:
            self.delete_button['state'] = 'normal'
        self.theme_v.set(theme)
        self.update_colors()

    def change_color(self, foreground=True):
        "Called when a color well is clicked on."
        if self.theme_v.get() in self.default_themes:
            self.newtheme(tried_modifying_builtin=True)
        else:
            title = 'Foreground' if foreground else 'Background'
            title += ' for %s' % self.element_v.get()
            color = self.current_color(self.theme_v.get(),
                        self.element_v.get(), 'fg' if foreground else 'bg')
            newcolor = colorchooser.askcolor(parent=self, title=title,
                                             initialcolor=color)[1]
            if newcolor is not None:
                fgbg = '-foreground' if foreground else '-background'
                self.preference_changed('highlight', self.theme_v.get(),
                        self.elements[self.element_v.get()][0]+fgbg, newcolor)
                self.update_colors()

    def update_colors(self):
        """"When a theme, color or the active element changes, update the
        colors in the UI, both the sample and also the color wells, to match
        the new state."""
        theme = self.theme_v.get()
        for element in self.elements:
            elt = self.elements[element][0]
            fg = self.current_color(self.theme_v.get(), element, 'fg')
            bg = self.current_color(self.theme_v.get(), element, 'bg')
            if elt == 'cursor':
                bg = idleConf.GetHighlight(theme, 'normal', fgBg='bg')
            self.sample.tag_config(elt, background=bg, foreground=fg)
            if element == self.element_v.get():
                self.foregroundWell.configure(background=fg)
                self.backgroundWell.configure(background=bg)

    def all_theme_names(self):
        themelist = self.default_themes[:]
        userlist = idleConf.GetSectionList('user', 'highlight')
        if userlist:
            themelist.extend(userlist)
        return themelist

    def current_color(self, theme, element, fgBg):
        """Retrieve the current color of a theme element, factoring in we may
        have some unsaved changes."""
        elt = self.elements[element][0]
        pref = elt + '-foreground' if fgBg == 'fg' else elt + '-background'
        try:
            c = self.get_pending_change('highlight', theme, pref)
        except KeyError:
            c = idleConf.GetHighlight(theme, elt, fgBg)
        return c

    def newtheme(self, tried_modifying_builtin=False):
        "Ask for the name of a new theme, and create it."
        cur = self.theme_v.get()
        prompt = ''
        if tried_modifying_builtin:
            prompt = '"' + cur + '" is built-in and cannot be modified.\n'
            prompt += 'Create a new theme based on it instead?\n\n'
        prompt += 'Name for new theme:'
        new_theme = self.suggested_themename(cur)
        def validate_theme(s):
            if not s:
                raise ValueError('Cannot be blank')
            if len(s) > 30:
                raise ValueError('Cannot be longer than 30 characters')
            if s in self.all_theme_names():
                raise ValueError('Name already used')
        new_theme = querydialog.askstring(parent=self, prompt=prompt,
                    title='Create New Theme', initialvalue=new_theme,
                    oklabel='Create', validatecmd=validate_theme)
        if new_theme is not None:
            if not idleConf.userCfg['highlight'].has_section(new_theme):
                idleConf.userCfg['highlight'].add_section(new_theme)
            for element in self.elements:
                idleConf.userCfg['highlight'].SetOption(new_theme,
                                self.elements[element][0]+'-foreground',
                                self.current_color(cur, element, 'fg'))
                idleConf.userCfg['highlight'].SetOption(new_theme,
                                self.elements[element][0]+'-background',
                                self.current_color(cur, element, 'bg'))
            self.theme_v.set(new_theme)
            self.rebuild_themes_list()

    def suggested_themename(self, basename):
        """Suggest a new name for a theme based on another theme.
        This will be of the form "original Copy" or "original Copy 2",
        taking into account the original may already be a copy."""
        copycount = 1
        name = basename[:]
        match = re.search('^(.*) Copy( [0-9]+)?$', basename)
        if match:
            name = match.group(1)
            num = match.group(2)
            if num is not None:
                copycount = int(num.strip())
        while True:
            possiblename = name + ' Copy'
            if copycount > 1:
                possiblename += ' '+str(copycount)
            if possiblename not in self.all_theme_names():
                return possiblename
            copycount += 1

    def delete_theme(self):
        theme = self.theme_v.get()
        if theme not in self.default_themes:  # shouldn't happen
            delmsg = 'Are you sure you wish to delete the theme %r ?'
            if messagebox.askyesno('Delete Theme', delmsg % theme,
                                     parent=self):
                idleConf.userCfg['highlight'].remove_section(theme)
                self.cancel_pending_change('highlight', theme)
                idleConf.userCfg['highlight'].Save()
                self.theme_v.set(self.default_themes[0])
                self.rebuild_themes_list()

    def load_element_data(self):
        self.elements = {
            'Normal Text':('normal', '00'),
            'Python Keywords':('keyword', '01'),
            'Python Definitions':('definition', '02'),
            'Python Builtins':('builtin', '03'),
            'Python Comments':('comment', '04'),
            'Python Strings':('string', '05'),
            'Selected Text':('hilite', '06'),
            'Found Text':('hit', '07'),
            'Cursor':('cursor', '08'),
            'Error Text':('error', '09'),
            'Shell Normal Text':('console', '10'),
            'Shell Stdout Text':('stdout', '11'),
            'Shell Stderr Text':('stderr', '12'),
            }
        self.sample_text_tags = (
            ('#you can click here', 'comment'), ('\n', 'normal'),
            ('#to choose items', 'comment'), ('\n', 'normal'),
            ('def', 'keyword'), (' ', 'normal'),
            ('func', 'definition'), ('(param):\n  ', 'normal'),
            ('"""string"""', 'string'), ('\n  var0 = ', 'normal'),
            ("'string'", 'string'), ('\n  var1 = ', 'normal'),
            ("'selected'", 'hilite'), ('\n  var2 = ', 'normal'),
            ("'found'", 'hit'), ('\n  var3 = ', 'normal'),
            ('list', 'builtin'), ('(', 'normal'),
            ('None', 'keyword'), (')\n\n', 'normal'),
            (' error ', 'error'), (' ', 'normal'),
            ('cursor |', 'cursor'), ('\n ', 'normal'),
            ('shell', 'console'), (' ', 'normal'),
            ('stdout', 'stdout'), (' ', 'normal'),
            ('stderr', 'stderr'), ('\n', 'normal'))


class KeysPane(PreferencesPane):
    """
    Prefernce pane to select between, view and modify sets of key bindings.
    
    There are many parallels with how themes are handled, including the
    handling of built-in and user themes, forcing writes to the 
    configuration system on creating and destroying key sets, and the
    need to poke around in pending changes at times.
    """
    def __init__(self, parent, owner):
        PreferencesPane.__init__(self, parent, owner)

        # list of keysets, and currently selected keyset
        self.default_keysets = idleConf.GetSectionList('default', 'keys')
        self.keyset_v = self.register_prefvar('main', 'Keys', 'name')
        self.keyset = ttk.Combobox(self, state='readonly', width=20,
                          textvariable=self.keyset_v, exportselection=False)
        # by default comboboxes highlight their selection; change that:
        self.keyset.bind('<<ComboboxSelected>>', self.keyset_changed)
        self.keyset.grid(column=2, row=0, sticky='we')
        ttk.Label(self, text='Key Bindings Set:').grid(column=1, row=0)
        
        # new or delete key set buttons
        self.new_button = ttk.Button(self, text='New...',
                                     command=self.newkeyset)
        self.new_button.grid(column=4, row=0)
        self.delete_button = ttk.Button(self, text='Delete...',
                                 command=self.delete_keyset)
        self.delete_button.grid(column=5, row=0)
        
        # sync'ed listboxes holding list of actions and keys
        # for a Tcl based description of scrolling two widgets simultaneously,
        # see http://wiki.tcl.tk/9254
        frm = ttk.Frame(self)
        frm.grid(column=1, row=1, columnspan=5, sticky='news', pady=[10,10])
        self.actions = Listbox(frm, exportselection=FALSE, activestyle='none',
                               borderwidth=0, yscrollcommand=self.yset)
        self.keys = Listbox(frm, exportselection=FALSE, activestyle='none',
                            borderwidth=0, yscrollcommand=self.yset)
        self.scroll = ttk.Scrollbar(frm, command=self.yview)
        self.actions.bind('<<ListboxSelect>>', 
                        lambda e: self.listsel('actions'))
        self.keys.bind('<<ListboxSelect>>', 
                        lambda e: self.listsel('keys'))
        self.actions.grid(column=1, row=1, sticky='nwes')
        self.keys.grid(column=2, row=1, sticky='nwes')
        self.scroll.grid(column=3, row=1, sticky='ns')
        frm.grid_columnconfigure(2, weight=1)
        frm.grid_rowconfigure(1, weight=1)
        
        # fields for changing keys for currently selected action
        frm = ttk.Frame(self)
        frm.grid(column=1, row=2, columnspan=5, sticky='news', pady=[10,10])
        frm.grid_columnconfigure(2, weight=1)
        ttk.Label(frm, text='Action:').grid(column=1, row=1, sticky='e', 
                        padx=[0,10])
        self.action_l = ttk.Label(frm)
        self.action_l.grid(column=2, row=1, sticky='we')
        ttk.Label(frm, text='New Key:').grid(column=1, row=2, sticky='e',
                        padx=[0,10])
        self.keysym_v = StringVar(self)
        self.keysym_v.trace_variable('w', lambda v,i,o: self.keysym_changed())
        self.keysym = ttk.Entry(frm, textvariable=self.keysym_v)
        self.keysym.grid(column=2, row=2, sticky='we')
        self.change = ttk.Button(frm, text='Change',
                                 command=self.change_keysym)
        self.change.grid(column=3, row=2, padx=[5,0])
        self.revert = ttk.Button(frm, text='Revert',
                                 command=self.revert_keysym)
        self.revert.grid(column=4, row=2, padx=[5,0])
        self.keysym_tester = ttk.Frame(frm)   # not shown, for validating keys

        self.configure(padding=6)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.rebuild_keysets_list()

    
    def rebuild_keysets_list(self):
        "Update the combobox containing the available keysets"
        self.keyset['values'] = self.all_keyset_names()
        self.keyset_changed()
        
    def keyset_changed(self, event=None):
        "Current keyset (from combobox) changed; adjust state and UI to match"
        # by default comboboxes highlight their selection; change that:
        self.keyset.selection_clear()
        if self.keyset_v.get() in self.default_keysets:
            self.delete_button['state'] = 'disabled'
        else:
            self.delete_button['state'] = 'normal'
        # Update the listboxes to show the keys/actions for the current keyset
        self.actions.delete(0, END)
        self.keys.delete(0, END)
        self.bindings = idleConf.GetKeySet(self.keyset_v.get())
        self.binding_names = sorted(self.bindings.keys())
        for action in self.binding_names:
            try:    # update with any pending changes for this keyset
                keys = self.get_pending_change('keys', 
                            self.keyset_v.get(), action.strip('<>'))
                self.bindings[action] = keys.split(' ')
            except KeyError:
                pass
            self.actions.insert(END, action.strip('<>'))
            self.keys.insert(END, self.bindings[action])
        self.action_selected()
        
    def all_keyset_names(self):
        keysets = self.default_keysets[:]
        userlist = idleConf.GetSectionList('user', 'keys')
        if userlist:
            keysets.extend(userlist)
        return keysets
        
    def action_selected(self):
        if len(self.actions.curselection()) > 0:
            action = self.binding_names[self.actions.curselection()[0]]
            self.action_l['text'] = action.strip('<>')
            self.keysym_v.set(self.keysyms_toentry(self.bindings[action]))
            self.keysym['state'] = 'normal'
        else:
            self.action_l['text'] = ''
            self.keysym_v.set('')
            self.keysym['state'] = 'disabled'
        self.keysym_changed()
        
    def keysym_changed(self, event=None):
        self.change['state'] = 'disabled'
        self.revert['state'] = 'disabled'
        if len(self.actions.curselection()) > 0:
            action = self.binding_names[self.actions.curselection()[0]]
            if (self.keysym_v.get().strip() !=
                                self.keysyms_toentry(self.bindings[action])):
                self.revert['state'] = 'normal'
                if self.valid_keysym(self.keysym_v.get().strip()):
                    self.change['state'] = 'normal'
                    
    def change_keysym(self):
        idx = self.actions.curselection()[0]
        action = self.binding_names[idx]
        if self.keyset_v.get() in self.default_keysets:
            self.newkeyset(tried_modifying_builtin=True, which_action_idx=idx,
                            changed_value=self.keysym_v.get())
        else:
            newkey = self.keysyms_fromentry(self.keysym_v.get().strip())
            self.preference_changed('keys', self.keyset_v.get(),
                                    action.strip('<>'), newkey)
            self.keys.delete(idx)
            self.keys.insert(idx, newkey)
            self.keys.selection_set(idx, idx)
        
    def revert_keysym(self):
        if len(self.actions.curselection()) > 0:
            action = self.binding_names[self.actions.curselection()[0]]
            self.keysym_v.set(self.keysyms_toentry(self.bindings[action]))

    def keysyms_toentry(self, s):
        "Convert from list stored in preferences to a flat string"
        return ' '.join(s)
        
    def keysyms_fromentry(self, s):
        "Convert from flat string in entry to list"
        return ' '.join(re.findall('<[^>]+>', s.strip()))
        
    def valid_keysym(self, keysym):
        if re.match('^(?:(<[^>]+>)\s*)+$', keysym) is None:
            return False
        for ks in re.findall('<[^>]+>', keysym):
            if ks.endswith('->'):
                return False
            if ks.lower() in ['<shift-key>', '<control-key>',
                             '<alt-key>', '<meta-key>', '<command-key>']:
                return False
            try:
                self.keysym_tester.bind(ks, 'break')
            except Exception:
                return False
        return True
        
    def newkeyset(self, tried_modifying_builtin=False, 
                        which_action_idx=None, changed_value=None):
        cur = self.keyset_v.get()
        prompt = ''
        if tried_modifying_builtin:
            prompt = '"' + cur + '" is built-in and cannot be modified.\n'
            prompt += 'Create a new key set based on it instead?\n\n'
        prompt += 'Name for new key set:'
        new_keyset = self.suggested_keysetname(cur)
        def validate_keyset(s):
            if not s:
                raise ValueError('Cannot be blank')
            if len(s) > 30:
                raise ValueError('Cannot be longer than 30 characters')
            if s in self.all_keyset_names():
                raise ValueError('Name already used')
        new_keyset = querydialog.askstring(parent=self, prompt=prompt,
                    title='Create New Key Set', initialvalue=new_keyset,
                    oklabel='Create', validatecmd=validate_keyset)
        if new_keyset is not None:
            if not idleConf.userCfg['keys'].has_section(new_keyset):
                idleConf.userCfg['keys'].add_section(new_keyset)
            for action in self.binding_names:
                keysym = self.keysyms_toentry(self.bindings[action])
                idleConf.userCfg['keys'].SetOption(new_keyset, 
                            action.strip('<>'), keysym)
            self.keyset_v.set(new_keyset)
            self.rebuild_keysets_list()
            if which_action_idx is not None:
                self.actions.selection_clear(0, END)
                self.actions.selection_set(which_action_idx, which_action_idx)
                self.keys.selection_clear(0, END)
                self.keys.selection_set(which_action_idx, which_action_idx)
                self.action_selected()
            if changed_value is not None:
                self.keysym_v.set(changed_value)
                self.keysym_changed()
                self.keysym.focus()
        
    def suggested_keysetname(self, basename):
        """Suggest a new name for a key set based on another .
        This will be of the form "original Copy" or "original Copy 2",
        taking into account the original may already be a copy.
        We also strip off any leading 'IDLE Classic '..."""
        copycount = 1
        name = basename[:]
        if name.startswith('IDLE Classic'):
            name = name[len('IDLE Classic'):].strip()
        match = re.search('^(.*) Copy( [0-9]+)?$', basename)
        if match:
            name = match.group(1)
            num = match.group(2)
            if num is not None:
                copycount = int(num.strip())
        while True:
            possiblename = name + ' Copy'
            if copycount > 1:
                possiblename += ' '+str(copycount)
            if possiblename not in self.all_keyset_names():
                return possiblename
            copycount += 1

    def delete_keyset(self):
        keyset = self.keyset_v.get()
        if keyset not in self.default_keysets: 
            delmsg = 'Are you sure you wish to delete the key bindings set %r ?'
            if messagebox.askyesno('Delete Key Set', delmsg % keyset,
                                    parent=self):
                idleConf.userCfg['keys'].remove_section(keyset)
                self.cancel_pending_change('keys', keyset)
                idleConf.userCfg['keys'].Save()
                # TODO - go back to right one for their platform
                self.keyset_v.set(self.default_keysets[0])
                self.rebuild_keysets_list()
        
    def yset(self, *args):  
        "Used for synchronizing scrolling of two listboxes"
        self.scroll.set(*args)
        self.yview('moveto', self.scroll.get()[0])
        
    def yview(self, *args):
        "Used for synchronizing scrolling of two listboxes"
        self.actions.yview(*args)
        self.keys.yview(*args)
        
    def listsel(self, which):
        "Used to synchronize selection of listboxes, and handling selection"
        w1 = self.actions if which == 'actions' else self.keys
        w2 = self.keys if which == 'actions' else self.actions
        sel = w1.curselection()
        w2.selection_clear(0, END)
        for s in sel:
            w2.selection_set(s)
        self.action_selected()
    


class GeneralPane(PreferencesPane):
    """
    Preference pane for (generally) random miscellaneous things that
    don't fit elsewhere.
    
    Of note regarding the extra help sources: unlike with themes and
    keys, where we do commit changes to preferences when we add or
    delete items, for help sources everything is kept in the pending
    changes storage until changes are applied. Therefore, we only
    query the preferences store when first loading the dialog, and
    our own 'helplist' becomes effectively the reference copy while
    editing.
    """
    def __init__(self, parent, owner):
        PreferencesPane.__init__(self, parent, owner)

        self.userHelpBrowser = BooleanVar(parent)
        self.helpBrowser = StringVar(parent)

        self.configure(padding=10)
        self.grid_rowconfigure(0, pad=5)
        self.grid_rowconfigure(1, pad=5)
        self.grid_rowconfigure(2, pad=5)
        self.grid_columnconfigure(15, weight=1)

        # shell vs. edit
        self.editor_startup_v = self.register_prefvar('main', 'General',
                            'editor-on-startup', varclass=IntVar)
        open_editor = ttk.Radiobutton(self, text='Editor',
                                      variable=self.editor_startup_v, value=1)
        open_shell = ttk.Radiobutton(self, text='Shell',
                                     variable=self.editor_startup_v, value=0)
        startup_l = ttk.Label(self, text='Window to open at startup:')
        startup_l.grid(column=0, row=0, sticky=E, padx=[0,10], columnspan=2)
        open_editor.grid(column=11, row=0, columnspan=2, sticky=W)
        open_shell.grid(column=13, row=0, columnspan=2, sticky=W)

        # prompt to save unsaved files before running
        self.autosave_v = self.register_prefvar('main', 'General', 'autosave',
                                                varclass=IntVar)
        autosave = ttk.Checkbutton(self, text='Prompt to save',
                    variable=self.autosave_v, onvalue=1, offvalue=0)
        autosave_l = ttk.Label(self, text='Before running unsaved files:')
        autosave_l.grid(column=0, row=1, sticky=E, padx=[0,10], columnspan=2)
        autosave.grid(column=11, row=1, columnspan=4, sticky=W)

        # window size
        self.width_v = self.register_prefvar('main', 'EditorWindow', 'width')
        self.height_v = self.register_prefvar('main', 'EditorWindow', 'height')
        winsize_l = ttk.Label(self, text='Initial window size (characters):')
        width = ttk.Entry(self, width=3, textvariable=self.width_v)
        width_l = ttk.Label(self, text='Width:')
        height = ttk.Entry(self, width=3, textvariable=self.height_v)
        height_l = ttk.Label(self, text='Height:')
        winsize_l.grid(column=0, row=2, sticky=E, padx=[0,10], columnspan=2)
        width_l.grid(column=11, row=2, sticky=W)
        width.grid(column=12, row=2, sticky=W)
        height_l.grid(column=13, row=2, sticky=W)
        height.grid(column=14, row=2, sticky=W)

        # help sources list
        ttk.Separator(self).grid(column=0, row=4, sticky=EW, columnspan=20,
                                 pady=10)
        help_l = ttk.Label(self, text='Additional Help Sources:')
        self.cur_helpidx = None
        self.helpitems = idleConf.GetAllExtraHelpSourcesList()
        self.helpsrc = Listbox(self, height=5, exportselection=FALSE,
                               activestyle='none')
        for item in self.helpitems:
            self.helpsrc.insert(END, item[0])
        self.helpsrc.bind('<<ListboxSelect>>', self.helpsrc_changed)
        help_l.grid(column=0, row=5, sticky=W, columnspan=2)
        self.helpsrc.grid(column=0, row=6, sticky='nsew', rowspan=5,
                          columnspan=2)
        scroll = ttk.Scrollbar(self, command=self.helpsrc.yview)
        self.helpsrc.yscrollcommand = scroll.set
        scroll.grid(column=2, row=6, rowspan=5, sticky='ns', padx=[0,10])

        # details for help source
        menuname_l = ttk.Label(self, text='Label for menu:')
        self.menuname_v = StringVar(self)
        self.menuname = ttk.Entry(self, textvariable=self.menuname_v)
        url_l = ttk.Label(self, text="URL (or 'Browse' for file):")
        self.url_v = StringVar(self)
        self.url = ttk.Entry(self, textvariable=self.url_v)
        self.menuname_v.trace_variable('w', lambda v, i, o:
                                       self.help_details_changed())
        self.url_v.trace_variable('w', lambda v, i, o:
                                  self.help_details_changed())
        self.browse = ttk.Button(self, text='Browse', command=self.browsehelp)
        menuname_l.grid(column=11, row=6, columnspan=5, sticky=W)
        self.menuname.grid(column=11, row=7, columnspan=5, sticky=EW)
        url_l.grid(column=11, row=8, columnspan=5, sticky=W, pady=[6,0])
        self.url.grid(column=11, row=9, columnspan=5, sticky=EW)
        self.browse.grid(column=16, row=9, sticky=W)

        # buttons to add and delete
        self.new_button = ttk.Button(self, text='New', command=self.newhelp)
        self.del_button = ttk.Button(self, text='Delete', state='disabled',
                                     command=self.deletehelp)
        self.new_button.grid(column=0, row=20)
        self.del_button.grid(column=1, row=20, padx=[0,10])

        self.configure(padding=6)
        
    def helpsrc_changed(self, event=None):
        if len(self.helpsrc.curselection()) > 0:
            idx = self.cur_helpidx = self.helpsrc.curselection()[0]
            self.menuname_v.set(self.helpitems[idx][0])
            self.url_v.set(self.helpitems[idx][1])
            self.menuname.selection_clear()
            self.url.selection_clear()
            state = 'normal'
        else:
            self.cur_helpidx = None
            self.menuname_v.set('')
            self.url_v.set('')
            state = 'disabled'
        self.del_button['state'] = state
        self.browse['state'] = state
        self.url['state'] = state
        self.menuname['state'] = state

    def newhelp(self):
        self.helpitems.append(('Help', ''))
        self.helpsrc.insert(END, 'Help')
        self.helpsrc.selection_clear(0, END)
        self.helpsrc.selection_set(END, END)
        self.helpsrc_changed()
        self.menuname.selection_range(0, END)
        self.menuname.icursor(END)
        self.menuname.focus()
        self.update_preferences()
        
    def deletehelp(self):
        if self.cur_helpidx is not None:
            delmsg = ('Are you sure you wish to remove this source ' +
                     'from the Help menu?')
            if messagebox.askyesno('Delete Source', delmsg, parent=self):
                del(self.helpitems[self.cur_helpidx])
                self.helpsrc.delete(self.cur_helpidx)
                self.helpsrc.selection_clear(0, END)
                self.helpsrc_changed()
                self.update_preferences()
    
    def help_details_changed(self):
        if self.cur_helpidx is not None: 
            self.helpitems[self.cur_helpidx] = (self.menuname_v.get(), 
                                                self.url_v.get())
            # TODO - error checking; see configHelpSourceEdit: MenuOk, PathOk
            self.helpsrc.delete(self.cur_helpidx)
            self.helpsrc.insert(self.cur_helpidx, self.menuname_v.get())
            self.helpsrc.selection_clear(0, END)
            self.helpsrc.selection_set(self.cur_helpidx, self.cur_helpidx)
            self.update_preferences()
    
    def browsehelp(self):
        filetypes = [
            ("HTML Files", "*.htm *.html", "TEXT"),
            ("PDF Files", "*.pdf", "TEXT"),
            ("Windows Help Files", "*.chm"),
            ("Text Files", "*.txt", "TEXT"),
            ("All Files", "*")]
        path = self.url_v.get()
        if path:
            dir, base = os.path.split(path)
        else:
            base = None
            if sys.platform[:3] == 'win':
                dir = os.path.join(os.path.dirname(sys.executable), 'Doc')
                if not os.path.isdir(dir):
                    dir = os.getcwd()
            else:
                dir = os.getcwd()
        opendialog = filedialog.Open(parent=self, filetypes=filetypes)
        file = opendialog.show(initialdir=dir, initialfile=base)
        if file:
            self.url_v.set(file)
        
    def update_preferences(self):
        "Rebuild pending changes to preferences to match our internal list."
        self.cancel_pending_change('main', 'HelpFiles')
        for num in range(1, len(self.helpitems) + 1):
            self.preference_changed('main', 'HelpFiles', str(num),
                    ';'.join(self.helpitems[num-1][:2]))



class ExtensionsPane(PreferencesPane):
    def __init__(self, parent, owner):
        PreferencesPane.__init__(self, parent, owner)

        self.defaultCfg = idleConf.defaultCfg['extensions']
        self.userCfg = idleConf.userCfg['extensions']
        self.load_extensions()
        self.extension_names = StringVar(self)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(2, weight=1)
        self.extension_list = Listbox(self, listvariable=self.extension_names,
                                      selectmode='browse')
        self.extension_list.bind('<<ListboxSelect>>', self.extension_selected)
        scroll = ttk.Scrollbar(self, command=self.extension_list.yview)
        self.extension_list.yscrollcommand = scroll.set
        self.details_frame = ttk.LabelFrame(self, width=275, height=250)
        self.extension_list.grid(column=0, row=0, sticky='nws')
        scroll.grid(column=1, row=0, sticky='ns')
        self.details_frame.grid(column=2, row=0, sticky='nsew', padx=[10,0])
        self.details_frame.grid_propagate(0)
        self.config_frame = {}
        self.current_extension = None
        ext_names = ''
        for ext_name in sorted(self.extensions):
            self.create_extension_frame(ext_name)
            ext_names = ext_names + '{' + ext_name + '} '
        self.extension_names.set(ext_names)
        self.extension_list.selection_set(0)
        self.extension_selected(None)
        self.configure(padding=6)

    def extension_selected(self, event):
        newsel = self.extension_list.curselection()
        if newsel:
            newsel = self.extension_list.get(newsel)
        if newsel is None or newsel != self.current_extension:
            if self.current_extension:
                self.details_frame.config(text='')
                self.config_frame[self.current_extension].grid_forget()
                self.current_extension = None
        if newsel:
            self.details_frame.config(text=newsel)
            self.config_frame[newsel].grid(column=0, row=0, sticky='nw')
            self.current_extension = newsel

    def create_extension_frame(self, ext_name):
        """Create a frame holding the widgets to configure one extension"""
        f = ttk.Frame(self.details_frame, padding=10)
        self.config_frame[ext_name] = f
        entry_area = f
        # create an entry for each configuration option
        for row, opt in enumerate(self.extensions[ext_name]):
            # create a row with a label and entry/checkbutton
            label = ttk.Label(entry_area, text=opt['name'])
            label.grid(row=row, column=0, sticky=NW)
            var = opt['var']
            if opt['type'] == 'bool':
                ttk.Checkbutton(entry_area, variable=var,
                            onvalue='True', offvalue='False').grid(row=row,
                                         column=1, sticky=W, padx=7)
            elif opt['type'] == 'int':
                ttk.Entry(entry_area, textvariable=var, validate='key',
                    validatecommand=(self.is_int, '%P')
                    ).grid(row=row, column=1, sticky=NSEW, padx=7)

            else:
                ttk.Entry(entry_area, textvariable=var
                    ).grid(row=row, column=1, sticky=NSEW, padx=7)
        return

    def is_int(s):
        "Return 's is blank or represents an int'"
        if not s:
            return True
        try:
            int(s)
            return True
        except ValueError:
            return False

    def load_extensions(self):
        "Fill self.extensions with data from the default and user configs."
        self.extensions = {}
        for ext_name in idleConf.GetExtensions(active_only=False):
            self.extensions[ext_name] = []

        for ext_name in self.extensions:
            opt_list = sorted(self.defaultCfg.GetOptionList(ext_name))

            # bring 'enable' options to the beginning of the list
            enables = [opt_name for opt_name in opt_list
                       if opt_name.startswith('enable')]
            for opt_name in enables:
                opt_list.remove(opt_name)
            opt_list = enables + opt_list

            for opt_name in opt_list:
                def_str = self.defaultCfg.Get(
                        ext_name, opt_name, raw=True)
                try:
                    def_obj = {'True':True, 'False':False}[def_str]
                    opt_type = 'bool'
                except KeyError:
                    try:
                        def_obj = int(def_str)
                        opt_type = 'int'
                    except ValueError:
                        def_obj = def_str
                        opt_type = None
                try:
                    value = self.userCfg.Get(
                            ext_name, opt_name, type=opt_type, raw=True,
                            default=def_obj)
                except ValueError:  # Need this until .Get fixed
                    value = def_obj  # bad values overwritten by entry
                var = StringVar(self)
                var.set(str(value))

                self.extensions[ext_name].append({'name': opt_name,
                                                  'type': opt_type,
                                                  'default': def_str,
                                                  'value': value,
                                                  'var': var,
                                                 })


if __name__ == '__main__':
    root = Tk()
    root.wm_withdraw()
    dlg = PreferencesDialog(parent=root, destroy_callback=sys.exit)
    root.mainloop()
