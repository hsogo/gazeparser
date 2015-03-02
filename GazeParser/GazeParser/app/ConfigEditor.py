"""
Part of GazeParser library.
Copyright (C) 2012-2015 Hiroyuki Sogo.
Distributed under the terms of the GNU General Public License (GPL).

GazeParser.Configuration is a class for holding GazeParser configuration.
"""

import os
import Tkinter
import tkFileDialog
import tkMessageBox

import GazeParser
from GazeParser.Configuration import GazeParserDefaults, GazeParserOptions, Config


class ConfigEditor(Tkinter.Frame):
    def __init__(self, master=None, configObject=None, showExit=True):
        Tkinter.Frame.__init__(self, master)
        self.master.title('GazeParser Configuration')
        self.ftypes = [('GazeParser ConfigFile', '*.cfg')]
        self.StringVarDict = {}
        r = 0

        for key in GazeParserOptions:
            self.StringVarDict[key] = Tkinter.StringVar()
            Tkinter.Label(self, text=key).grid(row=r, column=0, sticky=Tkinter.W)
            Tkinter.Entry(self, textvariable=self.StringVarDict[key]).grid(row=r, column=1)
            r += 1

        self.menu_bar = Tkinter.Menu(tearoff=False)
        self.menu_file = Tkinter.Menu(tearoff=False)
        self.menu_bar.add_cascade(label='File', menu=self.menu_file, underline=0)
        self.menu_file.add_command(label='Open', under=0, command=self._openfile)
        self.menu_file.add_command(label='Save', under=0, command=self._save)
        self.menu_file.add_command(label='Save as...', under=0, command=self._saveas)
        if showExit:
            self.menu_file.add_command(label='Exit', under=0, command=self._quitfunc)
        self.master.configure(menu=self.menu_bar)

        self.pack()

        if configObject is not None:
            for key in GazeParserOptions:
                self.StringVarDict[key].set(getattr(configObject, key))

    def _openfile(self):
        if os.path.exists(GazeParser.configDir):
            fdir = GazeParser.configDir
        else:
            fdir = GazeParser.homeDir
        self.ConfigFileName = tkFileDialog.askopenfilename(filetypes=self.ftypes, initialdir=fdir)

        try:
            config = Config(self.ConfigFileName)
        except:
            tkMessageBox.showerror('Error', 'Cannot read %s.\nThis file may not be a GazeParser ConfigFile' % self.ConfigFileName)
        else:
            for key in GazeParserOptions:
                self.StringVarDict[key].set(getattr(config, key))

    def _quitfunc(self):
        self.winfo_toplevel().destroy()
        self.quit()

    def _save(self):
        if not hasattr(self, 'ConfigFileName'):
            self._saveas()
            return

        if self.ConfigFileName == '':
            self._saveas()
            return

        for key in GazeParserOptions:
            if self.StringVarDict[key].get() == '':
                tkMessageBox.showerror('Error', '\'%s\' is empty.\nConfiguration is not saved.' % key)
                return

        try:
            fp = open(self.ConfigFileName, 'w')
        except:
            tkMessageBox.showerror('Error', 'Could not open \'%s\' for writing.' % self.ConfigFileName)
            return

        fp.write('[GazeParser]\n')
        for key in GazeParserOptions:
            fp.write('%s = %s\n' % (key, self.StringVarDict[key].get()))
        fp.close()

        tkMessageBox.showinfo('Info', 'Saved to \'%s\'' % self.ConfigFileName)

    def _saveas(self):
        for key in GazeParserOptions:
            if self.StringVarDict[key].get() == '':
                tkMessageBox.showerror('Error', '\'%s\' is empty.\nConfiguration is not saved.' % key)
                return

        try:
            fdir = os.path.split(self.ConfigFileName)[0]
        except:
            if os.path.exists(GazeParser.configDir):
                fdir = GazeParser.configDir
            else:
                fdir = GazeParser.homeDir
        fname = tkFileDialog.asksaveasfilename(filetypes=self.ftypes, initialdir=fdir)

        if fname == '':
            return

        try:
            fp = open(fname, 'w')
        except:
            tkMessageBox.showerror('Error', 'Could not open \'%s\'' % fname)
            return

        fp.write('[GazeParser]\n')
        for key in GazeParserOptions:
            fp.write('%s = %s\n' % (key, self.StringVarDict[key].get()))
        fp.close()

        tkMessageBox.showinfo('Info', 'Saved to \'%s\'' % fname)

if (__name__ == '__main__'):
    w = ConfigEditor()
    w.mainloop()
