from tkinter import BOTH, END, LEFT, N, RIGHT, S, TOP, W, E, StringVar, Tk
from tkinter import filedialog, Button, Canvas, Entry, Frame, Label, Listbox
from tkinter import messagebox
from tkinter import ttk
from PIL import Image, ImageTk
import os
import glob
import random
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
        self.currentLabelclass = ''
        self.cla_can_temp = []
        self.classcandidate_filename = 'class.txt'

        # initialize mouse state
        self.STATE = {}
        self.STATE['click'] = 0
        self.STATE['x'], self.STATE['y'] = 0, 0

        # reference to bbox
        self.bboxIdList = []
        self.bboxId = None
        self.bboxList = []
        self.hl = None
        self.vl = None

        # ----------------- GUI stuff ---------------------

        # Empty label
        self.lblAlign = Label(self.rootPanel, text='  \n  ', bg='green')
        self.lblAlign.grid(column=0, row=0, rowspan=100, sticky=W)
        
        # Top panel stuff
        self.ctrTopPanel = Frame(self.rootPanel)
        self.ctrTopPanel.grid(row=0, column=1, sticky=W+N)
        Button(self.ctrTopPanel, text="Image input folder", command=self.selectSrcDir, ).grid(row=0, column=0)

        # input image dir entry
        self.svSourcePath = StringVar()
        self.entrySrc = Entry(self.ctrTopPanel, textvariable=self.svSourcePath, width=70)
        self.entrySrc.grid(row=0, column=1, sticky=W+E)
        self.svSourcePath.set(os.path.join(os.getcwd(), "images"))

        # filter
        self.filterVar = StringVar()
        Entry(self.ctrTopPanel, textvariable=self.filterVar, width=10).grid(row=0, column=2, sticky=W+E)
        self.filterVar.set('-rgb')

        self.bLoad = Button(self.ctrTopPanel, text="Load Dir", command=self.loadDir).grid(row=0, column=3, rowspan=1, padx=2, pady=2, ipadx=5, ipady=5)
        self.lblFilename = Label(self.ctrTopPanel, text="Current filename: <name>", justify=LEFT, anchor="w")
        self.lblFilename.grid(row=1, column=0, columnspan=2, sticky=W)
        
        # main panel for labeling
        self.mainPanel = Canvas(self.rootPanel, cursor='tcross')
        self.mainPanel.grid(row=1, column=1, sticky=W+N)
        self.mainPanel.bind("<Button-1>", self.mouseClick)
        self.mainPanel.bind("<Motion>", self.mouseMove)
        self.rootPanel.bind("<Escape>", self.cancelBBox)  # press <Espace> to cancel current bbox
        self.rootPanel.bind("c", self.cancelBBox)
        self.rootPanel.bind("a", self.prevImage)  # press 'a' to go backforward
        self.rootPanel.bind("d", self.nextImage)  # press 'd' to go forward

        # Class panel
        self.ctrClassPanel = Frame(self.rootPanel)
        self.ctrClassPanel.grid(row=1, column=2, sticky="e")

        self.className = StringVar()
        self.classCandidate = ttk.Combobox(self.ctrClassPanel, state='readonly', textvariable=self.className)
        self.classCandidate.grid(row=2, column=2)
        if os.path.exists(self.classcandidate_filename):
            with open(self.classcandidate_filename) as cf:
                for line in cf.readlines():
                    self.cla_can_temp.append(line.strip('\n'))
        self.classCandidate['values'] = self.cla_can_temp
        self.classCandidate.current(0)
        self.currentLabelclass = self.classCandidate.get()
        self.btnclass = Button(self.ctrClassPanel, text='ComfirmClass', command=self.setClass).grid(row=2, column=3, sticky=W+E)

        # showing bbox info & delete bbox
        Label(self.ctrClassPanel, text='Bounding boxes:').grid(row=3, column=2,  sticky=W+N)
        self.classList = Listbox(self.ctrClassPanel, width=22, height=12).grid(row=4, column=2, sticky=N+S)
        Button(self.ctrClassPanel, text='Delete', command=self.delBBox).grid(row=4, column=3, sticky=W+E+N)
        Button(self.ctrClassPanel, text='ClearAll', command=self.clearBBox).grid(row=4, column=3, sticky=W+E+S)

        # control panel for image navigation
        self.ctrBottomPanel = Frame(self.rootPanel)
        self.ctrBottomPanel.grid(row=2, column=1, columnspan=2, sticky=W+E)
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
        self.disp=Label(self.ctrBottomPanel, text='')
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
        #self.imageDir = os.path.join(r'./Images', '%03d' %(self.category))
        self.imageDir = self.svSourcePath.get()
        if not os.path.isdir(self.imageDir):
            messagebox.showerror("Error!", message="The specified dir doesn't exist!")
            return

        extlist = ["*.JPEG", "*.jpeg", "*JPG", "*.jpg", "*.PNG", "*.png", "*.BMP", "*.bmp"]
        for e in extlist:
            filelist = glob.glob(os.path.join(self.imageDir, e))
            filelist = [k for k in filelist if self.filterVar.get() in k]
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
        # load image
        imagePath = self.imageList[self.cur - 1]
        self.img = Image.open(imagePath)
        size = self.img.size
        self.factor = max(size[0]/1000, size[1]/1000., 1.)
        self.img = self.img.resize((int(size[0]/self.factor), int(size[1]/self.factor)))
        self.tkimg = ImageTk.PhotoImage(self.img)
        self.mainPanel.config(width=max(self.tkimg.width(), 800), height=max(self.tkimg.height(), 400))
        self.mainPanel.create_image(0, 0, image=self.tkimg, anchor=N+W)
        self.progLabel.config(text=f"{self.cur}//{self.total}")
        self.lblFilename.config(text=f"Filename: {imagePath}")

        return
    
        # load labels
        self.clearBBox()
        #self.imagename = os.path.split(imagepath)[-1].split('.')[0]
        fullfilename = os.path.basename(imagePath)
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
                    tmpId = self.mainPanel.create_rectangle(tmp[0], tmp[1], \
                                                            tmp[2], tmp[3], \
                                                            width = 2, \
                                                            outline = COLORS[color_index])
                                                            #outline = COLORS[(len(self.bboxList)-1) % len(COLORS)])
                    self.bboxIdList.append(tmpId)
                    self.classList.insert(END, '%s : (%d, %d) -> (%d, %d)' %(tmp[4], tmp[0], tmp[1], tmp[2], tmp[3]))
                    self.classList.itemconfig(len(self.bboxIdList) - 1, fg = COLORS[color_index])
                    # self.listbox.itemconfig(len(self.bboxIdList) - 1, fg = COLORS[(len(self.bboxIdList) - 1) % len(COLORS)])

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
        if self.STATE['click'] == 0:
            self.STATE['x'], self.STATE['y'] = event.x, event.y
        else:
            x1, x2 = min(self.STATE['x'], event.x), max(self.STATE['x'], event.x)
            y1, y2 = min(self.STATE['y'], event.y), max(self.STATE['y'], event.y)
            self.bboxList.append((x1, y1, x2, y2, self.currentLabelclass))
            self.bboxIdList.append(self.bboxId)
            self.bboxId = None
            self.classList.insert(END, '%s : (%d, %d) -> (%d, %d)' %(self.currentLabelclass, x1, y1, x2, y2))
            self.classList.itemconfig(len(self.bboxIdList) - 1, fg = COLORS[(len(self.bboxIdList) - 1) % len(COLORS)])
        self.STATE['click'] = 1 - self.STATE['click']

    def mouseMove(self, event):
        self.disp.config(text = 'x: %d, y: %d' %(event.x, event.y))
        if self.tkimg:
            if self.hl:
                self.mainPanel.delete(self.hl)
            self.hl = self.mainPanel.create_line(0, event.y, self.tkimg.width(), event.y, width = 2)
            if self.vl:
                self.mainPanel.delete(self.vl)
            self.vl = self.mainPanel.create_line(event.x, 0, event.x, self.tkimg.height(), width = 2)
        if 1 == self.STATE['click']:
            if self.bboxId:
                self.mainPanel.delete(self.bboxId)
            COLOR_INDEX = len(self.bboxIdList) % len(COLORS)
            self.bboxId = self.mainPanel.create_rectangle(self.STATE['x'], self.STATE['y'], \
                                                            event.x, event.y, \
                                                            width = 2, \
                                                            outline = COLORS[len(self.bboxList) % len(COLORS)])

    def cancelBBox(self, event):
        if 1 == self.STATE['click']:
            if self.bboxId:
                self.mainPanel.delete(self.bboxId)
                self.bboxId = None
                self.STATE['click'] = 0

    def delBBox(self):
        sel = self.classList.curselection()
        if len(sel) != 1 :
            return
        idx = int(sel[0])
        self.mainPanel.delete(self.bboxIdList[idx])
        self.bboxIdList.pop(idx)
        self.bboxList.pop(idx)
        self.classList.delete(idx)

    def clearBBox(self):
        for idx in range(len(self.bboxIdList)):
            self.mainPanel.delete(self.bboxIdList[idx])
        self.classList.delete(0, len(self.bboxList))
        self.bboxIdList = []
        self.bboxList = []

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

    def setClass(self):
        self.currentLabelclass = self.classCandidate.get()
        print('set label class to : %s' % self.currentLabelclass)


if __name__ == '__main__':
    root = Tk()
    tool = LabelTool(root)
    root.resizable(width=True, height=True)
    root.mainloop()
