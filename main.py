import ast
from tkinter import END, LEFT, N, RIGHT, S, W, E, StringVar, Tk
from tkinter import filedialog, Button, Canvas, Entry, Frame, Label, Listbox
from tkinter import messagebox
from tkinter import ttk
from PIL import Image, ImageTk
import os
import glob
from ultralytics import YOLO

# colors for the bboxes
COLORS = ['red', 'blue', 'pink', 'cyan', 'green', 'black']
# image sizes for the examples
SIZE = 256, 256


class LabelTool():
    def __init__(self, master):
        # set up the main frame
        self.rootPanel = master
        self.rootPanel.title("az Image Annotations")
        self.rootPanel.resizable(width=False, height=False)

        # initialize global state
        self.imageDir = ''
        self.imageList = []
        self.cur = 0
        self.total = 0
        self.category = 0
        self.imagename = ''
        self.labelfilename = ''
        self.tkimg = None
        self.currentLabelClass = ''
        self.cla_can_temp = []
        self.classCandidateFilename = 'class.txt'

        # initialize mouse state
        self.STATE = {}

        # reference to bbox
        self.bboxIdList = []
        self.curBBoxId = None
        self.hl = None
        self.vl = None

        # ----------------- GUI stuff ---------------------

        # Empty label
        self.lblAlign = Label(self.rootPanel, text='  \n  ', bg='green')
        self.lblAlign.grid(column=0, row=0, rowspan=100, sticky=W)
        
        # Top panel stuff
        self.ctrTopPanel = Frame(self.rootPanel)
        self.ctrTopPanel.grid(row=0, column=1, sticky=W+N)
        Button(self.ctrTopPanel, text="Image input folder", command=self.selectSrcDir).grid(row=0, column=0)

        # input image dir entry
        self.svSourcePath = StringVar()
        Entry(self.ctrTopPanel, textvariable=self.svSourcePath, width=70).grid(row=0, column=1, sticky=W+E, padx=5)
        self.svSourcePath.set(os.path.join(os.getcwd(), "images"))

        # filter
        self.filterVar = StringVar()
        Entry(self.ctrTopPanel, textvariable=self.filterVar, width=25).grid(row=0, column=2, sticky=W+E, padx=5)
        self.filterVar.set('rgb|fg_mask|disparity')

        # Button load dir
        self.bLoad = Button(self.ctrTopPanel, text="Load Dir", command=self.loadDir)
        self.bLoad.grid(row=0, column=3, rowspan=1, padx=2, pady=2, ipadx=5, ipady=5)
        self.lblFilename = Label(self.ctrTopPanel, text="Current filename: <name>", justify=LEFT, anchor="w")
        self.lblFilename.grid(row=1, column=0, columnspan=2, sticky=W)

        # main panel for labeling
        self.mainPanels = [None, None, None]
        self.mainPanels[0] = Canvas(self.rootPanel, cursor='tcross')
        self.mainPanels[0].grid(row=1, column=1, sticky=W+N)
        self.mainPanels[0].bind("<Button-1>", self.mouseClick)
        self.mainPanels[0].bind("<Motion>", self.mouseMove)

        self.mainPanels[1] = Canvas(self.rootPanel, cursor='tcross')
        self.mainPanels[1].grid(row=2, column=1, sticky=W+N)

        self.mainPanels[2] = Canvas(self.rootPanel, cursor='tcross')
        self.mainPanels[2].grid(row=2, column=2, sticky=W+N)

        self.rootPanel.bind("<Escape>", self.cancelBBox)  # press <Espace> to cancel current bbox
        self.rootPanel.bind("c", self.cancelBBox)
        self.rootPanel.bind("a", self.prevImage)  # press 'a' to go backward
        self.rootPanel.bind("d", self.nextImage)  # press 'd' to go forward

        # Class panel
        self.ctrClassPanel = Frame(self.rootPanel)
        self.ctrClassPanel.grid(row=1, column=2, sticky=E)

        Label(self.ctrClassPanel, text='Current class:').grid(row=1, column=1, sticky=W)
        self.className = StringVar()
        self.classCandidate = ttk.Combobox(self.ctrClassPanel, state='readonly', textvariable=self.className)
        self.classCandidate.grid(row=2, column=1, sticky=W)
        if os.path.exists(self.classCandidateFilename):
            with open(self.classCandidateFilename) as cf:
                for line in cf.readlines():
                    self.cla_can_temp.append(line.strip('\n'))
        self.classCandidate['values'] = self.cla_can_temp
        self.classCandidate.current(0)
        self.currentLabelClass = self.classCandidate.get()

        # showing bbox info & delete bbox
        Label(self.ctrClassPanel, text='Annotations:').grid(row=3, column=1,  sticky=W+N)
        Button(self.ctrClassPanel, text='Delete Selected', command=self.delBBox).grid(row=4, column=1, sticky=W+E+N)
        self.classList = Listbox(self.ctrClassPanel, width=50, height=12)
        self.classList.grid(row=5, column=1, sticky=N+S)
        Button(self.ctrClassPanel, text='Clear All', command=self.clearBBox).grid(row=6, column=1, sticky=W+E+S)

        # control panel for image navigation
        self.ctrBottomPanel = Frame(self.rootPanel)
        self.ctrBottomPanel.grid(row=4, column=1, columnspan=2, sticky=W+E)
        self.prevBtn = Button(self.ctrBottomPanel, text='<< Prev', width=10, command=self.prevImage)
        self.prevBtn.pack(side=LEFT, padx=5, pady=3)
        self.nextBtn = Button(self.ctrBottomPanel, text='Next >>', width=10, command=self.nextImage)
        self.nextBtn.pack(side=LEFT, padx=5, pady=3)
        self.progLabel = Label(self.ctrBottomPanel, text="Progress:     /    ")
        self.progLabel.pack(side=LEFT, padx=5)
        self.tmpLabel = Label(self.ctrBottomPanel, text="Go to Image No.")
        self.tmpLabel.pack(side=LEFT, padx=5)
        self.idxEntry = Entry(self.ctrBottomPanel, width=5)
        self.idxEntry.pack(side=LEFT)
        self.goBtn = Button(self.ctrBottomPanel, text='Go', command=self.gotoImage)
        self.goBtn.pack(side=LEFT)

        # display mouse position
        self.disp = Label(self.ctrBottomPanel, text='')
        self.disp.pack(side=RIGHT)
        self.rootPanel.columnconfigure(5, weight=1)
        self.rootPanel.rowconfigure(6, weight=1)

    def selectSrcDir(self):
        path = filedialog.askdirectory(title="Select image source folder", initialdir=self.svSourcePath.get())
        self.svSourcePath.set(path)
        return

    def loadDir(self):
        self.rootPanel.focus()
        # get image list
        # self.imageDir = os.path.join(r'./Images', '%03d' %(self.category))
        self.imageDir = self.svSourcePath.get()
        if not os.path.isdir(self.imageDir):
            messagebox.showerror("Error!", message="The specified dir doesn't exist!")
            return

        self.fileNameTrailings = self.filterVar.get().split("|")
        self.fileNameExt = ".jpg"
        suffixForLoad = f'{self.fileNameTrailings[0]}{self.fileNameExt}'

        filelist = glob.glob(os.path.join(self.imageDir, "*-" + suffixForLoad))
        filelist = [k.split("\\")[-1] for k in filelist]  # in form of filename
        filelist = [k.replace(suffixForLoad, '') for k in filelist]  # store file name prefixes only
        self.imageList.extend(filelist)

        if len(self.imageList) == 0:
            print('No .JPEG images found in the specified dir!')
            return

        # default to the 1st image in the collection
        self.cur = 1
        self.total = len(self.imageList)

        # set up output dir
        # self.outDir = os.path.join(r'./Labels', '%03d' %(self.category))
        # self.outDir = self.svDestinationPath.get()
        # if not os.path.exists(self.outDir):
        #     os.mkdir(self.outDir)

        # load example bboxes
        # self.egDir = os.path.join(r'./Examples', '%03d' %(self.category))
        # self.egDir = os.path.join(os.getcwd(), "Examples/001")
        # if not os.path.exists(self.egDir):
        #     return
        # filelist = glob.glob(os.path.join(self.egDir, '*.JPEG'))
        # self.tmp = []
        # self.egList = []
        # random.shuffle(filelist)
        # for (i, f) in enumerate(filelist):
        #     if i == 1:
        #         break
        #     im = Image.open(f)
        #     r = min(SIZE[0] / im.size[0], SIZE[1] / im.size[1])
        #     new_size = int(r * im.size[0]), int(r * im.size[1])
        #     self.tmp.append(im.resize(new_size, Image.ANTIALIAS))
        #     self.egList.append(ImageTk.PhotoImage(self.tmp[-1]))
        #     self.egLabels[i].config(image=self.egList[-1], width=SIZE[0], height=SIZE[1])

        self.loadImage()

    def loadImage(self):
        self.tkimg = [0,0]
        # load image
        imgRootName = self.imageList[self.cur - 1]
        for panelNo in range(0, 2):
            imgFilePath = os.path.join(self.imageDir, imgRootName + self.fileNameTrailings[panelNo] + self.fileNameExt)
            self.tkimg[panelNo] = self.loadImgFromDisk(imgFilePath)
            self.mainPanels[panelNo].config(width=max(self.tkimg[panelNo].width(), 800), height=max(self.tkimg[panelNo].height(), 400))
            self.mainPanels[panelNo].create_image(0, 0, image=self.tkimg[panelNo], anchor=N+W)

        self.progLabel.config(text=f"{self.cur}/{self.total}")
        self.lblFilename.config(text=f"Filename: {imgFilePath}")

        self.clearBBox()
        return

        # load labels
        # self.imagename = os.path.split(imagepath)[-1].split('.')[0]
        fullfilename = os.path.basename(imgRootName)
        self.imagename, _ = os.path.splitext(fullfilename)
        labelname = self.imagename + '.txt'
        self.labelfilename = os.path.join(self.outDir, labelname)
        bbox_cnt = 0
        if os.path.exists(self.labelfilename):
            with open(self.labelfilename) as f:
                for i, line in enumerate(f):
                    # if i == 0:
                    #     bbox_cnt = int(line.strip())
                    #     continue
                    # tmp = [int(t.strip()) for t in line.split()]
                    tmp = line.split()
                    tmp[0] = int(int(tmp[0])/self.factor)
                    tmp[1] = int(int(tmp[1])/self.factor)
                    tmp[2] = int(int(tmp[2])/self.factor)
                    tmp[3] = int(int(tmp[3])/self.factor)
                    self.bboxList.append(tuple(tmp))
                    color_index = (len(self.bboxList)-1) % len(COLORS)
                    tmpId = self.mainPanel.create_rectangle(tmp[0], tmp[1],
                                                            tmp[2], tmp[3],
                                                            width = 2,
                                                            outline = COLORS[color_index])
                                                            #outline = COLORS[(len(self.bboxList)-1) % len(COLORS)])
                    self.bboxIdList.append(tmpId)
                    self.classList.insert(END, '%s : (%d, %d) -> (%d, %d)' %(tmp[4], tmp[0], tmp[1], tmp[2], tmp[3]))
                    self.classList.itemconfig(len(self.bboxIdList) - 1, fg = COLORS[color_index])

    def loadImgFromDisk(self, fullFilePath):
        loaded_img = Image.open(fullFilePath)
        size = loaded_img.size
        img_factor = max(size[0]/1000, size[1]/1000., 1.)
        loaded_img = loaded_img.resize((int(size[0]/img_factor), int(size[1]/img_factor)))
        return ImageTk.PhotoImage(loaded_img)
        
    def saveImage(self):
        return
        if self.labelfilename == '':
            return
        with open(self.labelfilename, 'w') as f:
            f.write('%d\n' %len(self.bboxList))
            for bbox in self.bboxList:
                f.write("{} {} {} {} {}\n".format(int(int(bbox[0])*self.factor),
                                                int(int(bbox[1])*self.factor),
                                                int(int(bbox[2])*self.factor),
                                                int(int(bbox[3])*self.factor), bbox[4]))
                #f.write(' '.join(map(str, bbox)) + '\n')
        print('Image No. %d saved' %(self.cur))

    def mouseClick(self, event):
        if self.STATE == {}:
            self.STATE['x1'], self.STATE['y1'], self.STATE['class'] = event.x, event.y, self.currentLabelClass
        else:
            self.STATE['x2'], self.STATE['y2'] = event.x, event.y
            bboxId = self.mainPanels[0].create_rectangle(self.STATE['x1'], self.STATE['y1'],
                                                         self.STATE['x2'], self.STATE['y2'],
                                                         width=2,
                                                         outline=COLORS[0])
            self.STATE['bboxId'] = bboxId
            self.classList.insert(END, self.STATE)
            self.STATE = {}

    def mouseMove(self, event):
        self.disp.config(text='x: %d, y: %d' %(event.x, event.y))

        if self.tkimg[0]:
            if self.hl:
                self.mainPanels[0].delete(self.hl)
            self.hl = self.mainPanels[0].create_line(0, event.y, self.tkimg[0].width(), event.y, width=2)
            if self.vl:
                self.mainPanels[0].delete(self.vl)
            self.vl = self.mainPanels[0].create_line(event.x, 0, event.x, self.tkimg[0].height(), width=2)
        if self.STATE != {}:
            if self.curBBoxId:
                self.mainPanels[0].delete(self.curBBoxId)
            self.curBBoxId = self.mainPanels[0].create_rectangle(self.STATE['x1'], self.STATE['y1'],
                                                                 event.x, event.y,
                                                                 width=2,
                                                                 outline=COLORS[4])

    def cancelBBox(self, event):
        if self.curBBoxId:
            self.mainPanels[0].delete(self.curBBoxId)
        self.STATE = {}

    def delBBox(self):
        for cur_item in self.classList.curselection()[::-1]:
            idx = int(cur_item)
            bboxToRemove = ast.literal_eval(self.classList.get(idx, idx)[0])['bboxId']
            self.mainPanels[0].delete(bboxToRemove)
            self.classList.delete(idx)

    def clearBBox(self):
        self.classList.select_set(0, END)
        self.delBBox()

    def prevImage(self, event=None):
        self.saveImage()
        if self.cur > 1:
            self.cur -= 1
            self.loadImage()

    def nextImage(self, event=None):
        self.saveImage()
        if self.cur < self.total:
            self.cur += 1
            self.loadImage()

    def gotoImage(self):
        idx = int(self.idxEntry.get())
        if 1 <= idx and idx <= self.total:
            self.saveImage()
            self.cur = idx
            self.loadImage()

if __name__ == '__main__':
    root = Tk()
    tool = LabelTool(root)
    root.resizable(width=True, height=True)
    root.mainloop()
