import ast
import json
import pathlib
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
        self.classesList = []
        self.classCandidateFilename = 'class.txt'
        self.data_repo = "az-datasets"
        self.annotations_dir = "annotations"
        self.annotations_batch = "2023-05-11-07_55_46-rgb-depth-fg_mask"

        self.data_repo_path = os.path.join(str(pathlib.Path(__file__).parent.resolve().parent),  # parent dir
                                           self.data_repo)
        self.default_images_filepath = os.path.join(self.data_repo_path,
                                                    self.annotations_dir,
                                                    self.annotations_batch)

        # initialize mouse state
        self.STATE = {}

        # reference to bbox
        self.bboxIdList = []
        self.curBBoxId = None
        self.hl = None
        self.vl = None

        # ----------------- GUI stuff ---------------------

        # Empty label
        self.lblAlign = Label(self.rootPanel, text='  \n  ')
        self.lblAlign.grid(column=0, row=0, rowspan=100, sticky=W)

        # Top panel stuff
        self.ctrTopPanel = Frame(self.rootPanel)
        self.ctrTopPanel.grid(row=0, column=1, sticky=W+N)
        Button(self.ctrTopPanel, text="Image input folder", command=self.selectSrcDir).grid(row=0, column=0)

        # input image dir entry
        self.svSourcePath = StringVar()
        Entry(self.ctrTopPanel, textvariable=self.svSourcePath, width=70).grid(row=0, column=1, sticky=W+E, padx=5)
        self.svSourcePath.set(self.default_images_filepath)

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
        self.ctrClassPanel.grid(row=1, column=2, sticky=W+N)

        Label(self.ctrClassPanel, text='Current class:').grid(row=1, column=0, sticky=W)
        self.className = StringVar()
        self.classCandidate = ttk.Combobox(self.ctrClassPanel, state='readonly', textvariable=self.className)
        self.classCandidate.grid(row=2, column=0, sticky=W)
        if os.path.exists(self.classCandidateFilename):
            with open(self.classCandidateFilename) as cf:
                for line in cf.readlines():
                    self.classesList.append(line.strip('\n'))
        self.classCandidate['values'] = self.classesList
        self.classCandidate.current(0)
        self.currentLabelClass = self.classCandidate.get()

        # showing bbox info & delete bbox
        Label(self.ctrClassPanel, text='Annotations:').grid(row=3, column=0,  sticky=W+N)
        Button(self.ctrClassPanel, text='Delete Selected', command=self.delBBox).grid(row=4, column=0, sticky=W+E+N)
        Button(self.ctrClassPanel, text='Clear All', command=self.clearBBox).grid(row=4, column=1, sticky=W+E+S)
        self.annotationsList = Listbox(self.ctrClassPanel, width=60, height=12)
        self.annotationsList.grid(row=5, column=0, columnspan=2, sticky=N+S+W)

        # control panel GoTo

        Label(self.ctrClassPanel, text='  \n  ').grid(row=7, column=0, columnspan=2)

        self.ctrGoToPanel = Frame(self.ctrClassPanel)
        self.ctrGoToPanel.grid(row=8, column=0, columnspan=2, sticky=W+E)
        self.tmpLabel = Label(self.ctrGoToPanel, text="Go to Image No.")
        self.tmpLabel.pack(side=LEFT, padx=5)
        self.idxEntry = Entry(self.ctrGoToPanel, width=5)
        self.idxEntry.pack(side=LEFT)
        self.goBtn = Button(self.ctrGoToPanel, text='Go', command=self.gotoImage)
        self.goBtn.pack(side=LEFT)

        Label(self.ctrClassPanel, text='  \n  ').grid(row=9, column=0, columnspan=2)

        # Navigation control panel
        self.ctrNavigatePanel = Frame(self.ctrClassPanel)
        self.ctrNavigatePanel.grid(row=10, column=0, columnspan=2, sticky=W+E)
        self.prevBtn = Button(self.ctrNavigatePanel, text='<< Prev (a)', width=10, command=self.prevImage)
        self.prevBtn.pack(side=LEFT, padx=5, pady=3)
        self.nextBtn = Button(self.ctrNavigatePanel, text='(d) Next >>', width=10, command=self.nextImage)
        self.nextBtn.pack(side=LEFT, padx=5, pady=3)
        self.progLabel = Label(self.ctrNavigatePanel, text="Progress:     /    ")
        self.progLabel.pack(side=LEFT, padx=5)

        # display mouse position
        self.disp = Label(self.ctrNavigatePanel, text='')
        self.disp.pack(side=RIGHT)
        self.rootPanel.columnconfigure(5, weight=1)
        self.rootPanel.rowconfigure(6, weight=1)

    def selectSrcDir(self):
        path = filedialog.askdirectory(title="Select image source folder", initialdir=self.svSourcePath.get())
        self.svSourcePath.set(path)
        return

    def loadDir(self):
        self.rootPanel.focus()

        self.imageDir = self.svSourcePath.get()
        if not os.path.isdir(self.imageDir):
            messagebox.showerror("Error!", message="The specified dir doesn't exist!")
            return

        self.labelsDir = os.path.join(self.imageDir, 'labels')
        if not os.path.isdir(self.labelsDir):
            os.makedirs(self.labelsDir, exist_ok=True)

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

        # Load a model
        self.model = YOLO(os.path.join(self.data_repo_path, "models", "best.pt"))

        self.loadImage()

    def loadImage(self):
        self.tkimg = [0, 0, 0]
        # load image
        self.imgRootName = self.imageList[self.cur - 1]
        for panelNo in range(0, 3):
            imgFilePath = os.path.join(self.imageDir, self.imgRootName + self.fileNameTrailings[panelNo] + self.fileNameExt)
            self.tkimg[panelNo] = self.loadImgFromDisk(imgFilePath)
            self.mainPanels[panelNo].config(width=max(self.tkimg[panelNo].width(), 10), height=max(self.tkimg[panelNo].height(), 10))
            self.mainPanels[panelNo].create_image(0, 0, image=self.tkimg[panelNo], anchor=N+W)

        self.progLabel.config(text=f"{self.cur}/{self.total}")
        self.lblFilename.config(text=f"Filename: {self.imgRootName}")

        self.clearBBox()

        # load labels
        xyxyList = self.getBoxesFromFile()
        if xyxyList is None:
            xyxyList = self.getPredictionsFromYolo()

        for x1, y1, x2, y2, classIndex in xyxyList:
            bboxId = self.createBBox(x1, y1, x2, y2)
            self.annotationsList.insert(END, f"{{'x1':{x1}, 'y1':{y1}, 'class': '{self.classesList[classIndex]}', 'x2': {x2}, 'y2': {y2}, 'bboxId':{bboxId}  }}")

    def getBoxesFromFile(self):
        annotationFilePath, imgWidth, imgHeight = self.get_annotations_metadata()
        results = []
        if os.path.exists(annotationFilePath):
            with open(annotationFilePath) as f:
                for i, line in enumerate(f):
                    tmp = line.split()
                    classIndex = int(tmp[0])
                    cx = int(float(tmp[1])*imgWidth)
                    cy = int(float(tmp[2])*imgHeight)
                    hw = int(float(tmp[3])*imgWidth/2)
                    hh = int(float(tmp[4])*imgHeight/2)
                    x1 = cx - hw
                    y1 = cy - hh
                    x2 = cx + hw
                    y2 = cy + hh
                    results.append((x1, y1, x2, y2, classIndex))
        else:
            return None
        return results

    def getPredictionsFromYolo(self):
        rgbImgFilePath = os.path.join(self.imageDir, self.imgRootName + self.fileNameTrailings[0] + self.fileNameExt)
        predictions = self.model(rgbImgFilePath)  # predict on an image
        results = []
        classIndex = 0
        for result in predictions:
            for box in result.boxes:
                for x1, y1, x2, y2 in box.xyxy:
                    results.append((int(x1), int(y1), int(x2), int(y2), classIndex))
                    # self.annotationsList.itemconfig(len(self.bboxIdList) - 1, fg = COLORS[color_index])
        return results

    def loadImgFromDisk(self, fullFilePath):
        loaded_img = Image.open(fullFilePath)
        size = loaded_img.size
        img_factor = max(size[0]/1000, size[1]/1000., 1.)
        loaded_img = loaded_img.resize((int(size[0]/img_factor), int(size[1]/img_factor)))
        return ImageTk.PhotoImage(loaded_img)

    def saveImage(self):
        if self.imgRootName == '':
            return

        annotationFilePath, imgWidth, imgHeight = self.get_annotations_metadata()
        annotations = self.annotationsList.get(0, END)

        with open(annotationFilePath, 'w') as f:
            for annotationListItem in annotations:
                annotation = ast.literal_eval(annotationListItem)
                class_ = self.classesList.index(annotation['class'])
                centerX = (annotation['x1'] + annotation['x2']) / 2. / imgWidth
                centerY = (annotation['y1'] + annotation['y2']) / 2. / imgHeight
                height = abs(annotation['x1'] - annotation['x2']) * 1. / imgWidth
                width = abs(annotation['y1'] - annotation['y2']) * 1. / imgHeight
    
                f.write(f'{class_} {centerX} {centerY} {height} {width}\n')

    def get_annotations_metadata(self):
        annotationFileName = self.imgRootName + self.fileNameTrailings[0]
        annotationFilePath = os.path.join(self.labelsDir, annotationFileName + ".txt")
        imgWidth, imgHeight = self.tkimg[0].width(), self.tkimg[0].height()
        return annotationFilePath, imgWidth, imgHeight

    def mouseClick(self, event):
        if self.STATE == {}:
            self.STATE['x1'], self.STATE['y1'], self.STATE['class'] = event.x, event.y, self.currentLabelClass
        else:
            self.STATE['x2'], self.STATE['y2'] = event.x, event.y
            bboxId = self.createBBox(self.STATE['x1'], self.STATE['y1'], self.STATE['x2'], self.STATE['y2'])
            self.STATE['bboxId'] = bboxId
            self.annotationsList.insert(END, self.STATE)
            self.STATE = {}

    def createBBox(self, x1, y1, x2, y2):
        for i in range(0, 3):
            bboxId = self.mainPanels[i].create_rectangle(x1, y1, x2, y2, width=2, outline=COLORS[0])
        return bboxId

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
        for cur_item in self.annotationsList.curselection()[::-1]:
            idx = int(cur_item)
            bboxToRemove = ast.literal_eval(self.annotationsList.get(idx, idx)[0])['bboxId']
            self.mainPanels[0].delete(bboxToRemove)
            self.annotationsList.delete(idx)

    def clearBBox(self):
        self.annotationsList.select_set(0, END)
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
