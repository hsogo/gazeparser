from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys
import os
import numpy

pillow = False

try:
    import Image, ImageTk
except ImportError:
    from PIL import Image, ImageTk
    pillow = True

if sys.version_info[0] == 2:
    import Tkinter
    import tkFileDialog
    import tkMessageBox
    import tkColorChooser
else:
    import tkinter as Tkinter
    from tkinter import filedialog as tkFileDialog
    from tkinter import messagebox as tkMessageBox
    from tkinter import colorchooser as tkColorChooser


import GazeParser.ScanMatch
from GazeParser import homeDir

class ScanMatchMatricesFromImage(Tkinter.Frame):
    def __init__(self, master=None):
        Tkinter.Frame.__init__(self, master)
        self.master.title('Create ScanMatch matrices from Image')
        
        self.threshold = Tkinter.StringVar()
        self.margeColor = Tkinter.StringVar()
        
        imagefile = os.path.join(os.path.dirname(__file__),'img','white800x600.png')
        self.img = ImageTk.PhotoImage(Image.open(imagefile))
        self.imageLabel = Tkinter.Label(self,image=self.img, relief=Tkinter.RAISED, bd=3)
        self.menu_bar = Tkinter.Menu(tearoff=False)
        self.menu_file = Tkinter.Menu(tearoff=False)
        self.menu_bar.add_cascade(label='File',menu=self.menu_file,underline=0)
        self.menu_file.add_command(label='Open image',under=0,command=self._open)
        self.menu_file.add_command(label='Exit',under=0,command=self.quit)
        self.master.configure(menu = self.menu_bar)
        
        self.imageLabel.pack()
        self.pack(side=Tkinter.LEFT)
        
        self.sideFrame = Tkinter.Frame(master)
        
        self.commandFrame = Tkinter.Frame(self.sideFrame)
        Tkinter.Label(self.commandFrame,text='Threshold').grid(row=0,column=0)
        Tkinter.Entry(self.commandFrame,textvariable=self.threshold).grid(row=0,column=1)
        Tkinter.Label(self.commandFrame,text='Marge to...').grid(row=1,column=0)
        Tkinter.Entry(self.commandFrame,textvariable=self.margeColor).grid(row=1,column=1)
        Tkinter.Label(self.commandFrame,text='You can choose color from\nthe list below by double-clicking').grid(row=2,column=0,columnspan=2)
        Tkinter.Button(self.commandFrame,text='Generate matrices', command=self._generateMatrices).grid(row=3,column=0,columnspan=2)
        
        self.listboxFrame = Tkinter.Frame(self.sideFrame)
        self.yscroll = Tkinter.Scrollbar(self.listboxFrame, orient=Tkinter.VERTICAL)
        self.listbox = Tkinter.Listbox(master=self.listboxFrame,yscrollcommand=self.yscroll.set, selectmode=Tkinter.EXTENDED)
        self.listbox.pack(side=Tkinter.LEFT, fill=Tkinter.BOTH, expand=True)
        self.yscroll.pack(side=Tkinter.LEFT, anchor=Tkinter.W, fill=Tkinter.Y, expand=False)
        self.yscroll['command'] = self.listbox.yview
        self.listbox.bind('<Double-1>',self._getcolor)
        
        self.commandFrame.pack(side=Tkinter.TOP,fill=Tkinter.BOTH)
        self.listboxFrame.pack(side=Tkinter.TOP,fill=Tkinter.BOTH, expand=True)
        self.sideFrame.pack(side=Tkinter.LEFT, fill=Tkinter.BOTH, expand=True)
    
    def _open(self):
        filename = tkFileDialog.askopenfilename(initialdir=homeDir)
        if filename == '':
            return
        
        pilImg = Image.open(filename)
        if pilImg.size[0]>800 or pilImg.size[0]>600:
            scale = max(800.0/pilImg.size[0], 600.0/pilImg.size[1])
            w = int(pilImg.size[0]*scale)
            h = int(pilImg.size[1]*scale)
            self.img = ImageTk.PhotoImage(pilImg.resize((w,h)))
        else:
            self.img = ImageTk.PhotoImage(pilImg)
        self.imageLabel.configure(image=self.img)
        
        d = numpy.uint32(numpy.asarray(pilImg))
        if len(d.shape)==3:
            d = (d[:,:,0]<<16) + (d[:,:,1]<<8) + d[:,:,2]
        uniqueData = numpy.unique(d)
        
        if len(uniqueData)>128:
            res = tkMessageBox.askquestion('Warning','More than 128 colors are used in this image.\nBuilding color list may take very long time.\nAre you sure to continure processing?')
            if res=='no':
                return
        
        self.dataArray = d
        self.regionlist = [(uniqueData[i],len(numpy.where(d==uniqueData[i])[0]))
                           for i in range(len(uniqueData))]
        
        self.listbox.delete(0,self.listbox.size())
        for i in range(len(self.regionlist)):
            self.listbox.insert(Tkinter.END,'0x%06x: %d'%self.regionlist[i])
            (r,g,b) = ((self.regionlist[i][0] & 0x00FF0000)>>16,
                       (self.regionlist[i][0] & 0x0000FF00)>>8,
                       (self.regionlist[i][0] & 0x000000FF))
            if min(r,g,b) < 128:
                col = 'white'
            else:
                col = 'black'
            self.listbox.itemconfig(Tkinter.END,bg='#%06x' % self.regionlist[i][0], fg=col)
    
    def _getcolor(self,event):
        activeText = self.listbox.get(Tkinter.ACTIVE)
        self.margeColor.set(activeText[:8])
    
    def _generateMatrices(self):
        threshold = int(self.threshold.get())
        margeColor = int(self.margeColor.get(),16)
        mask,colorList = GazeParser.ScanMatch.generateMaskFromArray(self.dataArray,threshold,margeColor)
        
        if len(colorList) > 12:
            tkMessageBox.showinfo('Info','Mask matrix and color list are generated.\nEdit Submatrix manually because color list is too long (>12)')
            saveSubmatrix = 'no'
        else:
            saveSubmatrix = tkMessageBox.askquestion('Info','Mask matrix and color list are generated.\nInput data for Submatrix?')
            if saveSubmatrix=='yes':
                submatrix = self._inputSubMatrix(colorList)
                if submatrix == None:
                    res = tkMessageBox.askquestion('Error','Invalid value is found.\nSave only mask matrix and color list?')
                    if res=='no':
                        return
                    else:
                        saveSubmatrix = 'no'
        
        maskfile = tkFileDialog.asksaveasfilename(title='Save Mask matrix...',initialfile='mask.txt',initialdir=homeDir)
        if maskfile != '':
            numpy.savetxt(maskfile,mask,fmt='%d')
        
        colorfile = tkFileDialog.asksaveasfilename(title='Save color list...',initialfile='colorlist.txt',initialdir=homeDir)
        if colorfile != '':
            numpy.savetxt(colorfile,colorList,fmt='%06x',delimiter=',')
        
        if saveSubmatrix=='yes':
            subfile = tkFileDialog.asksaveasfilename(title='Save Submatrix...',initialfile='submatrix.txt',initialdir=homeDir)
            if subfile != '':
                numpy.savetxt(subfile,submatrix,fmt='%f',delimiter=',')
        
        tkMessageBox.showinfo('Info','Done!')
    
    def _inputSubMatrix(self, colorList):
        dlg = Tkinter.Toplevel(self)
        Tkinter.Label(dlg,text=' ').grid(row=0,column=0)
        fgColorList = []
        nColor = len(colorList)
        for i in range(nColor):
            (r,g,b) = ((colorList[i] & 0x00FF0000)>>16,
                       (colorList[i] & 0x0000FF00)>>8,
                       (colorList[i] & 0x000000FF))
            if min(r,g,b) < 128:
                col = 'white'
            else:
                col = 'black'
            fgColorList.append(col)
            Tkinter.Label(dlg,text=str(i),bg='#%06x'%colorList[i],fg=col,width=8).grid(row=0,column=i+1)
        
        varList = [Tkinter.StringVar() for i in range(nColor**2)]
        for r in range(nColor):
            Tkinter.Label(dlg,text=str(r),bg='#%06x'%colorList[r],fg=fgColorList[r],width=3).grid(row=r+1,column=0)
            for c in range(nColor):
                Tkinter.Entry(dlg,width=8,textvariable=varList[r*nColor+c]).grid(row=r+1,column=c+1)
        
        Tkinter.Button(dlg,text='OK',command=dlg.destroy).grid(row=nColor+1,column=0,columnspan=nColor+1)
        
        dlg.focus_set()
        dlg.grab_set()
        dlg.transient(self)
        dlg.resizable(0, 0)
        dlg.wait_window(dlg)
        
        submatrix = numpy.zeros((nColor,nColor))
        try:
            for r in range(nColor):
                for c in range(nColor):
                    submatrix[r,c] = float(varList[r*nColor+c].get())
        except:
            return None
        
        return submatrix

if (__name__ == '__main__'):
    w = ScanMatchMatricesFromImage()
    w.mainloop()
